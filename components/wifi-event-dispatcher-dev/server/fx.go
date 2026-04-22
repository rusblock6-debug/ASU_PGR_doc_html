package server

import (
	"wifi-event-dispatcher/internal/dedup"
	fxgrpc "wifi-event-dispatcher/internal/fx/grpc"
	"wifi-event-dispatcher/internal/rabbitmq"
	"wifi-event-dispatcher/server/internal/application"
	"wifi-event-dispatcher/server/internal/grpc"
	"wifi-event-dispatcher/server/internal/infrastructure"

	"github.com/rs/zerolog"
	"go.uber.org/fx"
)

var Module = fx.Module("server",
	fx.Provide(
		NewEventPublisher,
		NewSubscriber,
		NewQueueDiscoverer,
		application.New,
		AsServiceRegistrar(grpc.RegisterServer),
	),
)

func NewEventPublisher(pub *rabbitmq.Publisher, svc dedup.Service, log zerolog.Logger) application.Publisher {
	return infrastructure.NewEventPublisher(pub, svc, log)
}

func NewSubscriber(client *rabbitmq.Client) application.Subscriber {
	return client
}

func NewQueueDiscoverer(mc *rabbitmq.ManagementClient) application.QueueDiscoverer {
	return mc
}

func AsServiceRegistrar(f any) any {
	return fx.Annotate(f,
		fx.As(new(fxgrpc.ServiceRegistrar)),
		fx.ResultTags(`group:"grpc_services"`),
	)
}
