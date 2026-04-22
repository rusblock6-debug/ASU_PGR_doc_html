package grpc

import (
	"context"
	"errors"
	"io"
	"sync"
	"testing"
	"time"
	"wifi-event-dispatcher/internal/rabbitmq"
	"wifi-event-dispatcher/server/serverpb"

	amqp "github.com/rabbitmq/amqp091-go"
	"github.com/rs/zerolog"
	"go.uber.org/mock/gomock"
	"google.golang.org/grpc/metadata"
)

// ---------------------------------------------------------------------------
// mockDedupService — test double for dedup.Service
// ---------------------------------------------------------------------------

type mockDedupService struct {
	isDuplicate bool
	err         error
	called      bool
}

func (m *mockDedupService) IsDuplicate(_ context.Context, _ string) (bool, error) {
	m.called = true
	return m.isDuplicate, m.err
}

func (m *mockDedupService) MarkSeen(_ context.Context, _ string) error { return nil }

// ---------------------------------------------------------------------------
// mockAcknowledger — test double for amqp.Acknowledger
// ---------------------------------------------------------------------------

type mockAcknowledger struct {
	ackCalled bool
}

func (m *mockAcknowledger) Ack(_ uint64, _ bool) error {
	m.ackCalled = true
	return nil
}

func (m *mockAcknowledger) Nack(_ uint64, _ bool, _ bool) error { return nil }
func (m *mockAcknowledger) Reject(_ uint64, _ bool) error       { return nil }

// ---------------------------------------------------------------------------
// mockSendEventsStream
// ---------------------------------------------------------------------------

type mockSendEventsStream struct {
	ctx    context.Context
	recvCh chan *serverpb.SendEventRequest
	mu     sync.Mutex
	sent   []*serverpb.SendEventResponse
}

func newMockSendEventsStream(ctx context.Context) *mockSendEventsStream {
	return &mockSendEventsStream{
		ctx:    ctx,
		recvCh: make(chan *serverpb.SendEventRequest, 16),
	}
}

func (m *mockSendEventsStream) Send(resp *serverpb.SendEventResponse) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.sent = append(m.sent, resp)
	return nil
}

func (m *mockSendEventsStream) Recv() (*serverpb.SendEventRequest, error) {
	req, ok := <-m.recvCh
	if !ok {
		return nil, io.EOF
	}
	return req, nil
}

func (m *mockSendEventsStream) SetHeader(metadata.MD) error  { return nil }
func (m *mockSendEventsStream) SendHeader(metadata.MD) error { return nil }
func (m *mockSendEventsStream) SetTrailer(metadata.MD)       {}
func (m *mockSendEventsStream) Context() context.Context     { return m.ctx }
func (m *mockSendEventsStream) SendMsg(any) error            { return nil }
func (m *mockSendEventsStream) RecvMsg(any) error            { return nil }

func (m *mockSendEventsStream) sentResponses() []*serverpb.SendEventResponse {
	m.mu.Lock()
	defer m.mu.Unlock()
	dst := make([]*serverpb.SendEventResponse, len(m.sent))
	copy(dst, m.sent)
	return dst
}

// ---------------------------------------------------------------------------
// errorSendEventsStream
// ---------------------------------------------------------------------------

type errorSendEventsStream struct {
	ctx     context.Context
	recvErr error
	mu      sync.Mutex
	sent    []*serverpb.SendEventResponse
}

func (m *errorSendEventsStream) Send(resp *serverpb.SendEventResponse) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.sent = append(m.sent, resp)
	return nil
}

func (m *errorSendEventsStream) Recv() (*serverpb.SendEventRequest, error) {
	return nil, m.recvErr
}

func (m *errorSendEventsStream) SetHeader(metadata.MD) error  { return nil }
func (m *errorSendEventsStream) SendHeader(metadata.MD) error { return nil }
func (m *errorSendEventsStream) SetTrailer(metadata.MD)       {}
func (m *errorSendEventsStream) Context() context.Context     { return m.ctx }
func (m *errorSendEventsStream) SendMsg(any) error            { return nil }
func (m *errorSendEventsStream) RecvMsg(any) error            { return nil }

// ---------------------------------------------------------------------------
// helpers
// ---------------------------------------------------------------------------

