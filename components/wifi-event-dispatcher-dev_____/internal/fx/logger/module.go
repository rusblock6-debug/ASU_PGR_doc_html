package fxlogger

import (
	"wifi-event-dispatcher/internal/config"
	"wifi-event-dispatcher/internal/logger"

	"github.com/rs/zerolog"
	"go.uber.org/fx"
	//"go.uber.org/fx/fxevent"
)

var Module = fx.Module("logger",
	fx.Provide(NewLogger),
)

//var WithLogger = fx.WithLogger(func(log zerolog.Logger) fxevent.Logger {
//	l := log.With().Str("component", "fx").Logger()
//	return &zerologFxLogger{logger: l}
//})

func NewLogger(cfg *config.CommonConfig) zerolog.Logger {
	return logger.New(logger.LogConfig{
		Environment: cfg.Environment,
		LogLevel:    logger.Level(cfg.LogLevel),
	})
}

//type zerologFxLogger struct {
//	logger zerolog.Logger
//}
//
//func (l *zerologFxLogger) LogEvent(event fxevent.Event) {
//	switch e := event.(type) {
//	case *fxevent.Provided:
//		if e.Err != nil {
//			l.logger.Error().Err(e.Err).Str("module", e.ModuleName).Msg("provide failed")
//		}
//	case *fxevent.Invoked:
//		if e.Err != nil {
//			l.logger.Error().Err(e.Err).Str("function", e.FunctionName).Msg("invoke failed")
//		}
//	case *fxevent.Started:
//		if e.Err != nil {
//			l.logger.Error().Err(e.Err).Msg("start failed")
//		} else {
//			l.logger.Info().Msg("started")
//		}
//	case *fxevent.Stopped:
//		if e.Err != nil {
//			l.logger.Error().Err(e.Err).Msg("stop failed")
//		} else {
//			l.logger.Info().Msg("stopped")
//		}
//	case *fxevent.Stopping:
//		l.logger.Info().Str("signal", e.Signal.String()).Msg("stopping")
//	case *fxevent.OnStartExecuted:
//		if e.Err != nil {
//			l.logger.Error().Err(e.Err).Str("callee", e.FunctionName).Msg("OnStart hook failed")
//		}
//	case *fxevent.OnStopExecuted:
//		if e.Err != nil {
//			l.logger.Error().Err(e.Err).Str("callee", e.FunctionName).Msg("OnStop hook failed")
//		}
//	case *fxevent.RollingBack:
//		l.logger.Error().Err(e.StartErr).Msg("rolling back")
//	case *fxevent.RolledBack:
//		if e.Err != nil {
//			l.logger.Error().Err(e.Err).Msg("rollback failed")
//		}
//	case *fxevent.LoggerInitialized:
//		if e.Err != nil {
//			l.logger.Error().Err(e.Err).Msg("logger init failed")
//		}
//	case *fxevent.Run:
//		if e.Err != nil {
//			l.logger.Error().Err(e.Err).
//				Str("name", e.Name).
//				Str("module", e.ModuleName).
//				Msg("run failed")
//		}
//	}
//}
//
