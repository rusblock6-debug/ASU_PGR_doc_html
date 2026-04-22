package application

import (
	"context"
	"errors"
	"fmt"
	"sync"
	"testing"

	"wifi-event-dispatcher/internal/config"
	"wifi-event-dispatcher/internal/dedup"
	"wifi-event-dispatcher/internal/rabbitmq"
	"wifi-event-dispatcher/server/serverpb"

	amqp "github.com/rabbitmq/amqp091-go"
	"github.com/rs/zerolog"
	"go.uber.org/mock/gomock"
	"google.golang.org/grpc/metadata"
)

type mockGetEventsStream struct {
	ctx       context.Context
	sendErr   error
	sentMu    sync.Mutex
	sent      []*serverpb.GetEventRequest
	recvQueue []*serverpb.GetEventResponse
	recvErr   error
	recvIdx   int
}

func (m *mockGetEventsStream) Send(req *serverpb.GetEventRequest) error {
	if m.sendErr != nil {
		return m.sendErr
	}
	m.sentMu.Lock()
	m.sent = append(m.sent, req)
	m.sentMu.Unlock()
	return nil
}

func (m *mockGetEventsStream) Recv() (*serverpb.GetEventResponse, error) {
	if m.recvIdx >= len(m.recvQueue) {
		return nil, m.recvErr
	}
	resp := m.recvQueue[m.recvIdx]
	m.recvIdx++
	return resp, nil
}

func (m *mockGetEventsStream) Header() (metadata.MD, error) { return nil, nil }
func (m *mockGetEventsStream) Trailer() metadata.MD         { return nil }
func (m *mockGetEventsStream) CloseSend() error             { return nil }
func (m *mockGetEventsStream) Context() context.Context     { return m.ctx }
func (m *mockGetEventsStream) SendMsg(any) error            { return nil }
func (m *mockGetEventsStream) RecvMsg(any) error            { return nil }

type mockSendEventsClientStream struct {
	ctx       context.Context
	sendErr   error
	sentMu    sync.Mutex
	sent      []*serverpb.SendEventRequest
	recvQueue []*serverpb.SendEventResponse
	recvErr   error
	recvIdx   int
}

func (m *mockSendEventsClientStream) Send(req *serverpb.SendEventRequest) error {
	if m.sendErr != nil {
		return m.sendErr
	}
	m.sentMu.Lock()
	m.sent = append(m.sent, req)
	m.sentMu.Unlock()
	return nil
}

func (m *mockSendEventsClientStream) Recv() (*serverpb.SendEventResponse, error) {
	if m.recvIdx >= len(m.recvQueue) {
		return nil, m.recvErr
	}
	resp := m.recvQueue[m.recvIdx]
	m.recvIdx++
	return resp, nil
}

func (m *mockSendEventsClientStream) Header() (metadata.MD, error) { return nil, nil }
func (m *mockSendEventsClientStream) Trailer() metadata.MD         { return nil }
func (m *mockSendEventsClientStream) CloseSend() error             { return nil }
func (m *mockSendEventsClientStream) Context() context.Context     { return m.ctx }
func (m *mockSendEventsClientStream) SendMsg(any) error            { return nil }
func (m *mockSendEventsClientStream) RecvMsg(any) error            { return nil }

func newStreamTestApp(t *testing.T) (*app, *MockServerRepository, *MockEventPublisher, *MockRabbitSubscriber, *MockDedupService) {
	t.Helper()
	ctrl := gomock.NewController(t)

	repo := NewMockServerRepository(ctrl)
	pub := NewMockEventPublisher(ctrl)
	sub := NewMockRabbitSubscriber(ctrl)
	ded := NewMockDedupService(ctrl)
	disc := NewMockQueueDiscoverer(ctrl)
	disc.EXPECT().DiscoverQueues(gomock.Any(), gomock.Any()).Return([]string{"bort_4.server.trip.src"}, nil).AnyTimes()

	a := New(Deps{
		Cfg:              config.BortConfig{TruckID: 4, ServerAddress: "localhost:8085"},
		Logger:           zerolog.Nop(),
		ServerRepository: repo,
		Publisher:        pub,
		Subscriber:       sub,
		Discovery:        disc,
		Dedup:            dedup.Service(ded),
	}).(*app)
	return a, repo, pub, sub, ded
}