func newTestServer(app *MockApp) *server {
	logger := zerolog.Nop()
	return RegisterServer(app, &mockDedupService{}, logger, nil)
}

func validEventRequest(messageID, topic string) *serverpb.SendEventRequest {
	return &serverpb.SendEventRequest{
		Kind: &serverpb.SendEventRequest_Event{
			Event: &serverpb.Event{
				MessageId: messageID,
				Topic:     topic,
				Payload:   []byte(`{"key":"value"}`),
			},
		},
	}
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

func TestStreamBortSendEvents_ProducerRegistration(t *testing.T) {
	ctrl := gomock.NewController(t)
	app := NewMockApp(ctrl)
	srv := newTestServer(app)

	stream := newMockSendEventsStream(context.Background())

	stream.recvCh <- &serverpb.SendEventRequest{
		Kind: &serverpb.SendEventRequest_Producer{
			Producer: &serverpb.Client{TruckId: 42},
		},
	}
	close(stream.recvCh)

	err := srv.StreamBortSendEvents(stream)
	if err != nil {
		t.Fatalf("expected nil error on normal EOF close, got: %v", err)
	}

	responses := stream.sentResponses()
	if len(responses) != 0 {
		t.Fatalf("expected 0 responses for producer registration, got %d", len(responses))
	}
}

func TestStreamBortSendEvents_EventSuccess(t *testing.T) {
	ctrl := gomock.NewController(t)
	app := NewMockApp(ctrl)
	srv := newTestServer(app)

	stream := newMockSendEventsStream(context.Background())

	app.EXPECT().
		HandleEvent(gomock.Any(), gomock.Any()).
		Return(nil).
		Times(1)

	stream.recvCh <- validEventRequest("msg-1", "bort_4.server.trip_service.src")
	close(stream.recvCh)

	err := srv.StreamBortSendEvents(stream)
	if err != nil {
		t.Fatalf("expected nil error, got: %v", err)
	}

	responses := stream.sentResponses()
	if len(responses) != 1 {
		t.Fatalf("expected 1 ACK response, got %d", len(responses))
	}

	ack := responses[0].GetAck()
	if ack == nil {
		t.Fatal("expected non-nil ack in response")
	}
	if ack.GetMessageId() != "msg-1" {
		t.Errorf("expected message_id 'msg-1', got %q", ack.GetMessageId())
	}
	if !ack.GetOk() {
		t.Errorf("expected ack.ok=true, got false; error=%q", ack.GetError())
	}
}

func TestStreamBortSendEvents_EventHandleError(t *testing.T) {
	ctrl := gomock.NewController(t)
	app := NewMockApp(ctrl)
	srv := newTestServer(app)

	stream := newMockSendEventsStream(context.Background())

	handleErr := errors.New("publish failed")
	app.EXPECT().
		HandleEvent(gomock.Any(), gomock.Any()).
		Return(handleErr).
		Times(1)

	stream.recvCh <- validEventRequest("msg-2", "bort_4.server.trip_service.src")
	close(stream.recvCh)

	err := srv.StreamBortSendEvents(stream)
	if err != nil {
		t.Fatalf("expected nil error (stream should not break on HandleEvent error), got: %v", err)
	}

	responses := stream.sentResponses()
	if len(responses) != 1 {
		t.Fatalf("expected 1 ACK response, got %d", len(responses))
	}

	ack := responses[0].GetAck()
	if ack.GetOk() {
		t.Error("expected ack.ok=false when HandleEvent returns error")
	}
	if ack.GetError() != "publish failed" {
		t.Errorf("expected error 'publish failed', got %q", ack.GetError())
	}
}

func TestStreamBortSendEvents_InvalidEvent(t *testing.T) {
	ctrl := gomock.NewController(t)
	app := NewMockApp(ctrl)
	srv := newTestServer(app)

	stream := newMockSendEventsStream(context.Background())

	stream.recvCh <- &serverpb.SendEventRequest{
		Kind: &serverpb.SendEventRequest_Event{
			Event: &serverpb.Event{
				MessageId: "msg-3",
				Topic:     "", // empty topic -> validation error
				Payload:   []byte(`{"data":1}`),
			},
		},
	}
	close(stream.recvCh)

	err := srv.StreamBortSendEvents(stream)
	if err != nil {
		t.Fatalf("expected nil error, got: %v", err)
	}

	responses := stream.sentResponses()
	if len(responses) != 1 {
		t.Fatalf("expected 1 ACK response, got %d", len(responses))
	}

	ack := responses[0].GetAck()
	if ack.GetOk() {
		t.Error("expected ack.ok=false for invalid event")
	}
	if ack.GetError() == "" {
		t.Error("expected non-empty error string for invalid event")
	}
}

func TestStreamBortSendEvents_RecvError(t *testing.T) {
	ctrl := gomock.NewController(t)
	app := NewMockApp(ctrl)
	srv := newTestServer(app)

	recvErr := errors.New("transport broken")
	stream := &errorSendEventsStream{
		ctx:     context.Background(),
		recvErr: recvErr,
	}

	err := srv.StreamBortSendEvents(stream)
	if err == nil {
		t.Fatal("expected error from Recv propagation, got nil")
	}
	if !errors.Is(err, recvErr) {
		t.Errorf("expected error %q, got %q", recvErr, err)
	}
}

func TestStreamBortSendEvents_NilEvent(t *testing.T) {
	ctrl := gomock.NewController(t)
	app := NewMockApp(ctrl)
	srv := newTestServer(app)

	stream := newMockSendEventsStream(context.Background())

	stream.recvCh <- &serverpb.SendEventRequest{
		Kind: &serverpb.SendEventRequest_Event{
			Event: nil,
		},
	}
	close(stream.recvCh)

	err := srv.StreamBortSendEvents(stream)
	if err != nil {
		t.Fatalf("expected nil error, got: %v", err)
	}

	responses := stream.sentResponses()
	if len(responses) != 0 {
		t.Fatalf("expected 0 responses when event is nil, got %d", len(responses))
	}
}

// ===========================================================================
// StreamBortGetEvents tests
// ===========================================================================

// mockGetEventsServerStream implements the server-side bidi stream for StreamBortGetEvents.
type mockGetEventsServerStream struct {
	ctx    context.Context
	recvCh chan *serverpb.GetEventRequest
	mu     sync.Mutex
	sent   []*serverpb.GetEventResponse
}

func newMockGetEventsServerStream(ctx context.Context) *mockGetEventsServerStream {
	return &mockGetEventsServerStream{
		ctx:    ctx,
		recvCh: make(chan *serverpb.GetEventRequest, 16),
	}
}

func (m *mockGetEventsServerStream) Send(resp *serverpb.GetEventResponse) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.sent = append(m.sent, resp)
	return nil
}

