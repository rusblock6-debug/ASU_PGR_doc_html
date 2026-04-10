package domain

import (
	"context"
	"wifi-event-dispatcher/server/serverpb"
)

type ServerRepository interface {
	StreamGetEvents(ctx context.Context) (serverpb.EventDispatchService_StreamBortGetEventsClient, error)
	StreamSendEvents(ctx context.Context) (serverpb.EventDispatchService_StreamBortSendEventsClient, error)
}
