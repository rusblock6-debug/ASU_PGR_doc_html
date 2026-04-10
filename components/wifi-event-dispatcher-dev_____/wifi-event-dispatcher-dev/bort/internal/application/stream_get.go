package application

import (
	"context"
	"fmt"
	"wifi-event-dispatcher/domain"
	"wifi-event-dispatcher/internal/rabbitmq"
	"wifi-event-dispatcher/server/serverpb"
)

func (a *app) runGetEventsStream(ctx context.Context) error {
	defer func() {
		a.logger.Info().Msg("gRPC get-events stream closed")
	}()

	stream, err := a.serverRepository.StreamGetEvents(ctx)
	if err != nil {
		if ctx.Err() != nil {
			return nil
		}
		return fmt.Errorf("open gRPC get-events stream: %w", err)
	}

	// Send subscriber registration
	err = stream.Send(&serverpb.GetEventRequest{
		Kind: &serverpb.GetEventRequest_Subscriber{
			Subscriber: &serverpb.Client{
				TruckId: int32(a.cfg.TruckID),
			},
		},
	})
	if err != nil {
		if ctx.Err() != nil {
			return nil
		}
		return fmt.Errorf("send subscriber registration: %w", err)
	}

	a.logger.Info().Int("truck_id", a.cfg.TruckID).Msg("registered as subscriber")

	sendAck := func(messageID string, ok bool, ackError string) error {
		err := stream.Send(&serverpb.GetEventRequest{
			Kind: &serverpb.GetEventRequest_Ack{
				Ack: &serverpb.Ack{
					MessageId: messageID,
					Ok:        ok,
					Error:     ackError,
				},
			},
		})
		if err != nil {
			if ctx.Err() != nil {
				return nil
			}
			return fmt.Errorf("send event ACK: %w", err)
		}

		return nil
	}

	for {
		resp, err := stream.Recv()
		if err != nil {
			if ctx.Err() != nil {
				return nil
			}
			return fmt.Errorf("receive event from server: %w", err)
		}

		rawEvent := resp.GetEvent()
		messageID := rawEvent.GetMessageId()

		event, err := domain.EventFromProto(rawEvent)
		if err != nil {
			a.logger.Err(err).
				Str("message_id", messageID).
				Msg("failed to parse event")

			if err := sendAck(messageID, false, err.Error()); err != nil {
				return err
			}
			continue
		}

		a.logger.Debug().
			Str("message_id", event.MessageID).
			Str("topic", event.Topic).
			Msg("received event from server")

		// event.Topic: server.bort_4.trip_service.src
		// publisher need .dst
		routingKey := domain.ToDestinationTopic(event.Topic)

		// Dedup check before publishing to local RabbitMQ
		dup, err := a.dedup.IsDuplicate(ctx, event.MessageID)
		if err != nil {
			a.logger.Warn().Err(err).Str("message_id", event.MessageID).Msg("dedup Redis error, proceeding with publish")
		} else if dup {
			a.logger.Warn().Str("message_id", event.MessageID).Msg("duplicate message, skipping publish")
			if err := sendAck(event.MessageID, true, ""); err != nil {
				return err
			}
			continue
		}

		// Publish to local RabbitMQ
		pubErr := a.publisher.Publish(ctx, rabbitmq.PublishMessage{
			RoutingKey: routingKey,
			Body:       event.Payload,
			MessageID:  event.MessageID,
		})

		ackOk := true
		ackError := ""
		if pubErr != nil {
			ackOk = false
			ackError = pubErr.Error()
			a.logger.Err(pubErr).
				Str("message_id", event.MessageID).
				Msg("failed to publish event to local RabbitMQ")
		}

		// Send ACK back to server
		if err := sendAck(event.MessageID, ackOk, ackError); err != nil {
			return err
		}
	}
}
