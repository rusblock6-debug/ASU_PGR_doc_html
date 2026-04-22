package application

import (
	"context"
	"encoding/json"
	"io"
	"net/http"
	"net/http/httptest"
	"reflect"
	"sort"
	"testing"
	"time"

	"wifi-event-dispatcher/internal/autorepub"
	"wifi-event-dispatcher/internal/config"
	"wifi-event-dispatcher/internal/dedup"

	"github.com/rs/zerolog"
	"go.uber.org/mock/gomock"
)

func newTestApp(t *testing.T) (*app, *MockServerRepository, *MockEventPublisher, *MockRabbitSubscriber, *MockDedupService) {
	return newTestAppWithAutorepub(t, nil)
}

func newTestAppWithAutorepubAndServer(t *testing.T, srv *httptest.Server) (*app, *MockServerRepository, *MockEventPublisher, *MockRabbitSubscriber, *MockDedupService) {
	t.Helper()
	client := autorepub.NewClient(srv.URL, "", time.Second, zerolog.Nop())
	return newTestAppWithAutorepub(t, client)
}

func newTestAppWithAutorepub(t *testing.T, autorepubClient *autorepub.Client) (*app, *MockServerRepository, *MockEventPublisher, *MockRabbitSubscriber, *MockDedupService) {
	t.Helper()
	ctrl := gomock.NewController(t)

	repo := NewMockServerRepository(ctrl)
	pub := NewMockEventPublisher(ctrl)
	sub := NewMockRabbitSubscriber(ctrl)
	ded := NewMockDedupService(ctrl)
	disc := NewMockQueueDiscoverer(ctrl)
	disc.EXPECT().DiscoverQueues(gomock.Any(), gomock.Any()).Return([]string{"bort_42.server.trip.src"}, nil).AnyTimes()

	a := New(Deps{
		Cfg: config.BortConfig{
			TruckID:       42,
			ServerAddress: "localhost:8085",
		},
		Logger:           zerolog.Nop(),
		ServerRepository: repo,
		Publisher:        pub,
		Subscriber:       sub,
		Discovery:        disc,
		Dedup:            dedup.Service(ded),
		AutorepubClient:  autorepubClient,
	}).(*app)
	return a, repo, pub, sub, ded
}

func assertVehicleIDSet(t *testing.T, got, want []int) {
	t.Helper()

	gotCopy := append([]int(nil), got...)
	wantCopy := append([]int(nil), want...)
	sort.Ints(gotCopy)
	sort.Ints(wantCopy)

	if !reflect.DeepEqual(gotCopy, wantCopy) {
		t.Fatalf("vehicle IDs = %v, want %v", got, want)
	}
}

func TestNew(t *testing.T) {
	a, repo, pub, sub, _ := newTestApp(t)

	if a == nil {
		t.Fatal("New returned nil")
	}
	if a.cfg.TruckID != 42 {
		t.Errorf("TruckID = %d, want 42", a.cfg.TruckID)
	}
	if a.serverRepository != repo {
		t.Error("serverRepository not set correctly")
	}
	if a.publisher != pub {
		t.Error("publisher not set correctly")
	}
	if a.subscriber != sub {
		t.Error("subscriber not set correctly")
	}
	if a.wifiUp {
		t.Error("wifiUp should be false initially")
	}
	if a.streaming {
		t.Error("streaming should be false initially")
	}
}

func TestIsWifiUp_True(t *testing.T) {
	a, _, _, _, _ := newTestApp(t)

	up, err := a.isWifiUp([]byte(`{"data":{"value":true}}`))
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if !up {
		t.Error("expected wifi up = true")
	}
}

func TestIsWifiUp_False(t *testing.T) {
	a, _, _, _, _ := newTestApp(t)

	up, err := a.isWifiUp([]byte(`{"data":{"value":false}}`))
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if up {
		t.Error("expected wifi up = false")
	}
}

func TestIsWifiUp_InvalidJSON(t *testing.T) {
	a, _, _, _, _ := newTestApp(t)

	_, err := a.isWifiUp([]byte(`not json`))
	if err == nil {
		t.Fatal("expected error for invalid JSON")
	}
}

