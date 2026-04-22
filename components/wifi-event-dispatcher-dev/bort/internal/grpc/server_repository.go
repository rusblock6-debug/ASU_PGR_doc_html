package grpc

import (
	"context"
	"wifi-event-dispatcher/bort/internal/domain"
	"wifi-event-dispatcher/server/serverpb"

	"google.golang.org/grpc"
)

type ServerRepository struct {
	client serverpb.EventDispatchServiceClient
}

var _ domain.ServerRepository = (*ServerRepository)(nil)

func NewServerRepository(conn *grpc.ClientConn) *ServerRepository {
	return &ServerRepository{
		client: serverpb.NewEventDispatchServiceClient(conn),
	}
}

func (r *ServerRepository) StreamGetEvents(ctx context.Context) (serverpb.EventDispatchService_StreamBortGetEventsClient, error) {
	return r.client.StreamBortGetEvents(ctx)
}

func (r *ServerRepository) StreamSendEvents(ctx context.Context) (serverpb.EventDispatchService_StreamBortSendEventsClient, error) {
	return r.client.StreamBortSendEvents(ctx)
}
