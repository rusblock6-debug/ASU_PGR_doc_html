package application

import (
	"context"
	"fmt"
	"wifi-event-dispatcher/domain"
	"wifi-event-dispatcher/internal/rabbitmq"

	amqp "github.com/rabbitmq/amqp091-go"
)

type Subscriber interface {
	SubscribeChan(ctx context.Context, opt rabbitmq.SubscribeChanOptions) (*rabbitmq.ChanSubscription, error)
}

type QueueDiscoverer interface {
	DiscoverQueues(ctx context.Context, nameRegex string) ([]string, error)
}

type App interface {
	HandleEvent(ctx context.Context, event *domain.Event) error
	SubscribeAll(ctx context.Context, truckID int) ([]*rabbitmq.ChanSubscription, error)
}

type app struct {
	subscriber Subscriber
	publisher  Publisher
	discovery  QueueDiscoverer
}

var _ App = (*app)(nil)

func New(subscriber Subscriber, publisher Publisher, discovery QueueDiscoverer) App {
	return &app{publisher: publisher, subscriber: subscriber, discovery: discovery}
}

func (a *app) HandleEvent(ctx context.Context, event *domain.Event) error {
	err := a.publisher.Publish(ctx, event)
	return err
}

func (a *app) subscribe(ctx context.Context, queueName string) (*rabbitmq.ChanSubscription, error) {
	sub, err := a.subscriber.SubscribeChan(ctx, rabbitmq.SubscribeChanOptions{
		Queue:    queueName,
		Prefetch: 1,
		ConsumerArgs: amqp.Table{
			"x-priority": int32(10),
		},
	})
	if err != nil {
		return nil, err
	}

	return sub, nil
}

func (a *app) SubscribeAll(ctx context.Context, truckID int) ([]*rabbitmq.ChanSubscription, error) {
	pattern := domain.ServerQueuePattern(truckID)
	queues, err := a.discovery.DiscoverQueues(ctx, pattern)
	if err != nil {
		return nil, fmt.Errorf("discover queues: %w", err)
	}

	subs := make([]*rabbitmq.ChanSubscription, 0, len(queues))
	for _, queueName := range queues {
		sub, err := a.subscribe(ctx, queueName)
		if err != nil {
			continue
		}
		subs = append(subs, sub)
	}

	return subs, nil
}