func TestIsWifiUp_EmptyObject(t *testing.T) {
	a, _, _, _, _ := newTestApp(t)

	up, err := a.isWifiUp([]byte(`{}`))
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}
	if up {
		t.Error("expected wifi up = false for empty object")
	}
}

func TestWifiTopic(t *testing.T) {
	a, _, _, _, _ := newTestApp(t)

	got := a.wifiTopic()
	want := "truck/42/sensor/wifi/fake_events"
	if got != want {
		t.Errorf("wifiTopic() = %q, want %q", got, want)
	}
}

func TestWifiTopic_DifferentTruckID(t *testing.T) {
	a, _, _, _, _ := newTestApp(t)
	a.cfg.TruckID = 7

	got := a.wifiTopic()
	want := "truck/7/sensor/wifi/fake_events"
	if got != want {
		t.Errorf("wifiTopic() = %q, want %q", got, want)
	}
}

type mockMessage struct {
	payload []byte
	topic   string
}

func (m *mockMessage) Duplicate() bool   { return false }
func (m *mockMessage) Qos() byte         { return 0 }
func (m *mockMessage) Retained() bool    { return false }
func (m *mockMessage) Topic() string     { return m.topic }
func (m *mockMessage) MessageID() uint16 { return 0 }
func (m *mockMessage) Payload() []byte   { return m.payload }
func (m *mockMessage) Ack()              {}

func TestHandleWifi_WifiUp_StartsStream(t *testing.T) {
	a, repo, _, _, _ := newTestApp(t)
	ctx := context.Background()

	// The supervisor goroutine will call these — allow any number of calls
	repo.EXPECT().StreamGetEvents(gomock.Any()).Return(nil, context.Canceled).AnyTimes()
	repo.EXPECT().StreamSendEvents(gomock.Any()).Return(nil, context.Canceled).AnyTimes()

	msg := &mockMessage{payload: []byte(`{"data":{"value":true}}`)}
	a.handleWifi(ctx, msg)

	a.mu.Lock()

	if !a.wifiUp {
		t.Error("wifiUp should be true after wifi up event")
	}
	if !a.streaming {
		t.Error("streaming should be true after wifi up event")
	}
	if a.streamSessionID != 1 {
		t.Errorf("streamSessionID = %d, want 1", a.streamSessionID)
	}
	if a.cancelFn == nil {
		t.Error("cancelFn should be set after starting stream")
	}

	// Clean up goroutine
	a.cancelFn()
	a.mu.Unlock()

	// Give goroutine time to exit
	time.Sleep(50 * time.Millisecond)
}

func TestHandleWifi_WifiUp_SuspendsAutorepubBeforeStreamStart(t *testing.T) {
	var suspendBody []byte

	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/autorepub/suspend":
			var err error
			suspendBody, err = io.ReadAll(r.Body)
			if err != nil {
				t.Errorf("failed to read suspend body: %v", err)
				http.Error(w, "read body failed", http.StatusInternalServerError)
				return
			}
			w.WriteHeader(http.StatusOK)
		default:
			t.Errorf("unexpected path: %s", r.URL.Path)
			http.Error(w, "unexpected path", http.StatusNotFound)
		}
	}))
	defer srv.Close()

	a, repo, _, _, _ := newTestAppWithAutorepubAndServer(t, srv)
	ctx := context.Background()

	repo.EXPECT().StreamGetEvents(gomock.Any()).Return(nil, context.Canceled).AnyTimes()
	repo.EXPECT().StreamSendEvents(gomock.Any()).Return(nil, context.Canceled).AnyTimes()

	a.handleWifi(ctx, &mockMessage{payload: []byte(`{"data":{"value":true}}`)})

	a.mu.Lock()
	if !a.streaming {
		a.mu.Unlock()
		t.Fatal("streaming should be true after wifi up")
	}
	gotSuspended := a.suspended
	cancel := a.cancelFn
	a.mu.Unlock()

	if len(suspendBody) == 0 {
		t.Fatal("expected suspend request to be sent")
	}

	var req struct {
		VehicleIDs []int `json:"vehicle_ids"`
	}
	if err := json.Unmarshal(suspendBody, &req); err != nil {
		t.Fatalf("failed to decode suspend request: %v", err)
	}

	assertVehicleIDSet(t, req.VehicleIDs, []int{42})

	if !gotSuspended {
		t.Error("suspended should be true after successful suspend")
	}

	if cancel != nil {
		cancel()
	}
	time.Sleep(50 * time.Millisecond)
}