func TestRunGetEventsStream_OpenError(t *testing.T) {
	a, repo, _, _, _ := newStreamTestApp(t)
	ctx := context.Background()

	openErr := errors.New("connection refused")
	repo.EXPECT().StreamGetEvents(gomock.Any()).Return(nil, openErr)

	err := a.runGetEventsStream(ctx)
	if err == nil {
		t.Fatal("expected error, got nil")
	}
	if !errors.Is(err, openErr) {
		t.Errorf("expected wrapped %v, got %v", openErr, err)
	}
}

func TestRunGetEventsStream_OpenError_ContextCanceled(t *testing.T) {
	a, repo, _, _, _ := newStreamTestApp(t)

	ctx, cancel := context.WithCancel(context.Background())
	cancel()

	repo.EXPECT().StreamGetEvents(gomock.Any()).Return(nil, context.Canceled)

	err := a.runGetEventsStream(ctx)
	if err != nil {
		t.Errorf("expected nil when context canceled, got: %v", err)
	}
}

func TestRunGetEventsStream_SendRegistrationError(t *testing.T) {
	a, repo, _, _, _ := newStreamTestApp(t)
	ctx := context.Background()

	sendErr := errors.New("send failed")
	stream := &mockGetEventsStream{
		ctx:     ctx,
		sendErr: sendErr,
		recvErr: errors.New("should not reach recv"),
	}

	repo.EXPECT().StreamGetEvents(gomock.Any()).Return(stream, nil)

	err := a.runGetEventsStream(ctx)
	if err == nil {
		t.Fatal("expected error, got nil")
	}
	if !errors.Is(err, sendErr) {
		t.Errorf("expected wrapped %v, got %v", sendErr, err)
	}
}

func TestRunGetEventsStream_RecvEvent_PublishSuccess(t *testing.T) {
	a, repo, pub, _, ded := newStreamTestApp(t)
	ctx := context.Background()

	stream := &mockGetEventsStream{
		ctx: ctx,
		recvQueue: []*serverpb.GetEventResponse{
			{Event: &serverpb.Event{
				MessageId: "msg-1",
				Topic:     "server.bort_4.trip_service.src",
				Payload:   []byte(`{"data":1}`),
			}},
		},
		recvErr: fmt.Errorf("stream closed"),
	}

	repo.EXPECT().StreamGetEvents(gomock.Any()).Return(stream, nil)
	ded.EXPECT().IsDuplicate(gomock.Any(), "msg-1").Return(false, nil)
	pub.EXPECT().Publish(gomock.Any(), rabbitmq.PublishMessage{
		RoutingKey: "server.bort_4.trip_service.dst",
		Body:       []byte(`{"data":1}`),
		MessageID:  "msg-1",
	}).Return(nil)

	err := a.runGetEventsStream(ctx)
	// After receiving one event, next Recv returns error
	if err == nil {
		t.Fatal("expected error from second Recv, got nil")
	}

	// Verify ACK was sent (subscriber reg + ack = 2 sent messages)
	stream.sentMu.Lock()
	defer stream.sentMu.Unlock()
	if len(stream.sent) != 2 {
		t.Fatalf("expected 2 sent messages (registration + ack), got %d", len(stream.sent))
	}

	// Second message should be ACK
	ack := stream.sent[1].GetAck()
	if ack == nil {
		t.Fatal("expected ACK message")
	}
	if !ack.GetOk() {
		t.Error("expected ack.ok=true")
	}
	if ack.GetMessageId() != "msg-1" {
		t.Errorf("expected message_id 'msg-1', got %q", ack.GetMessageId())
	}
}

