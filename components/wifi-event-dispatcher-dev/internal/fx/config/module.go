package fxconfig

import (
	"time"
	"wifi-event-dispatcher/internal/config"
	"wifi-event-dispatcher/internal/rabbitmq"
	"wifi-event-dispatcher/internal/redis"

	"go.uber.org/fx"
)

type ServerConfig struct {
	Address         string
	ShutdownTimeout time.Duration
}

var ServerModule = fx.Module("config",
	fx.Provide(
		config.LoadServerConfig,
		func(cfg *config.ServerAppConfig) *config.CommonConfig {
			return &cfg.CommonConfig
		},
		func(cfg *config.ServerAppConfig) rabbitmq.Config {
			return cfg.RabbitmqConfig
		},
		func(cfg *config.ServerAppConfig) redis.Config {
			return cfg.RedisConfig
		},
		func(cfg *config.ServerAppConfig) ServerConfig {
			return ServerConfig{
				Address:         cfg.Server.Rpc.Address(),
				ShutdownTimeout: cfg.ShutdownTimeout,
			}
		},
		func(cfg *config.ServerAppConfig) config.AutorepubConfig {
			return cfg.AutorepubConfig()
		},
	),
)

var BortModule = fx.Module("config",
	fx.Provide(
		config.LoadBortConfig,
		func(cfg *config.BortAppConfig) *config.CommonConfig {
			return &cfg.CommonConfig
		},
		func(cfg *config.BortAppConfig) rabbitmq.Config {
			return cfg.RabbitmqConfig
		},
		func(cfg *config.BortAppConfig) redis.Config {
			return cfg.RedisConfig
		},
		func(cfg *config.BortAppConfig) config.BortConfig {
			return cfg.Bort
		},
		func(cfg *config.BortAppConfig) config.AutorepubConfig {
			return cfg.AutorepubConfig()
		},
	),
)
