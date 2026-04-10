package fxredis

import (
	"context"
	"wifi-event-dispatcher/internal/redis"

	goredis "github.com/redis/go-redis/v9"
	"github.com/rs/zerolog"
	"go.uber.org/fx"
)

// Module wires the Redis client into the Uber FX dependency graph.
// It mirrors the pattern of internal/fx/rabbitmq/module.go.
var Module = fx.Module("redis",
	fx.Provide(NewClient),
)

// NewClient constructs a *goredis.Client and registers lifecycle hooks
// that ping Redis on start (to fail fast on bad config) and close on stop.
func NewClient(lc fx.Lifecycle, cfg redis.Config, log zerolog.Logger) *goredis.Client {
	logger := log.With().Str("component", "redis").Logger()
	client := redis.NewClient(cfg)

	lc.Append(fx.Hook{
		OnStart: func(ctx context.Context) error {
			if err := client.Ping(ctx).Err(); err != nil {
				logger.Error().Err(err).Str("addr", cfg.Addr).Msg("redis ping failed")
				return err
			}
			logger.Info().Str("addr", cfg.Addr).Msg("redis connected")
			return nil
		},
		OnStop: func(ctx context.Context) error {
			logger.Info().Msg("redis stopping")
			return client.Close()
		},
	})

	return client
}