func TestRunGetEventsStream_DuplicateMessage_SkipsPublish(t *testing.T) {
	a, repo, _, _, ded := newStreamTestApp(t)
	ctx := context.Background()

	stream := &mockGetEventsStream{
		ctx: ctx,
		recvQueue: []*serverpb.GetEventResponse{
			{Event: &serverpb.Event{
				MessageId: "msg-dup",
				Topic:     "server.bort_4.trip_service.src",
				Payload:   []byte(`{"data":"dup"}`),
			}},
		},
		recvErr: fmt.Errorf("stream closed"),
	}

	repo.EXPECT().StreamGetEvents(gomock.Any()).Return(stream, nil)
	ded.EXPECT().IsDuplicate(gomock.Any(), "msg-dup").Return(true, nil)
	// pub.Publish must NOT be called — no expectation set

	err := a.runGetEventsStream(ctx)
	if err == nil {
		t.Fatal("expected error from second Recv, got nil")
	}

	// Verify ACK was sent with ok=true (duplicate is acked successfully)
	stream.sentMu.Lock()
	defer stream.sentMu.Unlock()
	if len(stream.sent) != 2 {
		t.Fatalf("expected 2 sent messages (registration + ack), got %d", len(stream.sent))
	}

	ack := stream.sent[1].GetAck()
	if ack == nil {
		t.Fatal("expected ACK message")
	}
	if !ack.GetOk() {
		t.Error("expected ack.ok=true for duplicate")
	}
	if ack.GetMessageId() != "msg-dup" {
		t.Errorf("expected message_id 'msg-dup', got %q", ack.GetMessageId())
	}
}

func TestRunGetEventsStream_RedisError_ProceedsWithPublish(t *testing.T) {
	a, repo, pub, _, ded := newStreamTestApp(t)
	ctx := context.Background()

	stream := &mockGetEventsStream{
		ctx: ctx,
		recvQueue: []*serverpb.GetEventResponse{
			{Event: &serverpb.Event{
				MessageId: "msg-redis-err",
				Topic:     "server.bort_4.trip_service.src",
				Payload:   []byte(`{"data":"redis-err"}`),
			}},
		},
		recvErr: fmt.Errorf("stream closed"),
	}

	repo.EXPECT().StreamGetEvents(gomock.Any()).Return(stream, nil)
	ded.EXPECT().IsDuplicate(gomock.Any(), "msg-redis-err").Return(false, errors.New("redis: connection refused"))
	pub.EXPECT().Publish(gomock.Any(), rabbitmq.PublishMessage{
		RoutingKey: "server.bort_4.trip_service.dst",
		Body:       []byte(`{"data":"redis-err"}`),
		MessageID:  "msg-redis-err",
	}).Return(nil)

	err := a.runGetEventsStream(ctx)
	if err == nil {
		t.Fatal("expected error from second Recv, got nil")
	}

	// Verify ACK was sent with ok=true (fail-open: publish succeeded)
	stream.sentMu.Lock()
	defer stream.sentMu.Unlock()
	if len(stream.sent) != 2 {
		t.Fatalf("expected 2 sent messages (registration + ack), got %d", len(stream.sent))
	}

	ack := stream.sent[1].GetAck()
	if ack == nil {
		t.Fatal("expected ACK message")
	}
	if !ack.GetOk() {
		t.Error("expected ack.ok=true (fail-open)")
	}
}

func TestRunGetEventsStream_RecvEvent_PublishError(t *testing.T) {
	a, repo, pub, _, ded := newStreamTestApp(t)
	ctx := context.Background()

	stream := &mockGetEventsStream{
		ctx: ctx,
		recvQueue: []*serverpb.GetEventResponse{
			{Event: &serverpb.Event{
				MessageId: "msg-2",
				Topic:     "server.bort_4.trip_service.src",
				Payload:   []byte(`{"data":2}`),
			}},
		},
		recvErr: fmt.Errorf("stream closed"),
	}

	repo.EXPECT().StreamGetEvents(gomock.Any()).Return(stream, nil)
	ded.EXPECT().IsDuplicate(gomock.Any(), "msg-2").Return(false, nil)
	pub.EXPECT().Publish(gomock.Any(), gomock.Any()).Return(errors.New("publish failed"))

	err := a.runGetEventsStream(ctx)
	if err == nil {
		t.Fatal("expected error from second Recv, got nil")
	}

	stream.sentMu.Lock()
	defer stream.sentMu.Unlock()
	if len(stream.sent) < 2 {
		t.Fatalf("expected at least 2 sent messages, got %d", len(stream.sent))
	}

	ack := stream.sent[1].GetAck()
	if ack == nil {
		t.Fatal("expected ACK message")
	}
	if ack.GetOk() {
		t.Error("expected ack.ok=false on publish error")
	}
	if ack.GetError() == "" {
		t.Error("expected non-empty error in ACK")
	}
}

