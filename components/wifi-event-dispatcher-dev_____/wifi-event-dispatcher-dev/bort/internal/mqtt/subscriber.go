package mqtt

import (
	"context"
	"time"

	mqtt "github.com/eclipse/paho.mqtt.golang"
	"github.com/rs/zerolog"
)

type Handler func(ctx context.Context, msg mqtt.Message)

type Route struct {
	Topic   string
	QoS     byte
	Handler Handler
}

type Subscriber struct {
	client mqtt.Client
	routes []Route
	ctx    context.Context
	logger *zerolog.Logger
}

func NewSubscriber(broker, clientID string, routes []Route, logger *zerolog.Logger) *Subscriber {
	s := &Subscriber{
		routes: routes,
		logger: logger,
	}

	opts := mqtt.NewClientOptions()
	opts.AddBroker(broker)
	opts.SetClientID(clientID)
	opts.OnConnect = func(_ mqtt.Client) {
		s.logger.Info().Str("clientID", clientID).Msg("client connected")
	}
	opts.OnConnectionLost = func(_ mqtt.Client, err error) {
		s.logger.Warn().Err(err).Str("clientID", clientID).Msg("client disconnected")
	}
	opts.SetAutoReconnect(true)
	opts.SetKeepAlive(60 * time.Second)

	s.client = mqtt.NewClient(opts)
	return s
}

func (s *Subscriber) Start(ctx context.Context) error {
	s.ctx = ctx

	if token := s.client.Connect(); token.Wait() && token.Error() != nil {
		return token.Error()
	}

	for _, r := range s.routes {
		r := r
		callback := func(_ mqtt.Client, msg mqtt.Message) {
			r.Handler(s.ctx, msg)
		}
		if token := s.client.Subscribe(r.Topic, r.QoS, callback); token.Wait() && token.Error() != nil {
			return token.Error()
		}
		s.logger.Info().Msgf("Subscribed to: %s\n", r.Topic)
	}

	<-ctx.Done()

	for _, r := range s.routes {
		s.client.Unsubscribe(r.Topic)
	}
	s.client.Disconnect(250)
	return ctx.Err()
}