func TestHandleWifi_WifiUp_SuspendError_DoesNotBlockStreamStart(t *testing.T) {
	suspendCalled := false

	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/autorepub/suspend":
			suspendCalled = true
			http.Error(w, "boom", http.StatusInternalServerError)
		default:
			t.Errorf("unexpected path: %s", r.URL.Path)
			http.Error(w, "unexpected path", http.StatusNotFound)
		}
	}))
	defer srv.Close()

	a, repo, _, _, _ := newTestAppWithAutorepubAndServer(t, srv)
	ctx := context.Background()

	repo.EXPECT().StreamGetEvents(gomock.Any()).Return(nil, context.Canceled).AnyTimes()
	repo.EXPECT().StreamSendEvents(gomock.Any()).Return(nil, context.Canceled).AnyTimes()

	a.handleWifi(ctx, &mockMessage{payload: []byte(`{"data":{"value":true}}`)})

	a.mu.Lock()
	if !a.streaming {
		a.mu.Unlock()
		t.Fatal("streaming should be true even when Suspend fails")
	}
	gotSuspended := a.suspended
	cancel := a.cancelFn
	a.mu.Unlock()

	if !suspendCalled {
		t.Fatal("expected suspend request to be sent")
	}
	if gotSuspended {
		t.Error("suspended should be false when suspend call failed")
	}

	if cancel != nil {
		cancel()
	}
	time.Sleep(50 * time.Millisecond)
}

func TestHandleWifi_WifiDown_StopsStream(t *testing.T) {
	a, repo, _, _, _ := newTestApp(t)
	ctx := context.Background()

	repo.EXPECT().StreamGetEvents(gomock.Any()).Return(nil, context.Canceled).AnyTimes()
	repo.EXPECT().StreamSendEvents(gomock.Any()).Return(nil, context.Canceled).AnyTimes()

	// Bring wifi up
	a.handleWifi(ctx, &mockMessage{payload: []byte(`{"data":{"value":true}}`)})

	a.mu.Lock()
	if !a.streaming {
		a.mu.Unlock()
		t.Fatal("streaming should be true after wifi up")
	}
	a.mu.Unlock()

	// Bring wifi down
	a.handleWifi(ctx, &mockMessage{payload: []byte(`{"data":{"value":false}}`)})

	// Give goroutine time to finish
	time.Sleep(50 * time.Millisecond)

	a.mu.Lock()
	defer a.mu.Unlock()

	if a.wifiUp {
		t.Error("wifiUp should be false after wifi down event")
	}
	if a.streaming {
		t.Error("streaming should be false after wifi down event")
	}
	if a.cancelFn != nil {
		t.Error("cancelFn should be nil after stopping stream")
	}
}

func TestHandleWifi_WifiDown_ResumesAutorepubAndClearsSuspended(t *testing.T) {
	var resumeBody []byte

	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/autorepub/suspend":
			w.WriteHeader(http.StatusOK)
		case "/autorepub/resume":
			var err error
			resumeBody, err = io.ReadAll(r.Body)
			if err != nil {
				t.Errorf("failed to read resume body: %v", err)
				http.Error(w, "read body failed", http.StatusInternalServerError)
				return
			}
			w.WriteHeader(http.StatusOK)
		default:
			t.Errorf("unexpected path: %s", r.URL.Path)
			http.Error(w, "unexpected path", http.StatusNotFound)
		}
	}))
	defer srv.Close()

	a, repo, _, _, _ := newTestAppWithAutorepubAndServer(t, srv)
	ctx := context.Background()

	repo.EXPECT().StreamGetEvents(gomock.Any()).Return(nil, context.Canceled).AnyTimes()
	repo.EXPECT().StreamSendEvents(gomock.Any()).Return(nil, context.Canceled).AnyTimes()

	a.handleWifi(ctx, &mockMessage{payload: []byte(`{"data":{"value":true}}`)})
	a.handleWifi(ctx, &mockMessage{payload: []byte(`{"data":{"value":false}}`)})

	time.Sleep(50 * time.Millisecond)

	if len(resumeBody) == 0 {
		t.Fatal("expected resume request to be sent")
	}

	var req struct {
		VehicleIDs []int `json:"vehicle_ids"`
	}
	if err := json.Unmarshal(resumeBody, &req); err != nil {
		t.Fatalf("failed to decode resume request: %v", err)
	}
	assertVehicleIDSet(t, req.VehicleIDs, []int{42})

	a.mu.Lock()
	defer a.mu.Unlock()

	if a.suspended {
		t.Error("suspended should be false after resume")
	}
}