func TestRunGetEventsStream_RecvError(t *testing.T) {
	a, repo, _, _, _ := newStreamTestApp(t)
	ctx := context.Background()

	stream := &mockGetEventsStream{
		ctx:     ctx,
		recvErr: errors.New("recv failed"),
	}

	repo.EXPECT().StreamGetEvents(gomock.Any()).Return(stream, nil)

	err := a.runGetEventsStream(ctx)
	if err == nil {
		t.Fatal("expected error, got nil")
	}
}

func TestRunGetEventsStream_InvalidEvent(t *testing.T) {
	a, repo, _, _, _ := newStreamTestApp(t)
	ctx := context.Background()

	stream := &mockGetEventsStream{
		ctx: ctx,
		recvQueue: []*serverpb.GetEventResponse{
			{Event: &serverpb.Event{
				MessageId: "msg-3",
				Topic:     "", // invalid: empty topic
				Payload:   []byte(`{"data":3}`),
			}},
		},
		recvErr: fmt.Errorf("stream closed"),
	}

	repo.EXPECT().StreamGetEvents(gomock.Any()).Return(stream, nil)

	err := a.runGetEventsStream(ctx)
	if err == nil {
		t.Fatal("expected error from second Recv, got nil")
	}

	// Should have sent registration + nack
	stream.sentMu.Lock()
	defer stream.sentMu.Unlock()
	if len(stream.sent) < 2 {
		t.Fatalf("expected at least 2 sent messages, got %d", len(stream.sent))
	}

	ack := stream.sent[1].GetAck()
	if ack == nil {
		t.Fatal("expected ACK message for invalid event")
	}
	if ack.GetOk() {
		t.Error("expected ack.ok=false for invalid event")
	}
}

func TestRunSendEventsStream_OpenError(t *testing.T) {
	a, repo, _, _, _ := newStreamTestApp(t)
	ctx := context.Background()

	openErr := errors.New("connection refused")
	repo.EXPECT().StreamSendEvents(gomock.Any()).Return(nil, openErr)

	err := a.runSendEventsStream(ctx)
	if err == nil {
		t.Fatal("expected error, got nil")
	}
	if !errors.Is(err, openErr) {
		t.Errorf("expected wrapped %v, got %v", openErr, err)
	}
}

func TestRunSendEventsStream_OpenError_ContextCanceled(t *testing.T) {
	a, repo, _, _, _ := newStreamTestApp(t)

	ctx, cancel := context.WithCancel(context.Background())
	cancel()

	repo.EXPECT().StreamSendEvents(gomock.Any()).Return(nil, context.Canceled)

	err := a.runSendEventsStream(ctx)
	if err != nil {
		t.Errorf("expected nil when context canceled, got: %v", err)
	}
}

func TestRunSendEventsStream_RegisterError(t *testing.T) {
	a, repo, _, _, _ := newStreamTestApp(t)
	ctx := context.Background()

	sendErr := errors.New("send failed")
	stream := &mockSendEventsClientStream{
		ctx:     ctx,
		sendErr: sendErr,
		recvErr: errors.New("should not reach recv"),
	}

	repo.EXPECT().StreamSendEvents(gomock.Any()).Return(stream, nil)

	err := a.runSendEventsStream(ctx)
	if err == nil {
		t.Fatal("expected error, got nil")
	}
	if !errors.Is(err, sendErr) {
		t.Errorf("expected wrapped %v, got %v", sendErr, err)
	}
}

func TestRunSendEventsStream_SubscribeError(t *testing.T) {
	a, repo, _, sub, _ := newStreamTestApp(t)
	ctx := context.Background()

	stream := &mockSendEventsClientStream{
		ctx:     ctx,
		recvErr: errors.New("should not reach recv"),
	}

	repo.EXPECT().StreamSendEvents(gomock.Any()).Return(stream, nil)
	sub.EXPECT().SubscribeChan(gomock.Any(), gomock.Any()).Return(nil, errors.New("subscribe failed"))

	err := a.runSendEventsStream(ctx)
	if err == nil {
		t.Fatal("expected error, got nil")
	}
}

func TestNackPendingDeliveries_EmptyPending(t *testing.T) {
	a, _, _, _, _ := newStreamTestApp(t)

	pending := newPendingDeliveries()

	// Should not panic on empty pending
	a.nackPendingDeliveries(pending)
}

