package infrastructure

import (
	"context"
	"errors"
	"wifi-event-dispatcher/domain"
	"wifi-event-dispatcher/internal/dedup"
	"wifi-event-dispatcher/internal/rabbitmq"
	"wifi-event-dispatcher/server/internal/application"

	"github.com/rs/zerolog"
)

var _ application.Publisher = (*EventPublisher)(nil)

// rabbitPublisher is a narrow interface over rabbitmq.Publisher for testability.
type rabbitPublisher interface {
	Publish(ctx context.Context, msg rabbitmq.PublishMessage) error
}

type EventPublisher struct {
	publisher rabbitPublisher
	dedup     dedup.Service
	log       zerolog.Logger
}

func NewEventPublisher(publisher *rabbitmq.Publisher, svc dedup.Service, log zerolog.Logger) *EventPublisher {
	return &EventPublisher{
		publisher: publisher,
		dedup:     svc,
		log:       log.With().Str("component", "publisher").Logger(),
	}
}

func (e *EventPublisher) Publish(ctx context.Context, event *domain.Event) error {
	if event.MessageID == "" {
		return errors.New("event MessageID must not be empty")
	}

	dup, err := e.dedup.IsDuplicate(ctx, event.MessageID)
	if err != nil {
		e.log.Warn().Err(err).Str("messageID", event.MessageID).Msg("dedup Redis error, proceeding with publish")
	} else if dup {
		e.log.Warn().Str("messageID", event.MessageID).Msg("duplicate message, skipping publish")
		return nil
	}

	return e.publisher.Publish(ctx, rabbitmq.PublishMessage{
		MessageID:  event.MessageID,
		Body:       event.Payload,
		RoutingKey: event.Topic,
	})
}
