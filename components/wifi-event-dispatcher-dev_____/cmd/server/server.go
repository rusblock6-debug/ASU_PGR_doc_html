package main

import (
	fxautorepub "wifi-event-dispatcher/internal/fx/autorepub"
	fxconfig "wifi-event-dispatcher/internal/fx/config"
	fxdedup "wifi-event-dispatcher/internal/fx/dedup"
	fxgrpc "wifi-event-dispatcher/internal/fx/grpc"
	fxlogger "wifi-event-dispatcher/internal/fx/logger"
	fxrabbitmq "wifi-event-dispatcher/internal/fx/rabbitmq"
	fxredis "wifi-event-dispatcher/internal/fx/redis"
	"wifi-event-dispatcher/server"

	"go.uber.org/fx"
)

func main() {
	fx.New(
		fxconfig.ServerModule,
		fxlogger.Module,
		fxrabbitmq.Module,
		fxredis.Module,
		fxdedup.Module,
		fxautorepub.Module,
		fxgrpc.Module,
		server.Module,
	).Run()
}