func TestHandleWifi_WifiDown_ResumeError_DoesNotBlockAndClearsSuspended(t *testing.T) {
	resumeCalled := false

	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/autorepub/suspend":
			w.WriteHeader(http.StatusOK)
		case "/autorepub/resume":
			resumeCalled = true
			http.Error(w, "boom", http.StatusInternalServerError)
		default:
			t.Errorf("unexpected path: %s", r.URL.Path)
			http.Error(w, "unexpected path", http.StatusNotFound)
		}
	}))
	defer srv.Close()

	a, repo, _, _, _ := newTestAppWithAutorepubAndServer(t, srv)
	ctx := context.Background()

	repo.EXPECT().StreamGetEvents(gomock.Any()).Return(nil, context.Canceled).AnyTimes()
	repo.EXPECT().StreamSendEvents(gomock.Any()).Return(nil, context.Canceled).AnyTimes()

	a.handleWifi(ctx, &mockMessage{payload: []byte(`{"data":{"value":true}}`)})
	a.handleWifi(ctx, &mockMessage{payload: []byte(`{"data":{"value":false}}`)})

	time.Sleep(50 * time.Millisecond)

	if !resumeCalled {
		t.Fatal("expected resume request to be sent")
	}

	a.mu.Lock()
	defer a.mu.Unlock()

	if a.streaming {
		t.Error("streaming should be false after wifi down event")
	}
	if a.cancelFn != nil {
		t.Error("cancelFn should be nil after stopping stream")
	}
	if a.suspended {
		t.Error("suspended should be false even when resume call failed")
	}
}

func TestHandleWifi_WifiDown_NotSuspended_SkipsResume(t *testing.T) {
	resumeCalled := false

	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch r.URL.Path {
		case "/autorepub/suspend":
			http.Error(w, "boom", http.StatusInternalServerError)
		case "/autorepub/resume":
			resumeCalled = true
			w.WriteHeader(http.StatusOK)
		default:
			t.Errorf("unexpected path: %s", r.URL.Path)
			http.Error(w, "unexpected path", http.StatusNotFound)
		}
	}))
	defer srv.Close()

	a, repo, _, _, _ := newTestAppWithAutorepubAndServer(t, srv)
	ctx := context.Background()

	repo.EXPECT().StreamGetEvents(gomock.Any()).Return(nil, context.Canceled).AnyTimes()
	repo.EXPECT().StreamSendEvents(gomock.Any()).Return(nil, context.Canceled).AnyTimes()

	a.handleWifi(ctx, &mockMessage{payload: []byte(`{"data":{"value":true}}`)})
	a.handleWifi(ctx, &mockMessage{payload: []byte(`{"data":{"value":false}}`)})

	time.Sleep(50 * time.Millisecond)

	if resumeCalled {
		t.Fatal("resume should not be called when not suspended")
	}

	a.mu.Lock()
	defer a.mu.Unlock()

	if a.suspended {
		t.Fatalf("suspended = %v, want false", a.suspended)
	}
}

func TestHandleWifi_SameState_NoChange(t *testing.T) {
	a, _, _, _, _ := newTestApp(t)
	ctx := context.Background()

	// Send false when already false -> no change
	a.handleWifi(ctx, &mockMessage{payload: []byte(`{"data":{"value":false}}`)})

	a.mu.Lock()
	defer a.mu.Unlock()

	if a.wifiUp {
		t.Error("wifiUp should remain false")
	}
	if a.streaming {
		t.Error("streaming should remain false")
	}
}