func (m *mockGetEventsServerStream) Recv() (*serverpb.GetEventRequest, error) {
	select {
	case req, ok := <-m.recvCh:
		if !ok {
			return nil, io.EOF
		}
		return req, nil
	case <-m.ctx.Done():
		return nil, m.ctx.Err()
	}
}

func (m *mockGetEventsServerStream) SetHeader(metadata.MD) error  { return nil }
func (m *mockGetEventsServerStream) SendHeader(metadata.MD) error { return nil }
func (m *mockGetEventsServerStream) SetTrailer(metadata.MD)       {}
func (m *mockGetEventsServerStream) Context() context.Context     { return m.ctx }
func (m *mockGetEventsServerStream) SendMsg(any) error            { return nil }
func (m *mockGetEventsServerStream) RecvMsg(any) error            { return nil }

func (m *mockGetEventsServerStream) sentResponses() []*serverpb.GetEventResponse {
	m.mu.Lock()
	defer m.mu.Unlock()
	dst := make([]*serverpb.GetEventResponse, len(m.sent))
	copy(dst, m.sent)
	return dst
}

// makeChanSubscription creates a ChanSubscription by using the SubscribeChan mock infrastructure.
// Since ChanSubscription has unexported fields, we use the real Client.SubscribeChan indirectly.
// Instead, we'll construct a test helper that returns messages via a channel.
func makeTestSubscription(ctx context.Context, msgs chan amqp.Delivery) *rabbitmq.ChanSubscription {
	// We cannot construct ChanSubscription directly (unexported fields).
	// Return nil and use a different approach for tests.
	return nil
}

