package bort

import (
	"context"

	"wifi-event-dispatcher/bort/internal/application"
	"wifi-event-dispatcher/bort/internal/domain"
	bortgrpc "wifi-event-dispatcher/bort/internal/grpc"
	"wifi-event-dispatcher/internal/config"
	"wifi-event-dispatcher/internal/rabbitmq"

	"go.uber.org/fx"
	"google.golang.org/grpc"
)

var Module = fx.Module("bort",
	fx.Provide(
		NewGRPCConn,
		AsServerRepository(bortgrpc.NewServerRepository),
		NewEventPublisher,
		NewRabbitSubscriber,
		NewBortQueueDiscoverer,
		application.New,
	),
	fx.Invoke(RunApp),
)

func NewEventPublisher(pub *rabbitmq.Publisher) application.EventPublisher {
	return pub
}

func NewRabbitSubscriber(client *rabbitmq.Client) application.RabbitSubscriber {
	return client
}

func NewBortQueueDiscoverer(mc *rabbitmq.ManagementClient) application.QueueDiscoverer {
	return mc
}

func NewGRPCConn(lc fx.Lifecycle, cfg config.BortConfig) (*grpc.ClientConn, error) {
	conn, err := bortgrpc.NewClient(context.Background(), cfg.ServerAddress)
	if err != nil {
		return nil, err
	}

	lc.Append(fx.Hook{
		OnStop: func(ctx context.Context) error {
			return conn.Close()
		},
	})

	return conn, nil
}

func AsServerRepository(f any) any {
	return fx.Annotate(f, fx.As(new(domain.ServerRepository)))
}

func RunApp(lc fx.Lifecycle, app application.App) {
	var cancel context.CancelFunc

	lc.Append(fx.Hook{
		OnStart: func(ctx context.Context) error {
			var appCtx context.Context
			appCtx, cancel = context.WithCancel(context.Background())
			go app.Start(appCtx)
			return nil
		},
		OnStop: func(ctx context.Context) error {
			if cancel != nil {
				cancel()
			}
			return nil
		},
	})
}
