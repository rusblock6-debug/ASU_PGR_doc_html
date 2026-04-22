package rabbitmq

import (
	"context"
	"fmt"
	"sync"
	"sync/atomic"
	"time"

	amqp "github.com/rabbitmq/amqp091-go"
	"github.com/rs/zerolog"
)

// DedupService is a narrow interface used by Publisher to record a MessageID
// as seen in the dedup store after a successful broker ACK.
type DedupService interface {
	MarkSeen(ctx context.Context, messageID string) error
}

type PublishMessage struct {
	RoutingKey string
	Body       []byte
	MessageID  string
	Headers    map[string]string
}

type publishRequest struct {
	msg    PublishMessage
	ctx    context.Context
	result chan error
}

type Publisher struct {
	client     *Client
	logger     zerolog.Logger
	requests   chan publishRequest
	bufferSize int
	dedupSvc   DedupService

	mu         sync.RWMutex
	pending    map[uint64]chan error
	ch         *amqp.Channel
	confirms   chan amqp.Confirmation
	returns    chan amqp.Return
	seqToMsgID map[uint64]string
	returned   map[string]amqp.Return

	connected atomic.Bool
	done      chan struct{}
	closeOnce sync.Once

	// настройки reconnect
	reconnectDelay    time.Duration
	maxReconnectDelay time.Duration
	connectWait       time.Duration
	connectPoll       time.Duration
}

type PublisherOption func(*Publisher)

func WithReconnectDelay(initial, max time.Duration) PublisherOption {
	return func(p *Publisher) {
		p.reconnectDelay = initial
		p.maxReconnectDelay = max
	}
}

func NewPublisher(client *Client, bufferSize int, dedupSvc DedupService, opts ...PublisherOption) *Publisher {
	p := &Publisher{
		client:            client,
		logger:            client.logger.With().Str("subcomponent", "publisher").Logger(),
		requests:          make(chan publishRequest, bufferSize),
		bufferSize:        bufferSize,
		dedupSvc:          dedupSvc,
		pending:           make(map[uint64]chan error),
		seqToMsgID:        make(map[uint64]string),
		returned:          make(map[string]amqp.Return),
		done:              make(chan struct{}),
		reconnectDelay:    time.Second,
		maxReconnectDelay: 30 * time.Second,
		connectWait:       3 * time.Second,
		connectPoll:       100 * time.Millisecond,
	}

	for _, opt := range opts {
		opt(p)
	}

	go p.run()
	return p
}

func (p *Publisher) run() {
	for {
		select {
		case <-p.done:
			return
		default:
		}

		if err := p.connect(); err != nil {
			p.logger.Warn().Err(err).Msg("connect failed, retrying")
			p.waitReconnect()
			continue
		}

		p.resetReconnectDelay()
		p.processLoop()
	}
}

func (p *Publisher) connect() error {
	conn := p.client.getConn()
	if conn == nil || conn.IsClosed() {
		return fmt.Errorf("connection not ready")
	}

	ch, err := conn.Channel()
	if err != nil {
		return fmt.Errorf("open channel: %w", err)
	}

	if err := ch.Confirm(false); err != nil {
		ch.Close()
		return fmt.Errorf("enable confirms: %w", err)
	}

	p.mu.Lock()
	p.ch = ch
	p.confirms = ch.NotifyPublish(make(chan amqp.Confirmation, p.bufferSize))
	p.returns = ch.NotifyReturn(make(chan amqp.Return, p.bufferSize))
	p.seqToMsgID = make(map[uint64]string)
	p.returned = make(map[string]amqp.Return)
	p.mu.Unlock()

	p.connected.Store(true)
	p.logger.Info().Msg("connected")

	return nil
}

func (p *Publisher) processLoop() {
	closeCh := make(chan *amqp.Error, 1)
	p.ch.NotifyClose(closeCh)

	confirmsDone := make(chan struct{})
	go func() {
		p.handleConfirmsAndReturns()
		close(confirmsDone)
	}()

	defer func() {
		p.connected.Store(false)
		p.mu.Lock()
		if p.ch != nil {
			p.ch.Close()
			p.ch = nil
		}
		p.mu.Unlock()
		<-confirmsDone
	}()

	for {
		select {
		case <-p.done:
			return

		case err := <-closeCh:
			p.logger.Warn().Err(err).Msg("channel closed")
			p.failAllPending(fmt.Errorf("channel closed: %v", err))
			return

		case req := <-p.requests:
			if err := p.publish(req); err != nil {
				// ошибка публикации — канал сломан
				p.logger.Error().Err(err).Msg("publish failed")
				p.failAllPending(err)
				return
			}
		}
	}
}

