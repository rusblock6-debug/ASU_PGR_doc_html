package application

import (
	"context"
	"wifi-event-dispatcher/domain"
)

type Publisher interface {
	Publish(ctx context.Context, event *domain.Event) error
}
