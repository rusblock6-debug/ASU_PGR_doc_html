package application

import (
	"context"
	"errors"
	"testing"
	"wifi-event-dispatcher/domain"
	"wifi-event-dispatcher/internal/rabbitmq"

	amqp "github.com/rabbitmq/amqp091-go"
	"go.uber.org/mock/gomock"
)

func TestNew(t *testing.T) {
	ctrl := gomock.NewController(t)

	subscriber := NewMockSubscriber(ctrl)
	publisher := NewMockPublisher(ctrl)
	discovery := NewMockQueueDiscoverer(ctrl)

	a := New(subscriber, publisher, discovery)
	if a == nil {
		t.Fatal("expected non-nil App, got nil")
	}
}

func TestHandleEvent_Success(t *testing.T) {
	ctrl := gomock.NewController(t)

	ctx := context.Background()
	event := &domain.Event{
		Topic:     "test.topic",
		MessageID: "msg-123",
		Payload:   []byte("payload"),
	}

	subscriber := NewMockSubscriber(ctrl)
	publisher := NewMockPublisher(ctrl)
	discovery := NewMockQueueDiscoverer(ctrl)

	publisher.EXPECT().
		Publish(ctx, event).
		Return(nil)

	a := New(subscriber, publisher, discovery)

	err := a.HandleEvent(ctx, event)
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}
}

func TestHandleEvent_Error(t *testing.T) {
	ctrl := gomock.NewController(t)

	ctx := context.Background()
	event := &domain.Event{
		Topic:     "test.topic",
		MessageID: "msg-456",
		Payload:   []byte("payload"),
	}

	publishErr := errors.New("publish failed")

	subscriber := NewMockSubscriber(ctrl)
	publisher := NewMockPublisher(ctrl)
	discovery := NewMockQueueDiscoverer(ctrl)

	publisher.EXPECT().
		Publish(ctx, event).
		Return(publishErr)

	a := New(subscriber, publisher, discovery)

	err := a.HandleEvent(ctx, event)
	if err == nil {
		t.Fatal("expected error, got nil")
	}
	if !errors.Is(err, publishErr) {
		t.Fatalf("expected error %v, got %v", publishErr, err)
	}
}

func TestSubscribeAll_Success(t *testing.T) {
	ctrl := gomock.NewController(t)

	ctx := context.Background()
	truckID := 42

	subscriber := NewMockSubscriber(ctrl)
	publisher := NewMockPublisher(ctrl)
	discovery := NewMockQueueDiscoverer(ctrl)

	discoveredQueue := "server.bort_42.trip.src"
	discovery.EXPECT().
		DiscoverQueues(ctx, domain.ServerQueuePattern(truckID)).
		Return([]string{discoveredQueue}, nil)

	expectedOpt := rabbitmq.SubscribeChanOptions{
		Queue:    discoveredQueue,
		Prefetch: 1,
		ConsumerArgs: amqp.Table{
			"x-priority": int32(10),
		},
	}

	subscriber.EXPECT().
		SubscribeChan(ctx, expectedOpt).
		Return((*rabbitmq.ChanSubscription)(nil), nil)

	a := New(subscriber, publisher, discovery)

	subs, err := a.SubscribeAll(ctx, truckID)
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}
	if len(subs) != 1 {
		t.Fatalf("expected 1 subscription, got %d", len(subs))
	}
}

func TestSubscribeAll_SkipsMissingQueue(t *testing.T) {
	ctrl := gomock.NewController(t)

	ctx := context.Background()
	truckID := 7

	subscriber := NewMockSubscriber(ctrl)
	publisher := NewMockPublisher(ctrl)
	discovery := NewMockQueueDiscoverer(ctrl)

	discoveredQueue := "server.bort_7.trip.src"
	discovery.EXPECT().
		DiscoverQueues(ctx, domain.ServerQueuePattern(truckID)).
		Return([]string{discoveredQueue}, nil)

	subscribeErr := errors.New("queue does not exist")
	expectedOpt := rabbitmq.SubscribeChanOptions{
		Queue:    discoveredQueue,
		Prefetch: 1,
		ConsumerArgs: amqp.Table{
			"x-priority": int32(10),
		},
	}

	subscriber.EXPECT().
		SubscribeChan(ctx, expectedOpt).
		Return(nil, subscribeErr)

	a := New(subscriber, publisher, discovery)

	subs, err := a.SubscribeAll(ctx, truckID)
	if err != nil {
		t.Fatalf("expected no error, got %v", err)
	}
	if len(subs) != 0 {
		t.Fatalf("expected 0 subscriptions, got %d", len(subs))
	}
}
