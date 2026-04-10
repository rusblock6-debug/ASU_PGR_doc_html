package main

import (
	"wifi-event-dispatcher/bort"
	fxautorepub "wifi-event-dispatcher/internal/fx/autorepub"
	fxconfig "wifi-event-dispatcher/internal/fx/config"
	fxdedup "wifi-event-dispatcher/internal/fx/dedup"
	fxlogger "wifi-event-dispatcher/internal/fx/logger"
	fxrabbitmq "wifi-event-dispatcher/internal/fx/rabbitmq"
	fxredis "wifi-event-dispatcher/internal/fx/redis"

	"go.uber.org/fx"
)

func main() {
	fx.New(
		fxconfig.BortModule,
		fxlogger.Module,
		fxrabbitmq.Module,
		fxredis.Module,
		fxdedup.Module,
		fxautorepub.Module,
		bort.Module,
	).Run()
}