func TestHandleWifi_SameStateUp_NoExtraStream(t *testing.T) {
	a, repo, _, _, _ := newTestApp(t)
	ctx := context.Background()

	repo.EXPECT().StreamGetEvents(gomock.Any()).Return(nil, context.Canceled).AnyTimes()
	repo.EXPECT().StreamSendEvents(gomock.Any()).Return(nil, context.Canceled).AnyTimes()

	msg := &mockMessage{payload: []byte(`{"data":{"value":true}}`)}
	a.handleWifi(ctx, msg)

	a.mu.Lock()
	sessionBefore := a.streamSessionID
	a.mu.Unlock()

	// Duplicate wifi up -> should not start new session
	a.handleWifi(ctx, msg)

	a.mu.Lock()

	if a.streamSessionID != sessionBefore {
		t.Errorf("streamSessionID changed from %d to %d on duplicate wifi up", sessionBefore, a.streamSessionID)
	}

	if a.cancelFn != nil {
		a.cancelFn()
	}
	a.mu.Unlock()

	time.Sleep(50 * time.Millisecond)
}

func TestHandleWifi_InvalidPayload(t *testing.T) {
	a, _, _, _, _ := newTestApp(t)
	ctx := context.Background()

	a.handleWifi(ctx, &mockMessage{payload: []byte(`not json`)})

	a.mu.Lock()
	defer a.mu.Unlock()

	if a.wifiUp {
		t.Error("wifiUp should remain false on invalid payload")
	}
	if a.streaming {
		t.Error("streaming should remain false on invalid payload")
	}
}

func TestFinishStreamSession_MatchingID(t *testing.T) {
	a, _, _, _, _ := newTestApp(t)

	_, cancel := context.WithCancel(context.Background())
	a.mu.Lock()
	a.streaming = true
	a.streamSessionID = 5
	a.cancelFn = cancel
	a.mu.Unlock()

	a.finishStreamSession(5)

	a.mu.Lock()
	defer a.mu.Unlock()

	if a.streaming {
		t.Error("streaming should be false after matching finishStreamSession")
	}
	if a.cancelFn != nil {
		t.Error("cancelFn should be nil after matching finishStreamSession")
	}

	cancel() // cleanup
}

func TestFinishStreamSession_MismatchedID(t *testing.T) {
	a, _, _, _, _ := newTestApp(t)

	_, cancel := context.WithCancel(context.Background())
	a.mu.Lock()
	a.streaming = true
	a.streamSessionID = 5
	a.cancelFn = cancel
	a.mu.Unlock()

	a.finishStreamSession(3)

	a.mu.Lock()
	defer a.mu.Unlock()

	if !a.streaming {
		t.Error("streaming should remain true for mismatched session ID")
	}
	if a.cancelFn == nil {
		t.Error("cancelFn should remain set for mismatched session ID")
	}

	cancel() // cleanup
}

func TestStopStreamLocked_CancelsContext(t *testing.T) {
	a, _, _, _, _ := newTestApp(t)

	ctx, cancel := context.WithCancel(context.Background())
	a.cancelFn = cancel
	a.streaming = true

	a.stopStreamLocked()

	select {
	case <-ctx.Done():
		// expected
	case <-time.After(time.Second):
		t.Fatal("context should have been cancelled by stopStreamLocked")
	}

	if a.streaming {
		t.Error("streaming should be false after stopStreamLocked")
	}
	if a.cancelFn != nil {
		t.Error("cancelFn should be nil after stopStreamLocked")
	}
}

func TestStopStreamLocked_NilCancelFn(t *testing.T) {
	a, _, _, _, _ := newTestApp(t)

	a.cancelFn = nil
	a.streaming = true

	// Should not panic
	a.stopStreamLocked()

	if a.streaming {
		t.Error("streaming should be false after stopStreamLocked")
	}
}

func TestRunStreamAttempt_ContextCanceled(t *testing.T) {
	a, repo, _, sub, _ := newTestApp(t)

	ctx, cancel := context.WithCancel(context.Background())
	cancel()

	repo.EXPECT().StreamGetEvents(gomock.Any()).Return(nil, context.Canceled).AnyTimes()
	repo.EXPECT().StreamSendEvents(gomock.Any()).Return(nil, context.Canceled).AnyTimes()
	sub.EXPECT().SubscribeChan(gomock.Any(), gomock.Any()).AnyTimes()

	err := a.runStreamAttempt(ctx)
	if err != nil {
		t.Errorf("expected nil error when context is canceled, got: %v", err)
	}
}
