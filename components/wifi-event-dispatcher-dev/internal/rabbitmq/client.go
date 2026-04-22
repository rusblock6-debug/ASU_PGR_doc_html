package rabbitmq

import (
	"context"
	"fmt"
	"sync"
	"time"

	amqp "github.com/rabbitmq/amqp091-go"
	"github.com/rs/zerolog"
)

type Client struct {
	cfg    Config
	logger zerolog.Logger

	mu   sync.RWMutex
	conn *amqp.Connection

	closed chan struct{}
	once   sync.Once
}

func New(cfg Config, logger zerolog.Logger) *Client {
	if cfg.ExchangeType == "" {
		cfg.ExchangeType = "topic"
	}
	if cfg.ReconnectMin == 0 {
		cfg.ReconnectMin = 500 * time.Millisecond
	}
	if cfg.ReconnectMax == 0 {
		cfg.ReconnectMax = 10 * time.Second
	}

	return &Client{cfg: cfg, logger: logger, closed: make(chan struct{})}
}

func (c *Client) Start(_ context.Context) error {
	if err := c.connectAndInit(); err != nil {
		return err
	}
	go c.reconnectLoop()
	return nil
}

func (c *Client) Close() error {
	var err error
	c.once.Do(func() {
		c.logger.Info().Msg("closing")
		close(c.closed)
		c.mu.Lock()
		defer c.mu.Unlock()
		if c.conn != nil {
			err = c.conn.Close()
		}
	})
	return err
}

func (c *Client) connectAndInit() error {
	config := amqp.Config{
		Heartbeat: 10 * time.Second,
		Locale:    "en_US",
	}
	conn, err := amqp.DialConfig(c.cfg.Url(), config)
	if err != nil {
		return err
	}

	// topology: exchange — use a temporary channel
	if c.cfg.Exchange != "" {
		ch, err := conn.Channel()
		if err != nil {
			_ = conn.Close()
			return fmt.Errorf("open topology channel: %w", err)
		}

		if err := ch.ExchangeDeclare(
			c.cfg.Exchange,
			c.cfg.ExchangeType,
			true,  // durable
			false, // auto-delete
			false, false,
			nil,
		); err != nil {
			_ = ch.Close()
			_ = conn.Close()
			return fmt.Errorf("exchange declare: %w", err)
		}

		_ = ch.Close()
	}

	c.mu.Lock()
	c.conn = conn
	c.mu.Unlock()

	c.logger.Info().Msg("connected")
	return nil
}

func (c *Client) reconnectLoop() {
	backoff := c.cfg.ReconnectMin

	for {
		conn := c.getConn()
		if conn == nil {
			return
		}

		notify := conn.NotifyClose(make(chan *amqp.Error, 1))

		select {
		case <-c.closed:
			return
		case <-notify:
			c.logger.Warn().Msg("connection lost, reconnecting")
		}

		for {
			select {
			case <-c.closed:
				return
			default:
			}

			if err := c.connectAndInit(); err != nil {
				c.logger.Warn().Err(err).Msg("reconnect failed")
				time.Sleep(backoff)
				backoff *= 2
				if backoff > c.cfg.ReconnectMax {
					backoff = c.cfg.ReconnectMax
				}
				continue
			}

			c.logger.Info().Msg("reconnected")
			backoff = c.cfg.ReconnectMin
			break
		}
	}
}

func (c *Client) getConn() *amqp.Connection {
	c.mu.RLock()
	defer c.mu.RUnlock()
	return c.conn
}

// newConsumerChannel opens a new channel on the current connection for consumers.
func (c *Client) newConsumerChannel() (*amqp.Channel, error) {
	conn := c.getConn()
	if conn == nil {
		return nil, fmt.Errorf("no connection")
	}
	return conn.Channel()
}