func TestStreamBortGetEvents_RecvError(t *testing.T) {
	ctrl := gomock.NewController(t)
	app := NewMockApp(ctrl)
	srv := newTestServer(app)

	recvErr := errors.New("transport broken")
	stream := &errorGetEventsServerStream{
		ctx:     context.Background(),
		recvErr: recvErr,
	}

	err := srv.StreamBortGetEvents(stream)
	if err == nil {
		t.Fatal("expected error, got nil")
	}
	if !errors.Is(err, recvErr) {
		t.Errorf("expected error %v, got %v", recvErr, err)
	}
}

func TestStreamBortGetEvents_EOF(t *testing.T) {
	ctrl := gomock.NewController(t)
	app := NewMockApp(ctrl)
	srv := newTestServer(app)

	stream := newMockGetEventsServerStream(context.Background())
	close(stream.recvCh)

	err := srv.StreamBortGetEvents(stream)
	if err != nil {
		t.Fatalf("expected nil error on EOF, got: %v", err)
	}
}

func TestStreamBortGetEvents_ContextCanceled(t *testing.T) {
	ctrl := gomock.NewController(t)
	app := NewMockApp(ctrl)
	srv := newTestServer(app)

	ctx, cancel := context.WithCancel(context.Background())
	stream := newMockGetEventsServerStream(ctx)

	// Cancel immediately
	cancel()

	err := srv.StreamBortGetEvents(stream)
	if err == nil {
		t.Fatal("expected error, got nil")
	}
}

func TestStreamBortGetEvents_SubscriberRegistration_SubscribeError(t *testing.T) {
	ctrl := gomock.NewController(t)
	app := NewMockApp(ctrl)
	srv := newTestServer(app)

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	stream := newMockGetEventsServerStream(ctx)

	app.EXPECT().
		SubscribeAll(gomock.Any(), 42).
		Return(nil, errors.New("subscribe failed"))

	stream.recvCh <- &serverpb.GetEventRequest{
		Kind: &serverpb.GetEventRequest_Subscriber{
			Subscriber: &serverpb.Client{TruckId: 42},
		},
	}

	// Give time for the subscribe to fail
	go func() {
		time.Sleep(100 * time.Millisecond)
		cancel()
	}()

	err := srv.StreamBortGetEvents(stream)
	if err == nil {
		t.Fatal("expected error from subscribe failure, got nil")
	}
}

func TestStreamBortGetEvents_AckForUnknownMessage(t *testing.T) {
	ctrl := gomock.NewController(t)
	app := NewMockApp(ctrl)
	srv := newTestServer(app)

	stream := newMockGetEventsServerStream(context.Background())

	// Send an ACK for a message that was never sent to the client
	stream.recvCh <- &serverpb.GetEventRequest{
		Kind: &serverpb.GetEventRequest_Ack{
			Ack: &serverpb.Ack{
				MessageId: "unknown-msg",
				Ok:        true,
			},
		},
	}
	close(stream.recvCh)

	err := srv.StreamBortGetEvents(stream)
	if err != nil {
		t.Fatalf("expected nil error (unknown ACK is silently ignored), got: %v", err)
	}
}

// errorGetEventsServerStream: returns a specific error on Recv.
type errorGetEventsServerStream struct {
	ctx     context.Context
	recvErr error
	mu      sync.Mutex
	sent    []*serverpb.GetEventResponse
}

func (m *errorGetEventsServerStream) Send(resp *serverpb.GetEventResponse) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.sent = append(m.sent, resp)
	return nil
}

func (m *errorGetEventsServerStream) Recv() (*serverpb.GetEventRequest, error) {
	return nil, m.recvErr
}

func (m *errorGetEventsServerStream) SetHeader(metadata.MD) error  { return nil }
func (m *errorGetEventsServerStream) SendHeader(metadata.MD) error { return nil }
func (m *errorGetEventsServerStream) SetTrailer(metadata.MD)       {}
func (m *errorGetEventsServerStream) Context() context.Context     { return m.ctx }
func (m *errorGetEventsServerStream) SendMsg(any) error            { return nil }
func (m *errorGetEventsServerStream) RecvMsg(any) error            { return nil }