func TestConsumeSendEventsAck_RecvError(t *testing.T) {
	a, _, _, _, _ := newStreamTestApp(t)

	stream := &mockSendEventsClientStream{
		ctx:     context.Background(),
		recvErr: errors.New("recv failed"),
	}

	pending := newPendingDeliveries()
	errCh := make(chan error, 1)

	a.consumeSendEventsAck(stream, pending, errCh)

	select {
	case err := <-errCh:
		if err == nil {
			t.Fatal("expected error, got nil")
		}
	default:
		t.Fatal("expected error on errCh")
	}
}

func TestConsumeSendEventsAck_AckOk(t *testing.T) {
	a, _, _, _, _ := newStreamTestApp(t)

	stream := &mockSendEventsClientStream{
		ctx: context.Background(),
		recvQueue: []*serverpb.SendEventResponse{
			{Ack: &serverpb.Ack{MessageId: "msg-1", Ok: true}},
		},
		recvErr: errors.New("stream end"),
	}

	pending := newPendingDeliveries()
	// Add a delivery with an Acknowledger that won't panic (zero-value Delivery.Ack will
	// fail but the test just checks the flow reaches the right branch)
	pending.add("msg-1", amqp.Delivery{MessageId: "msg-1"})

	errCh := make(chan error, 1)
	a.consumeSendEventsAck(stream, pending, errCh)

	// The message should have been taken from pending
	_, found := pending.take("msg-1")
	if found {
		t.Error("expected msg-1 to be taken from pending after ACK")
	}
}

func TestConsumeSendEventsAck_AckNotOk(t *testing.T) {
	a, _, _, _, _ := newStreamTestApp(t)

	stream := &mockSendEventsClientStream{
		ctx: context.Background(),
		recvQueue: []*serverpb.SendEventResponse{
			{Ack: &serverpb.Ack{MessageId: "msg-2", Ok: false, Error: "rejected"}},
		},
		recvErr: errors.New("stream end"),
	}

	pending := newPendingDeliveries()
	pending.add("msg-2", amqp.Delivery{MessageId: "msg-2"})

	errCh := make(chan error, 1)
	a.consumeSendEventsAck(stream, pending, errCh)

	// The message should have been taken from pending
	_, found := pending.take("msg-2")
	if found {
		t.Error("expected msg-2 to be taken from pending after NACK")
	}
}

func TestConsumeSendEventsAck_UnknownMessage(t *testing.T) {
	a, _, _, _, _ := newStreamTestApp(t)

	stream := &mockSendEventsClientStream{
		ctx: context.Background(),
		recvQueue: []*serverpb.SendEventResponse{
			{Ack: &serverpb.Ack{MessageId: "unknown-msg", Ok: true}},
		},
		recvErr: errors.New("stream end"),
	}

	pending := newPendingDeliveries()
	errCh := make(chan error, 1)

	// Should not panic with unknown message
	a.consumeSendEventsAck(stream, pending, errCh)
}

func TestConsumeSendEventsAck_NilAck(t *testing.T) {
	a, _, _, _, _ := newStreamTestApp(t)

	stream := &mockSendEventsClientStream{
		ctx: context.Background(),
		recvQueue: []*serverpb.SendEventResponse{
			{Ack: nil}, // nil ack should be skipped
		},
		recvErr: errors.New("stream end"),
	}

	pending := newPendingDeliveries()
	errCh := make(chan error, 1)

	a.consumeSendEventsAck(stream, pending, errCh)
}

func TestRunSendEventsStream_ContextCanceled_AfterSubscribe(t *testing.T) {
	a, repo, _, sub, _ := newStreamTestApp(t)

	ctx, cancel := context.WithCancel(context.Background())

	stream := &mockSendEventsClientStream{
		ctx:     ctx,
		recvErr: errors.New("stream end"),
	}

	repo.EXPECT().StreamSendEvents(gomock.Any()).Return(stream, nil)

	// Return a nil subscription - the code will call sub.Messages() and sub.Stop()
	// We can't create a real ChanSubscription, so use a different approach:
	// cancel context before the main loop reads from subscription
	sub.EXPECT().SubscribeChan(gomock.Any(), gomock.Any()).DoAndReturn(
		func(ctx context.Context, opt rabbitmq.SubscribeChanOptions) (*rabbitmq.ChanSubscription, error) {
			cancel() // cancel immediately
			return nil, errors.New("canceled")
		},
	)

	err := a.runSendEventsStream(ctx)
	// Should get subscribe error since we returned error
	if err == nil {
		t.Fatal("expected error, got nil")
	}
}
