package rabbitmq

import (
	"context"
	"fmt"

	amqp "github.com/rabbitmq/amqp091-go"
)

type Subscription struct {
	cancel context.CancelFunc
	done   chan struct{}
}

func (s *Subscription) Stop() error {
	s.cancel()
	<-s.done
	return nil
}

type SubscribeChanOptions struct {
	Queue        string
	RoutingKey   string
	ConsumerTag  string
	Prefetch     int
	QueueArgs    amqp.Table
	ConsumerArgs amqp.Table
}

type ChanSubscription struct {
	msgs      <-chan amqp.Delivery
	ch        *amqp.Channel
	cancel    context.CancelFunc
	done      chan struct{}
	queueName string
}

func (s *ChanSubscription) Messages() <-chan amqp.Delivery {
	return s.msgs
}

func (s *ChanSubscription) QueueName() string {
	return s.queueName
}

func (s *ChanSubscription) Stop() error {
	s.cancel()
	<-s.done
	return nil
}

func (c *Client) SubscribeChan(ctx context.Context, opt SubscribeChanOptions) (*ChanSubscription, error) {
	if opt.Queue == "" {
		return nil, fmt.Errorf("queue required")
	}
	if opt.Prefetch <= 0 {
		opt.Prefetch = 1
	}

	c.logger.Info().Str("queue", opt.Queue).Str("routing_key", opt.RoutingKey).Msg("subscribing")

	ch, err := c.newConsumerChannel()
	if err != nil {
		c.logger.Error().Err(err).Str("queue", opt.Queue).Msg("failed to open consumer channel")
		return nil, err
	}

	if err := ch.Qos(opt.Prefetch, 0, false); err != nil {
		_ = ch.Close()
		return nil, err
	}

	_, err = ch.QueueDeclarePassive(
		opt.Queue,
		true,  // durable
		false, // auto-delete
		false, // exclusive
		false,
		opt.QueueArgs,
	)
	if err != nil {
		_ = ch.Close()
		c.logger.Warn().Str("queue", opt.Queue).Msg("queue does not exist")
		return nil, err
	}

	if opt.RoutingKey != "" {
		if err := ch.QueueBind(opt.Queue, opt.RoutingKey, c.cfg.Exchange, false, nil); err != nil {
			_ = ch.Close()
			return nil, err
		}
	}

	msgs, err := ch.Consume(
		opt.Queue,
		opt.ConsumerTag,
		false, // autoAck = false
		false, false, false, opt.ConsumerArgs,
	)
	if err != nil {
		_ = ch.Close()
		return nil, err
	}

	subCtx, cancel := context.WithCancel(ctx)
	done := make(chan struct{})

	go func() {
		defer close(done)
		<-subCtx.Done()
		_ = ch.Close()
	}()

	return &ChanSubscription{
		msgs:      msgs,
		ch:        ch,
		cancel:    cancel,
		done:      done,
		queueName: opt.Queue,
	}, nil
}
