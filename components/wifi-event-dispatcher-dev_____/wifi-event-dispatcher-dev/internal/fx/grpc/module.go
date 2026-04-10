package fxgrpc

import (
	"context"
	"net"
	"time"

	fxconfig "wifi-event-dispatcher/internal/fx/config"

	"github.com/rs/zerolog"
	"go.uber.org/fx"
	"google.golang.org/grpc"
	"google.golang.org/grpc/reflection"
)

var Module = fx.Module("grpc",
	fx.Provide(NewServer),
	fx.Invoke(func(*grpc.Server) {}), // force eager instantiation
)

type ServiceRegistrar interface {
	Register(grpc.ServiceRegistrar)
}

type ServerParams struct {
	fx.In
	LC         fx.Lifecycle
	Log        zerolog.Logger
	Cfg        fxconfig.ServerConfig
	Registrars []ServiceRegistrar `group:"grpc_services"`
}

func NewServer(p ServerParams) *grpc.Server {
	server := grpc.NewServer()
	reflection.Register(server)

	for _, r := range p.Registrars {
		r.Register(server)
	}

	p.LC.Append(fx.Hook{
		OnStart: func(ctx context.Context) error {
			lis, err := net.Listen("tcp", p.Cfg.Address)
			if err != nil {
				return err
			}
			go func() {
				p.Log.Info().Str("addr", p.Cfg.Address).Msg("grpc starting")
				server.Serve(lis)
			}()
			return nil
		},
		OnStop: func(ctx context.Context) error {
			p.Log.Info().Msg("grpc stopping")
			stopped := make(chan struct{})
			go func() {
				server.GracefulStop()
				close(stopped)
			}()
			select {
			case <-time.After(p.Cfg.ShutdownTimeout):
				server.Stop()
			case <-stopped:
			}
			return nil
		},
	})

	return server
}
