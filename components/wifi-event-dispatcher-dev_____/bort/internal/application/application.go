package application

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"sync"
	"time"

	"wifi-event-dispatcher/bort/internal/domain"
	"wifi-event-dispatcher/bort/internal/mqtt"
	"wifi-event-dispatcher/internal/autorepub"
	"wifi-event-dispatcher/internal/config"
	"wifi-event-dispatcher/internal/dedup"
	"wifi-event-dispatcher/internal/rabbitmq"

	paho "github.com/eclipse/paho.mqtt.golang"
	"github.com/rs/zerolog"
	"go.uber.org/fx"
	"golang.org/x/sync/errgroup"
)

type EventPublisher interface {
	Publish(ctx context.Context, msg rabbitmq.PublishMessage) error
}

type RabbitSubscriber interface {
	SubscribeChan(ctx context.Context, opt rabbitmq.SubscribeChanOptions) (*rabbitmq.ChanSubscription, error)
}

type QueueDiscoverer interface {
	DiscoverQueues(ctx context.Context, nameRegex string) ([]string, error)
}

type App interface {
	Start(ctx context.Context) error
}

type app struct {
	cfg              config.BortConfig
	logger           *zerolog.Logger
	serverRepository domain.ServerRepository
	publisher        EventPublisher
	subscriber       RabbitSubscriber
	discovery        QueueDiscoverer
	dedup            dedup.Service
	autorepubClient  *autorepub.Client

	mu              sync.Mutex
	wifiUp          bool
	streaming       bool
	streamSessionID uint64
	cancelFn        context.CancelFunc
	suspended       bool
}

var _ App = (*app)(nil)

const (
	streamRetryInitialDelay = 1 * time.Second
	streamRetryMaxDelay     = 30 * time.Second
)

type Deps struct {
	fx.In

	Cfg              config.BortConfig
	Logger           zerolog.Logger
	ServerRepository domain.ServerRepository
	Publisher        EventPublisher
	Subscriber       RabbitSubscriber
	Discovery        QueueDiscoverer
	Dedup            dedup.Service
	AutorepubClient  *autorepub.Client `optional:"true"`
}

func New(deps Deps) App {
	logger := deps.Logger
	return &app{
		cfg:              deps.Cfg,
		logger:           &logger,
		serverRepository: deps.ServerRepository,
		publisher:        deps.Publisher,
		subscriber:       deps.Subscriber,
		discovery:        deps.Discovery,
		dedup:            deps.Dedup,
		autorepubClient:  deps.AutorepubClient,
	}
}

func (a *app) Start(ctx context.Context) error {
	g, ctx := errgroup.WithContext(ctx)

	routes := []mqtt.Route{
		{Topic: a.wifiTopic(), QoS: 1, Handler: a.handleWifi},
	}

	wifiSub := mqtt.NewSubscriber(
		a.cfg.NanoMq.Url(),
		a.cfg.NanoMqClient(),
		routes,
		a.logger,
	)

	g.Go(func() error {
		return wifiSub.Start(ctx)
	})

	return g.Wait()
}

func (a *app) handleWifi(ctx context.Context, msg paho.Message) {
	wifiUp, err := a.isWifiUp(msg.Payload())
	if err != nil {
		a.logger.Err(err).Msg("failed to parse wifi event")
		return
	}

	a.mu.Lock()
	defer a.mu.Unlock()

	previousWifiUp := a.wifiUp
	a.wifiUp = wifiUp

	if wifiUp == previousWifiUp {
		return
	}

	if wifiUp {
		if !a.streaming {
			a.startStreamLocked(ctx)
		}
		return
	}

	if a.streaming {
		a.stopStreamLocked()
		return
	}
}

func (a *app) startStreamLocked(ctx context.Context) {
	a.suspended = false

	if a.autorepubClient == nil {
		a.logger.Warn().Msg("autorepub client is not configured, skipping suspend before stream startup")
	} else {
		if err := a.autorepubClient.SuspendDirect(ctx, []int{a.cfg.TruckID}); err != nil {
			a.logger.Warn().Err(err).Msg("failed to suspend autorepub before stream startup")
		} else {
			a.suspended = true
		}
	}

	streamCtx, cancel := context.WithCancel(ctx)
	a.streamSessionID++
	sessionID := a.streamSessionID

	a.cancelFn = cancel
	a.streaming = true

	go a.runStreamSupervisor(streamCtx, sessionID)

	a.logger.Info().
		Uint64("session_id", sessionID).
		Msg("wifi up - gRPC stream supervisor started")
}

func (a *app) stopStreamLocked() {
	if a.cancelFn != nil {
		a.cancelFn()
	}
	a.cancelFn = nil
	a.streaming = false

	if !a.suspended {
		a.logger.Debug().Msg("not suspended, skipping resume after stream stop")
	} else if a.autorepubClient == nil {
		a.logger.Warn().Msg("autorepub client is not configured, skipping resume after stream stop")
	} else {
		if err := a.autorepubClient.ResumeDirect(context.Background(), []int{a.cfg.TruckID}); err != nil {
			a.logger.Warn().Err(err).Msg("failed to resume autorepub after stream stop")
		}
	}

	a.suspended = false

	a.logger.Info().
		Uint64("session_id", a.streamSessionID).
		Msg("wifi down - gRPC streams stop requested")
}

func (a *app) runStreamSupervisor(ctx context.Context, sessionID uint64) {
	defer a.finishStreamSession(sessionID)

	retryDelay := streamRetryInitialDelay

	for {
		err := a.runStreamAttempt(ctx)
		if ctx.Err() != nil {
			return
		}

		if err == nil {
			err = errors.New("gRPC stream session ended unexpectedly")
		}

		a.logger.Err(err).
			Uint64("session_id", sessionID).
			Dur("retry_in", retryDelay).
			Msg("gRPC stream session closed with error, retrying")

		timer := time.NewTimer(retryDelay)
		select {
		case <-ctx.Done():
			timer.Stop()
			return
		case <-timer.C:
		}

		retryDelay *= 2
		if retryDelay > streamRetryMaxDelay {
			retryDelay = streamRetryMaxDelay
		}
	}
}

func (a *app) runStreamAttempt(ctx context.Context) error {
	g, runCtx := errgroup.WithContext(ctx)

	g.Go(func() error {
		return a.runGetEventsStream(runCtx)
	})
	g.Go(func() error {
		return a.runSendEventsStream(runCtx)
	})

	err := g.Wait()
	if err != nil {
		if errors.Is(err, context.Canceled) || ctx.Err() != nil {
			return nil
		}
		return err
	}

	if ctx.Err() != nil {
		return nil
	}

	return errors.New("both gRPC streams exited")
}

func (a *app) finishStreamSession(sessionID uint64) {
	a.mu.Lock()
	defer a.mu.Unlock()

	if a.streamSessionID != sessionID {
		return
	}

	a.cancelFn = nil
	a.streaming = false

	a.logger.Info().
		Uint64("session_id", sessionID).
		Msg("gRPC stream supervisor stopped")
}

type wifiEvent struct {
	Data struct {
		Value bool `json:"value"`
	} `json:"data"`
}

func (a *app) isWifiUp(payload []byte) (bool, error) {
	var event wifiEvent
	if err := json.Unmarshal(payload, &event); err != nil {
		return false, err
	}
	return event.Data.Value, nil
}

func (a *app) wifiTopic() string {
	return fmt.Sprintf("truck/%d/sensor/wifi/fake_events", a.cfg.TruckID)
}
