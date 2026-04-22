package fxautorepub

import (
	"wifi-event-dispatcher/internal/autorepub"
	"wifi-event-dispatcher/internal/config"

	"github.com/rs/zerolog"
	"go.uber.org/fx"
)

var Module = fx.Module("autorepub",
	fx.Provide(NewClient),
)

func NewClient(cfg config.AutorepubConfig, log zerolog.Logger) *autorepub.Client {
	logger := log.With().Str("component", "autorepub").Logger()
	return autorepub.NewClient(
		cfg.CoordinationURL,
		cfg.DistributionPort,
		cfg.AutorepubHTTPTimeout,
		logger,
	)
}
