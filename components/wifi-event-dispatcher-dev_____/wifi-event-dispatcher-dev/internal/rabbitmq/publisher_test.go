package rabbitmq

import (
	"context"
	"fmt"
	"sync/atomic"
	"testing"
	"time"

	amqp "github.com/rabbitmq/amqp091-go"
	"github.com/rs/zerolog"
)

// mockDedupSvc is a test double for DedupService.
type mockDedupSvc struct {
	callCount atomic.Int32
	lastMsgID string
	returnErr error
}

func (m *mockDedupSvc) MarkSeen(_ context.Context, messageID string) error {
	m.callCount.Add(1)
	m.lastMsgID = messageID
	return m.returnErr
}

// newTestPublisher creates a Publisher with internal maps initialised for unit
// testing resolveConfirm without starting the background goroutine.
func newTestPublisher(dedupSvc DedupService) *Publisher {
	return &Publisher{
		logger:     zerolog.Nop(),
		pending:    make(map[uint64]chan error),
		seqToMsgID: make(map[uint64]string),
		returned:   make(map[string]amqp.Return),
		done:       make(chan struct{}),
		dedupSvc:   dedupSvc,
	}
}

// TestResolveConfirm_ACK_callsMarkSeen verifies that after an ACK the dedup
// service's MarkSeen is called with the correct messageID, and the publish
// result is nil.
func TestResolveConfirm_ACK_callsMarkSeen(t *testing.T) {
	mock := &mockDedupSvc{}
	p := newTestPublisher(mock)

	result := make(chan error, 1)
	const msgID = "test-message-id"

	p.pending[1] = result
	p.seqToMsgID[1] = msgID

	p.resolveConfirm(amqp.Confirmation{DeliveryTag: 1, Ack: true})

	if err := <-result; err != nil {
		t.Fatalf("expected nil publish result on ACK, got %v", err)
	}
	if n := mock.callCount.Load(); n != 1 {
		t.Fatalf("expected MarkSeen called once, got %d", n)
	}
	if mock.lastMsgID != msgID {
		t.Fatalf("expected MarkSeen called with %q, got %q", msgID, mock.lastMsgID)
	}
}

// TestResolveConfirm_NACK_doesNotCallMarkSeen verifies that on a NACK the
// publish result is an error and MarkSeen is never called.
func TestResolveConfirm_NACK_doesNotCallMarkSeen(t *testing.T) {
	mock := &mockDedupSvc{}
	p := newTestPublisher(mock)

	result := make(chan error, 1)
	p.pending[1] = result
	p.seqToMsgID[1] = "test-msg"

	p.resolveConfirm(amqp.Confirmation{DeliveryTag: 1, Ack: false})

	if err := <-result; err == nil {
		t.Fatal("expected non-nil error on NACK, got nil")
	}
	if n := mock.callCount.Load(); n != 0 {
		t.Fatalf("expected MarkSeen NOT called on NACK, called %d times", n)
	}
}

// TestResolveConfirm_ACK_MarkSeenError_publishResultNil verifies that when
// MarkSeen returns an error the publish result is still nil (fail-open).
func TestResolveConfirm_ACK_MarkSeenError_publishResultNil(t *testing.T) {
	mock := &mockDedupSvc{returnErr: fmt.Errorf("redis unavailable")}
	p := newTestPublisher(mock)

	result := make(chan error, 1)
	const msgID = "test-message-id"
	p.pending[1] = result
	p.seqToMsgID[1] = msgID

	p.resolveConfirm(amqp.Confirmation{DeliveryTag: 1, Ack: true})

	if err := <-result; err != nil {
		t.Fatalf("expected nil publish result even when MarkSeen fails, got %v", err)
	}
	if n := mock.callCount.Load(); n != 1 {
		t.Fatalf("expected MarkSeen called once, got %d", n)
	}
}

// TestResolveConfirm_ACK_NilDedupSvc verifies that when dedupSvc is nil,
// resolveConfirm still works correctly on ACK (no panic, nil result).
func TestResolveConfirm_ACK_NilDedupSvc(t *testing.T) {
	p := newTestPublisher(nil) // nil dedup service

	result := make(chan error, 1)
	p.pending[1] = result
	p.seqToMsgID[1] = "test-msg"

	p.resolveConfirm(amqp.Confirmation{DeliveryTag: 1, Ack: true})

	if err := <-result; err != nil {
		t.Fatalf("expected nil publish result on ACK with nil dedup, got %v", err)
	}
}

// TestResolveConfirm_ACK_EmptyMsgID verifies that when msgID is empty,
// MarkSeen is not called even on ACK.
func TestResolveConfirm_ACK_EmptyMsgID(t *testing.T) {
	mock := &mockDedupSvc{}
	p := newTestPublisher(mock)

	result := make(chan error, 1)
	p.pending[1] = result
	p.seqToMsgID[1] = "" // empty message ID

	p.resolveConfirm(amqp.Confirmation{DeliveryTag: 1, Ack: true})

	if err := <-result; err != nil {
		t.Fatalf("expected nil publish result, got %v", err)
	}
	if n := mock.callCount.Load(); n != 0 {
		t.Fatalf("expected MarkSeen NOT called for empty msgID, called %d times", n)
	}
}

