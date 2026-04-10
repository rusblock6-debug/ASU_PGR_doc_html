package fxrabbitmq

import (
	"context"
	"time"
	"wifi-event-dispatcher/internal/dedup"
	"wifi-event-dispatcher/internal/rabbitmq"

	"github.com/rs/zerolog"
	"go.uber.org/fx"
)

var Module = fx.Module("rabbitmq",
	fx.Provide(NewClient, NewPublisher, NewManagementClient),
)

func NewManagementClient(cfg rabbitmq.Config, log zerolog.Logger) *rabbitmq.ManagementClient {
	logger := log.With().Str("component", "rabbitmq.management").Logger()
	return rabbitmq.NewManagementClient(cfg, logger)
}

func NewClient(lc fx.Lifecycle, cfg rabbitmq.Config, log zerolog.Logger) *rabbitmq.Client {
	logger := log.With().Str("component", "rabbitmq").Logger()
	client := rabbitmq.New(cfg, logger)

	lc.Append(fx.Hook{
		OnStart: func(ctx context.Context) error {
			return client.Start(ctx)
		},
		OnStop: func(ctx context.Context) error {
			logger.Info().Msg("rabbitmq stopping")
			return client.Close()
		},
	})

	return client
}

func NewPublisher(client *rabbitmq.Client, dedupSvc dedup.Service) *rabbitmq.Publisher {
	pub := rabbitmq.NewPublisher(client, 1000, dedupSvc,
		rabbitmq.WithReconnectDelay(time.Second, 30*time.Second))

	return pub
}
