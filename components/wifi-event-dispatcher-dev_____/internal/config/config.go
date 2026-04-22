package config

import (
	"time"
	"wifi-event-dispatcher/internal/rabbitmq"
	"wifi-event-dispatcher/internal/redis"

	"github.com/joho/godotenv"
	"github.com/kelseyhightower/envconfig"
	"github.com/rs/zerolog/log"
)

type CommonConfig struct {
	Environment     string          `envconfig:"ENVIRONMENT" default:"development"`
	ShutdownTimeout time.Duration   `envconfig:"SHUTDOWN_TIMEOUT" default:"30s"`
	LogLevel        string          `envconfig:"LOG_LEVEL" default:"DEBUG"`
	RabbitmqConfig  rabbitmq.Config `envconfig:"RABBIT"`
	RedisConfig     redis.Config    `envconfig:"REDIS"`
}

// AutorepubConfig is a runtime-only DTO passed to the autorepub client.
// Populated from each AppConfig's own fields, which carry envconfig tags with
// per-deployment defaults.
type AutorepubConfig struct {
	CoordinationURL      string
	DistributionPort     string
	AutorepubHTTPTimeout time.Duration
}

type ServerAppConfig struct {
	CommonConfig
	Server               ServerConfig  `envconfig:"SERVER"`
	CoordinationURL      string        `envconfig:"COORDINATION_URL" default:"http://sync-service:8000"`
	DistributionPort     string        `envconfig:"DISTRIBUTION_PORT" default:"8000"`
	AutorepubHTTPTimeout time.Duration `envconfig:"AUTOREPUB_HTTP_TIMEOUT" default:"10s"`
}

func (c *ServerAppConfig) AutorepubConfig() AutorepubConfig {
	return AutorepubConfig{
		CoordinationURL:      c.CoordinationURL,
		DistributionPort:     c.DistributionPort,
		AutorepubHTTPTimeout: c.AutorepubHTTPTimeout,
	}
}

type BortAppConfig struct {
	CommonConfig
	Bort                 BortConfig    `envconfig:"BORT"`
	CoordinationURL      string        `envconfig:"COORDINATION_URL" default:"http://sync-service:8000" `
	DistributionPort     string        `envconfig:"DISTRIBUTION_PORT" default:"8000"`
	AutorepubHTTPTimeout time.Duration `envconfig:"AUTOREPUB_HTTP_TIMEOUT" default:"10s"`
}

func (c *BortAppConfig) AutorepubConfig() AutorepubConfig {
	return AutorepubConfig{
		CoordinationURL:      c.CoordinationURL,
		DistributionPort:     c.DistributionPort,
		AutorepubHTTPTimeout: c.AutorepubHTTPTimeout,
	}
}

func loadEnv() {
	err := godotenv.Load()
	if err != nil {
		log.Info().Msg("Файл .env не найден, используем системные переменные")
	}
}

func LoadServerConfig() (*ServerAppConfig, error) {
	loadEnv()
	var cfg ServerAppConfig
	if err := envconfig.Process("", &cfg); err != nil {
		return nil, err
	}
	return &cfg, nil
}

func LoadBortConfig() (*BortAppConfig, error) {
	loadEnv()
	var cfg BortAppConfig
	if err := envconfig.Process("", &cfg); err != nil {
		return nil, err
	}
	return &cfg, nil
}