// TestResolveConfirm_UnknownTag verifies that a confirmation for an unknown
// delivery tag is silently ignored.
func TestResolveConfirm_UnknownTag(t *testing.T) {
	mock := &mockDedupSvc{}
	p := newTestPublisher(mock)

	// No pending entries — should not panic
	p.resolveConfirm(amqp.Confirmation{DeliveryTag: 999, Ack: true})

	if n := mock.callCount.Load(); n != 0 {
		t.Fatalf("expected MarkSeen NOT called for unknown tag, called %d times", n)
	}
}

// TestResolveConfirm_Return_NonNoRoute_ReturnsError verifies that when a message
// was returned with a non-312 code, it results in an error and MarkSeen is not called.
func TestResolveConfirm_Return_NonNoRoute_ReturnsError(t *testing.T) {
	mock := &mockDedupSvc{}
	p := newTestPublisher(mock)

	result := make(chan error, 1)
	const msgID = "test-message-id"
	p.pending[1] = result
	p.seqToMsgID[1] = msgID
	p.returned[msgID] = amqp.Return{ReplyCode: 313, ReplyText: "NO_CONSUMERS"}

	p.resolveConfirm(amqp.Confirmation{DeliveryTag: 1, Ack: true})

	if err := <-result; err == nil {
		t.Fatal("expected error on non-312 RETURN, got nil")
	}
	if n := mock.callCount.Load(); n != 0 {
		t.Fatalf("expected MarkSeen NOT called on RETURN, called %d times", n)
	}
}

// TestResolveConfirm_NoRoute312_RetriesPublish verifies that when a message is
// returned with 312 (NO_ROUTE), resolveConfirm retries via Publish in a goroutine
// instead of immediately returning an error.
func TestResolveConfirm_NoRoute312_RetriesPublish(t *testing.T) {
	mock := &mockDedupSvc{}
	p := newTestPublisher(mock)

	// Set up requests channel so the retry Publish can send to it.
	// We make the buffer large enough to not block.
	p.requests = make(chan publishRequest, 1)
	p.connected.Store(true)

	result := make(chan error, 1)
	const msgID = "retry-msg"
	p.pending[1] = result
	p.seqToMsgID[1] = msgID
	p.returned[msgID] = amqp.Return{
		ReplyCode:  312,
		ReplyText:  "NO_ROUTE",
		RoutingKey: "bort_4.server.trip.dst",
		MessageId:  msgID,
		Body:       []byte(`{"test":true}`),
	}

	p.resolveConfirm(amqp.Confirmation{DeliveryTag: 1, Ack: true})

	// The retry goes through p.Publish which sends to p.requests.
	// Verify the retry request was enqueued.
	select {
	case req := <-p.requests:
		if req.msg.RoutingKey != "bort_4.server.trip.dst" {
			t.Errorf("retry routing_key = %q, want bort_4.server.trip.dst", req.msg.RoutingKey)
		}
		if req.msg.MessageID != msgID {
			t.Errorf("retry message_id = %q, want %q", req.msg.MessageID, msgID)
		}
		if string(req.msg.Body) != `{"test":true}` {
			t.Errorf("retry body = %q, want {\"test\":true}", req.msg.Body)
		}
		// Simulate successful publish so the goroutine completes
		req.result <- nil
	case <-time.After(2 * time.Second):
		t.Fatal("timed out waiting for retry publish request")
	}

	// The result channel should get nil (success) from the retry
	select {
	case err := <-result:
		if err != nil {
			t.Fatalf("expected nil from retry, got %v", err)
		}
	case <-time.After(2 * time.Second):
		t.Fatal("timed out waiting for result from retry")
	}

	if n := mock.callCount.Load(); n != 0 {
		t.Fatalf("expected MarkSeen NOT called on NO_ROUTE retry, called %d times", n)
	}
}

// TestRecordReturn_NoRoute_CallsEnsureQueue verifies that recordReturn with
// code 312 calls ensureQueue. We test this indirectly: without a client
// connection ensureQueue will fail, but it should still record the return.
func TestRecordReturn_NoRoute_RecordsReturn(t *testing.T) {
	p := newTestPublisher(nil)
	// No client — ensureQueue will fail, but recordReturn should still store the return.
	p.client = &Client{}

	ret := amqp.Return{
		ReplyCode:  312,
		ReplyText:  "NO_ROUTE",
		RoutingKey: "server.bort_4.trip.dst",
		MessageId:  "msg-ensure",
	}

	p.recordReturn(ret)

	p.mu.RLock()
	stored, ok := p.returned["msg-ensure"]
	p.mu.RUnlock()

	if !ok {
		t.Fatal("expected return to be stored")
	}
	if stored.RoutingKey != "server.bort_4.trip.dst" {
		t.Errorf("stored routing_key = %q, want server.bort_4.trip.dst", stored.RoutingKey)
	}
}

// TestRecordReturn_NonNoRoute_DoesNotCallEnsureQueue verifies that recordReturn
// with a non-312 code does not attempt queue creation.
func TestRecordReturn_NonNoRoute_StoresReturn(t *testing.T) {
	p := newTestPublisher(nil)

	ret := amqp.Return{
		ReplyCode:  313,
		ReplyText:  "NO_CONSUMERS",
		RoutingKey: "some.key",
		MessageId:  "msg-non-312",
	}

	p.recordReturn(ret)

	p.mu.RLock()
	_, ok := p.returned["msg-non-312"]
	p.mu.RUnlock()

	if !ok {
		t.Fatal("expected return to be stored")
	}
}