// ===========================================================================
// isDuplicateDelivery unit tests
// ===========================================================================

func makeDelivery(messageID string, acker amqp.Acknowledger) amqp.Delivery {
	return amqp.Delivery{
		Acknowledger: acker,
		MessageId:    messageID,
	}
}

// TestIsDuplicateDelivery_Duplicate verifies that a duplicate delivery is Ack'd
// and isDuplicateDelivery returns true (message must NOT be forwarded).
func TestIsDuplicateDelivery_Duplicate_AckCalledDropped(t *testing.T) {
	ctrl := gomock.NewController(t)
	app := NewMockApp(ctrl)
	dedupSvc := &mockDedupService{isDuplicate: true}
	logger := zerolog.Nop()
	srv := RegisterServer(app, dedupSvc, logger, nil)

	acker := &mockAcknowledger{}
	delivery := makeDelivery("msg-dup", acker)

	dropped := srv.isDuplicateDelivery(context.Background(), delivery)

	if !dropped {
		t.Error("expected isDuplicateDelivery to return true for duplicate")
	}
	if !acker.ackCalled {
		t.Error("expected Ack to be called on duplicate delivery")
	}
	if !dedupSvc.called {
		t.Error("expected IsDuplicate to be called")
	}
}

// TestIsDuplicateDelivery_NonDuplicate verifies that a non-duplicate delivery is NOT Ack'd
// and isDuplicateDelivery returns false (message must be forwarded normally).
func TestIsDuplicateDelivery_NonDuplicate_ForwardedNormally(t *testing.T) {
	ctrl := gomock.NewController(t)
	app := NewMockApp(ctrl)
	dedupSvc := &mockDedupService{isDuplicate: false}
	logger := zerolog.Nop()
	srv := RegisterServer(app, dedupSvc, logger, nil)

	acker := &mockAcknowledger{}
	delivery := makeDelivery("msg-new", acker)

	dropped := srv.isDuplicateDelivery(context.Background(), delivery)

	if dropped {
		t.Error("expected isDuplicateDelivery to return false for non-duplicate")
	}
	if acker.ackCalled {
		t.Error("expected Ack NOT to be called for non-duplicate delivery")
	}
}

// TestIsDuplicateDelivery_RedisError verifies that a Redis error causes fail-open:
// Ack is NOT called and isDuplicateDelivery returns false (message forwarded).
func TestIsDuplicateDelivery_RedisError_ForwardedFailOpen(t *testing.T) {
	ctrl := gomock.NewController(t)
	app := NewMockApp(ctrl)
	dedupSvc := &mockDedupService{err: errors.New("redis: connection refused")}
	logger := zerolog.Nop()
	srv := RegisterServer(app, dedupSvc, logger, nil)

	acker := &mockAcknowledger{}
	delivery := makeDelivery("msg-redis-err", acker)

	dropped := srv.isDuplicateDelivery(context.Background(), delivery)

	if dropped {
		t.Error("expected isDuplicateDelivery to return false on Redis error (fail-open)")
	}
	if acker.ackCalled {
		t.Error("expected Ack NOT to be called on Redis error")
	}
}

// TestIsDuplicateDelivery_EmptyMessageId verifies that an empty MessageId skips
// the dedup check and isDuplicateDelivery returns false (message forwarded normally).
func TestIsDuplicateDelivery_EmptyMessageId_SkipsDedup(t *testing.T) {
	ctrl := gomock.NewController(t)
	app := NewMockApp(ctrl)
	dedupSvc := &mockDedupService{}
	logger := zerolog.Nop()
	srv := RegisterServer(app, dedupSvc, logger, nil)

	acker := &mockAcknowledger{}
	delivery := makeDelivery("", acker)

	dropped := srv.isDuplicateDelivery(context.Background(), delivery)

	if dropped {
		t.Error("expected isDuplicateDelivery to return false for empty MessageId")
	}
	if acker.ackCalled {
		t.Error("expected Ack NOT to be called for empty MessageId delivery")
	}
	if dedupSvc.called {
		t.Error("expected IsDuplicate NOT to be called for empty MessageId")
	}
}
