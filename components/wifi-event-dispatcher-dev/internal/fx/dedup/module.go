package fxdedup

import (
	"wifi-event-dispatcher/internal/dedup"
	"wifi-event-dispatcher/internal/redis"

	goredis "github.com/redis/go-redis/v9"
	"github.com/rs/zerolog"
	"go.uber.org/fx"
)

// Module wires DedupService into the Uber FX dependency graph.
// It depends on *redis.Client (provided by fxredis.Module) and redis.Config.
var Module = fx.Module("dedup",
	fx.Provide(NewService),
)

// NewService constructs a dedup.Service from the Redis client and config.
func NewService(client *goredis.Client, cfg redis.Config, log zerolog.Logger) dedup.Service {
	return dedup.New(client, cfg.DedupTTL, log)
}
