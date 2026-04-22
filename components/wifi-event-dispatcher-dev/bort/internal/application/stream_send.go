package application

import (
	"context"
	"errors"
	"fmt"
	"sync"
	"wifi-event-dispatcher/domain"
	"wifi-event-dispatcher/internal/rabbitmq"
	"wifi-event-dispatcher/server/serverpb"

	amqp "github.com/rabbitmq/amqp091-go"
)

func (a *app) runSendEventsStream(ctx context.Context) error {
	defer func() {
		a.logger.Info().Msg("gRPC send-events stream closed")
	}()

	stream, err := a.serverRepository.StreamSendEvents(ctx)
	if err != nil {
		if ctx.Err() != nil {
			return nil
		}
		return fmt.Errorf("open gRPC send-events stream: %w", err)
	}

	// Register as producer
	err = stream.Send(&serverpb.SendEventRequest{
		Kind: &serverpb.SendEventRequest_Producer{
			Producer: &serverpb.Client{TruckId: int32(a.cfg.TruckID)},
		},
	})
	if err != nil {
		if ctx.Err() != nil {
			return nil
		}
		return fmt.Errorf("register as producer: %w", err)
	}

	// Discover local queues by pattern
	pattern := domain.BortQueuePattern(a.cfg.TruckID)
	queues, err := a.discovery.DiscoverQueues(ctx, pattern)
	if err != nil {
		return fmt.Errorf("discover bort queues: %w", err)
	}
	if len(queues) == 0 {
		a.logger.Warn().Str("pattern", pattern).Msg("no bort queues discovered, nothing to send")
		return nil
	}

	// Subscribe to all discovered queues and fan-in into a single channel
	type bortMsg struct {
		delivery  amqp.Delivery
		queueName string
	}
	msgCh := make(chan bortMsg)
	var subs []*rabbitmq.ChanSubscription
	var subsWg sync.WaitGroup

	defer func() {
		for _, sub := range subs {
			_ = sub.Stop()
		}
		subsWg.Wait()
	}()

	for _, queueName := range queues {
		sub, err := a.subscriber.SubscribeChan(ctx, rabbitmq.SubscribeChanOptions{
			Queue:    queueName,
			Prefetch: 1,
		})
		if err != nil {
			a.logger.Warn().Str("queue", queueName).Err(err).Msg("failed to subscribe to bort queue, skipping")
			continue
		}
		subs = append(subs, sub)

		subsWg.Add(1)
		go func(s *rabbitmq.ChanSubscription) {
			defer subsWg.Done()
			for {
				select {
				case msg, ok := <-s.Messages():
					if !ok {
						return
					}
					select {
					case msgCh <- bortMsg{delivery: msg, queueName: s.QueueName()}:
					case <-ctx.Done():
						return
					}
				case <-ctx.Done():
					return
				}
			}
		}(sub)
	}

	if len(subs) == 0 {
		return errors.New("failed to subscribe to any bort queue")
	}

	pending := newPendingDeliveries()
	ackErrCh := make(chan error, 1)
	go a.consumeSendEventsAck(stream, pending, ackErrCh)

	// Main loop: read from merged channel → send to server
	for {
		select {
		case <-ctx.Done():
			a.nackPendingDeliveries(pending)
			return nil
		case err := <-ackErrCh:
			a.nackPendingDeliveries(pending)
			if ctx.Err() == nil {
				return fmt.Errorf("receive ACK from server: %w", err)
			}
			return nil
		case msg := <-msgCh:
			event, err := domain.NewEvent(msg.queueName, msg.delivery.MessageId, msg.delivery.Body)
			if err != nil {
				a.logger.Err(err).Msg("failed to create event from delivery")
				_ = msg.delivery.Nack(false, true)
				continue
			}

			pending.add(event.MessageID, msg.delivery)

			err = stream.Send(&serverpb.SendEventRequest{
				Kind: &serverpb.SendEventRequest_Event{
					Event: event.ToProto(),
				},
			})
			if err == nil {
				a.logger.Debug().
					Str("message_id", event.MessageID).
					Str("topic", event.Topic).
					Msg("sent event to server")
			}
			if err != nil {
				pending.remove(event.MessageID)
				_ = msg.delivery.Nack(false, true)
				if ctx.Err() != nil {
					return nil
				}
				return fmt.Errorf("send event to server: %w", err)
			}
		}
	}
}

func (a *app) consumeSendEventsAck(
	stream serverpb.EventDispatchService_StreamBortSendEventsClient,
	pending *pendingDeliveries,
	errCh chan<- error,
) {
	for {
		resp, err := stream.Recv()
		if err != nil {
			select {
			case errCh <- err:
			default:
			}
			return
		}

		ack := resp.GetAck()
		if ack == nil {
			continue
		}

		a.logger.Debug().
			Str("message_id", ack.GetMessageId()).
			Bool("ok", ack.GetOk()).
			Msg("received ACK from server")

		delivery, ok := pending.take(ack.GetMessageId())
		if !ok {
			a.logger.Warn().
				Str("message_id", ack.GetMessageId()).
				Msg("received ACK for unknown message")
			continue
		}

		if ack.GetOk() {
			if err := delivery.Ack(false); err != nil {
				a.logger.Err(err).
					Str("message_id", ack.GetMessageId()).
					Msg("failed to ACK local message")
			}
			continue
		}

		if err := delivery.Nack(false, true); err != nil {
			a.logger.Err(err).
				Str("message_id", ack.GetMessageId()).
				Msg("failed to NACK local message")
		}
	}
}

func (a *app) nackPendingDeliveries(pending *pendingDeliveries) {
	for _, delivery := range pending.drain() {
		if err := delivery.Nack(false, true); err != nil {
			a.logger.Err(err).Msg("failed to NACK pending message")
		}
	}
}