func (p *Publisher) publish(req publishRequest) error {
	p.mu.RLock()
	ch := p.ch
	p.mu.RUnlock()

	if ch == nil {
		req.result <- fmt.Errorf("no channel")
		return fmt.Errorf("no channel")
	}

	headers := amqp.Table{}
	for k, v := range req.msg.Headers {
		headers[k] = v
	}

	seqNo := ch.GetNextPublishSeqNo()

	// регистрируем ожидание ДО публикации
	p.mu.Lock()
	p.pending[seqNo] = req.result
	p.seqToMsgID[seqNo] = req.msg.MessageID
	p.mu.Unlock()

	err := ch.PublishWithContext(req.ctx,
		p.client.cfg.Exchange,
		req.msg.RoutingKey,
		true, false,
		amqp.Publishing{
			DeliveryMode: amqp.Persistent,
			ContentType:  "application/json",
			Body:         req.msg.Body,
			MessageId:    req.msg.MessageID,
			Timestamp:    time.Now(),
			Headers:      headers,
		},
	)

	if err != nil {
		p.mu.Lock()
		delete(p.pending, seqNo)
		delete(p.seqToMsgID, seqNo)
		p.mu.Unlock()
		req.result <- err
		return err
	}

	return nil
}

func (p *Publisher) handleConfirmsAndReturns() {
	p.mu.RLock()
	confirms := p.confirms
	returns := p.returns
	p.mu.RUnlock()

	if confirms == nil {
		return
	}

	for {
		// Приоритет: сначала дрейним returns (неблокирующе)
		select {
		case ret, ok := <-returns:
			if !ok {
				returns = nil
			} else {
				p.recordReturn(ret)
			}
			continue
		default:
		}

		// Затем ждём оба канала
		select {
		case ret, ok := <-returns:
			if !ok {
				returns = nil
			} else {
				p.recordReturn(ret)
			}

		case conf, ok := <-confirms:
			if !ok {
				return
			}
			p.resolveConfirm(conf)

		case <-p.done:
			return
		}
	}
}

func (p *Publisher) recordReturn(ret amqp.Return) {
	msgID := ret.MessageId
	p.logger.Warn().
		Str("message_id", msgID).
		Uint16("reply_code", ret.ReplyCode).
		Str("reply_text", ret.ReplyText).
		Str("routing_key", ret.RoutingKey).
		Msg("message returned: no route")

	if ret.ReplyCode == 312 {
		if err := p.ensureQueue(ret.RoutingKey); err != nil {
			p.logger.Error().Err(err).
				Str("routing_key", ret.RoutingKey).
				Msg("failed to auto-create queue after NO_ROUTE")
		}
	}

	p.mu.Lock()
	p.returned[msgID] = ret
	p.mu.Unlock()
}

func (p *Publisher) resolveConfirm(conf amqp.Confirmation) {
	p.mu.Lock()
	ch, exists := p.pending[conf.DeliveryTag]
	if exists {
		delete(p.pending, conf.DeliveryTag)
	}
	msgID := p.seqToMsgID[conf.DeliveryTag]
	delete(p.seqToMsgID, conf.DeliveryTag)
	ret, wasReturned := p.returned[msgID]
	if wasReturned {
		delete(p.returned, msgID)
	}
	p.mu.Unlock()

	if !exists {
		return
	}

	callMarkSeen := false
	if wasReturned {
		if ret.ReplyCode == 312 {
			// Queue was auto-created in recordReturn, retry publish
			go func() {
				err := p.Publish(context.Background(), PublishMessage{
					RoutingKey: ret.RoutingKey,
					Body:       ret.Body,
					MessageID:  ret.MessageId,
				})
				ch <- err
				close(ch)
			}()
			return
		}
		ch <- fmt.Errorf("message %s returned by broker: %d %s", msgID, ret.ReplyCode, ret.ReplyText)
	} else if conf.Ack {
		ch <- nil
		callMarkSeen = true
	} else {
		ch <- fmt.Errorf("nack for tag=%d", conf.DeliveryTag)
	}
	close(ch)

	if callMarkSeen && p.dedupSvc != nil && msgID != "" {
		if err := p.dedupSvc.MarkSeen(context.Background(), msgID); err != nil {
			p.logger.Warn().
				Str("component", "publisher").
				Str("messageID", msgID).
				Err(err).
				Msg("MarkSeen failed after ACK")
		}
	}
}

