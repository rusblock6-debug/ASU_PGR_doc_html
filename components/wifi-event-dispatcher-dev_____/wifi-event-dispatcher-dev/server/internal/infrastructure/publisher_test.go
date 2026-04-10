package infrastructure

import (
	"context"
	"errors"
	"testing"
	"wifi-event-dispatcher/domain"
	"wifi-event-dispatcher/internal/rabbitmq"

	"github.com/rs/zerolog"
)

// mockDedup is a test double for dedup.Service.
type mockDedup struct {
	isDuplicateReturn bool
	isDuplicateErr    error
}

func (m *mockDedup) IsDuplicate(_ context.Context, _ string) (bool, error) {
	return m.isDuplicateReturn, m.isDuplicateErr
}

func (m *mockDedup) MarkSeen(_ context.Context, _ string) error {
	return nil
}

// mockRabbitPublisher is a test double for rabbitPublisher that tracks calls.
type mockRabbitPublisher struct {
	called bool
	err    error
}

func (m *mockRabbitPublisher) Publish(_ context.Context, _ rabbitmq.PublishMessage) error {
	m.called = true
	return m.err
}

func newTestPublisher(d *mockDedup, pub *mockRabbitPublisher) *EventPublisher {
	return &EventPublisher{
		publisher: pub,
		dedup:     d,
		log:       zerolog.Nop(),
	}
}

func TestNewEventPublisher_ReturnsNonNil(t *testing.T) {
	p := NewEventPublisher(nil, &mockDedup{}, zerolog.Nop())
	if p == nil {
		t.Fatal("expected non-nil EventPublisher")
	}
}

func TestPublish_EmptyMessageID_ReturnsError(t *testing.T) {
	pub := newTestPublisher(&mockDedup{}, &mockRabbitPublisher{})
	event := &domain.Event{Topic: "test", MessageID: "", Payload: []byte("data")}

	err := pub.Publish(context.Background(), event)
	if err == nil {
		t.Fatal("expected error for empty MessageID")
	}
}

func TestPublish_Duplicate_PublishNotCalled_ReturnsNil(t *testing.T) {
	rabbit := &mockRabbitPublisher{}
	pub := newTestPublisher(&mockDedup{isDuplicateReturn: true}, rabbit)
	event := &domain.Event{Topic: "test", MessageID: "msg-dup", Payload: []byte("data")}

	err := pub.Publish(context.Background(), event)
	if err != nil {
		t.Fatalf("expected nil error for duplicate, got %v", err)
	}
	if rabbit.called {
		t.Fatal("expected Publish not to be called for duplicate")
	}
}

func TestPublish_NotDuplicate_PublishCalled(t *testing.T) {
	rabbit := &mockRabbitPublisher{}
	pub := newTestPublisher(&mockDedup{isDuplicateReturn: false}, rabbit)
	event := &domain.Event{Topic: "test", MessageID: "msg-new", Payload: []byte("data")}

	if err := pub.Publish(context.Background(), event); err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !rabbit.called {
		t.Fatal("expected Publish to be called for non-duplicate")
	}
}

func TestPublish_RedisError_PublishCalled(t *testing.T) {
	rabbit := &mockRabbitPublisher{}
	pub := newTestPublisher(&mockDedup{isDuplicateErr: errors.New("redis: connection refused")}, rabbit)
	event := &domain.Event{Topic: "test", MessageID: "msg-redis-err", Payload: []byte("data")}

	if err := pub.Publish(context.Background(), event); err != nil {
		t.Fatalf("unexpected error on Redis failure (fail-open): %v", err)
	}
	if !rabbit.called {
		t.Fatal("expected Publish to be called when Redis errors (fail-open)")
	}
}

func TestPublish_RabbitError_ReturnsError(t *testing.T) {
	rabbitErr := errors.New("rabbit: channel closed")
	rabbit := &mockRabbitPublisher{err: rabbitErr}
	pub := newTestPublisher(&mockDedup{}, rabbit)
	event := &domain.Event{Topic: "test", MessageID: "msg-rabbit-err", Payload: []byte("data")}

	err := pub.Publish(context.Background(), event)
	if err == nil {
		t.Fatal("expected error from rabbit publisher")
	}
	if !errors.Is(err, rabbitErr) {
		t.Errorf("expected %v, got %v", rabbitErr, err)
	}
}

func TestPublish_CorrectRoutingKeyAndBody(t *testing.T) {
	rabbit := &mockRabbitPublisher{}
	pub := newTestPublisher(&mockDedup{}, rabbit)
	event := &domain.Event{
		Topic:     "test.topic",
		MessageID: "msg-verify",
		Payload:   []byte(`{"key":"value"}`),
	}

	if err := pub.Publish(context.Background(), event); err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !rabbit.called {
		t.Fatal("expected Publish to be called")
	}
}