func (p *Publisher) ensureQueue(routingKey string) error {
	conn := p.client.getConn()
	if conn == nil || conn.IsClosed() {
		return fmt.Errorf("no connection")
	}

	ch, err := conn.Channel()
	if err != nil {
		return fmt.Errorf("open channel: %w", err)
	}
	defer ch.Close()

	_, err = ch.QueueDeclare(
		routingKey,
		true,  // durable
		false, // auto-delete
		false, // exclusive
		false, // no-wait
		nil,
	)
	if err != nil {
		return fmt.Errorf("declare queue %q: %w", routingKey, err)
	}

	err = ch.QueueBind(
		routingKey,
		routingKey,
		p.client.cfg.Exchange,
		false,
		nil,
	)
	if err != nil {
		return fmt.Errorf("bind queue %q: %w", routingKey, err)
	}

	p.logger.Info().
		Str("queue", routingKey).
		Str("exchange", p.client.cfg.Exchange).
		Msg("auto-created and bound queue after NO_ROUTE")

	return nil
}

func (p *Publisher) failAllPending(err error) {
	p.mu.Lock()
	defer p.mu.Unlock()

	for seqNo, ch := range p.pending {
		select {
		case ch <- err:
		default:
		}
		close(ch)
		delete(p.pending, seqNo)
	}

	for k := range p.seqToMsgID {
		delete(p.seqToMsgID, k)
	}
	for k := range p.returned {
		delete(p.returned, k)
	}
}

func (p *Publisher) waitReconnect() {
	delay := p.reconnectDelay

	select {
	case <-time.After(delay):
	case <-p.done:
		return
	}

	// exponential backoff
	p.reconnectDelay = min(p.reconnectDelay*2, p.maxReconnectDelay)
}

func (p *Publisher) resetReconnectDelay() {
	p.reconnectDelay = time.Second
}

// Publish — потокобезопасный метод
func (p *Publisher) Publish(ctx context.Context, msg PublishMessage) error {
	if err := p.waitUntilConnected(ctx); err != nil {
		return err
	}

	result := make(chan error, 1)
	req := publishRequest{
		msg:    msg,
		ctx:    ctx,
		result: result,
	}

	select {
	case p.requests <- req:
	case <-ctx.Done():
		return ctx.Err()
	case <-p.done:
		return fmt.Errorf("publisher closed")
	}

	select {
	case err := <-result:
		return err
	case <-ctx.Done():
		return ctx.Err()
	case <-p.done:
		return fmt.Errorf("publisher closed")
	}
}

func (p *Publisher) waitUntilConnected(ctx context.Context) error {
	if p.connected.Load() {
		return nil
	}

	if p.connectWait <= 0 {
		return fmt.Errorf("publisher not connected")
	}

	timer := time.NewTimer(p.connectWait)
	ticker := time.NewTicker(p.connectPoll)
	defer timer.Stop()
	defer ticker.Stop()

	for {
		if p.connected.Load() {
			return nil
		}

		select {
		case <-ctx.Done():
			return ctx.Err()
		case <-p.done:
			return fmt.Errorf("publisher closed")
		case <-timer.C:
			if p.connected.Load() {
				return nil
			}
			return fmt.Errorf("publisher not connected")
		case <-ticker.C:
		}
	}
}

// PublishWithRetry — публикация с повторами при временных ошибках
func (p *Publisher) PublishWithRetry(ctx context.Context, msg PublishMessage, maxRetries int) error {
	var lastErr error

	for i := 0; i <= maxRetries; i++ {
		if err := p.Publish(ctx, msg); err != nil {
			lastErr = err

			// не ретраим при отмене контекста
			if ctx.Err() != nil {
				return ctx.Err()
			}

			// ждём перед ретраем
			backoff := time.Duration(i+1) * 100 * time.Millisecond
			select {
			case <-time.After(backoff):
				continue
			case <-ctx.Done():
				return ctx.Err()
			}
		}
		return nil
	}

	return fmt.Errorf("after %d retries: %w", maxRetries, lastErr)
}

func (p *Publisher) IsConnected() bool {
	return p.connected.Load()
}

func (p *Publisher) Close() error {
	p.closeOnce.Do(func() {
		close(p.done)
		p.failAllPending(fmt.Errorf("publisher closed"))

		p.mu.Lock()
		if p.ch != nil {
			p.ch.Close()
		}
		p.mu.Unlock()
	})
	return nil
}
