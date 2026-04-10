package grpc

import (
	"context"
	"errors"
	"io"
	"sync"
	"wifi-event-dispatcher/domain"
	"wifi-event-dispatcher/internal/autorepub"
	"wifi-event-dispatcher/internal/dedup"
	"wifi-event-dispatcher/internal/rabbitmq"
	"wifi-event-dispatcher/server/internal/application"
	"wifi-event-dispatcher/server/serverpb"

	amqp "github.com/rabbitmq/amqp091-go"
	"github.com/rs/zerolog"
	"google.golang.org/grpc"
)

type server struct {
	serverpb.UnimplementedEventDispatchServiceServer
	logger          *zerolog.Logger
	app             application.App
	dedup           dedup.Service
	autorepubClient *autorepub.Client
}

var _ serverpb.EventDispatchServiceServer = (*server)(nil)

func RegisterServer(app application.App, svc dedup.Service, log zerolog.Logger, autorepubClient *autorepub.Client) *server {
	logger := log.With().Str("component", "grpc.server").Logger()
	return &server{app: app, dedup: svc, logger: &logger, autorepubClient: autorepubClient}
}

// isDuplicateDelivery checks whether the delivery is a duplicate.
// Returns true if the delivery was already seen (and has been Ack'd), false otherwise.
// An empty MessageId is treated as non-duplicate (dedup check skipped).
// On Redis error the check fails open (returns false).
func (s *server) isDuplicateDelivery(ctx context.Context, delivery amqp.Delivery) bool {
	if delivery.MessageId == "" {
		s.logger.Debug().Str("component", "consumer").Msg("received delivery with empty MessageId, skipping dedup check")
		return false
	}

	isDup, err := s.dedup.IsDuplicate(ctx, delivery.MessageId)
	if err != nil {
		s.logger.Warn().Err(err).Str("component", "consumer").Str("messageID", delivery.MessageId).Msg("redis error on dedup check, proceeding")
		return false
	}
	if isDup {
		_ = delivery.Ack(false)
		s.logger.Warn().Str("component", "consumer").Str("messageID", delivery.MessageId).Msg("duplicate delivery, dropping")
		return true
	}
	return false
}

func (s *server) Register(registrar grpc.ServiceRegistrar) {
	serverpb.RegisterEventDispatchServiceServer(registrar, s)
}

func (s *server) StreamBortSendEvents(stream serverpb.EventDispatchService_StreamBortSendEventsServer) error {
	sendAck := func(messageID string, err error) error {
		ack := &serverpb.Ack{
			MessageId: messageID,
			Ok:        err == nil,
		}
		if err != nil {
			ack.Error = err.Error()
		}
		return stream.Send(&serverpb.SendEventResponse{
			Ack: ack,
		})
	}

	ctx := stream.Context()

	for {
		req, err := stream.Recv()
		if err != nil {
			// io.EOF — клиент закрыл стрим, это нормальное завершение.
			if errors.Is(err, io.EOF) {
				return nil
			}
			return err
		}

		switch req.Kind.(type) {
		case *serverpb.SendEventRequest_Producer:
			producer := req.GetProducer()
			s.logger.Info().
				Int32("truck_id", producer.GetTruckId()).
				Str("stream", "StreamBortSendEvents").
				Msg("truck connected to stream")
			continue
		}

		ev := req.GetEvent()
		if ev == nil {
			continue
		}

		messageID := ev.GetMessageId()

		s.logger.Debug().
			Str("message_id", messageID).
			Str("topic", ev.GetTopic()).
			Msg("received event from bort")

		event, err := domain.EventFromProto(ev)
		if err != nil {
			_ = sendAck(messageID, err) // ошибка конвертации — только ACK, стрим не рвём
			continue
		}

		// Трансформация: bort_4.server.trip_service.src → bort_4.server.trip_service.dst
		event.Topic = domain.ToDestinationTopic(event.Topic)

		err = s.app.HandleEvent(ctx, event)

		if err != nil {
			s.logger.Err(err).Msg("failed to handle event")
		} else {
			s.logger.Debug().
				Str("message_id", messageID).
				Str("topic", event.Topic).
				Msg("published event to RabbitMQ")
		}

		if err := sendAck(messageID, err); err != nil {
			return err // не смогли отправить ACK — завершаем стрим
		}
	}
}
func (s *server) StreamBortGetEvents(stream serverpb.EventDispatchService_StreamBortGetEventsServer) error {
	ctx := stream.Context()

	type rabbitMsg struct {
		delivery amqp.Delivery
		sub      *rabbitmq.ChanSubscription
	}

	recvCh := make(chan *serverpb.GetEventRequest)
	recvErrCh := make(chan error, 1)
	msgCh := make(chan rabbitMsg)

	var subs []*rabbitmq.ChanSubscription
	var subsWg sync.WaitGroup
	pending := make(map[string]amqp.Delivery)
	var suspendedDistribution map[string][]int

	defer func() {
		// Nack все неподтверждённые сообщения — вернутся в очередь
		for _, d := range pending {
			_ = d.Nack(false, true)
		}

		for _, sub := range subs {
			_ = sub.Stop()
		}

		subsWg.Wait()

		if s.autorepubClient != nil && len(suspendedDistribution) > 0 {
			if err := s.autorepubClient.Resume(context.Background(), suspendedDistribution); err != nil {
				s.logger.Warn().Err(err).Msg("failed to resume autorepub after stream stop")
			}
		}
	}()

	go func() {
		defer close(recvCh)
		for {
			req, err := stream.Recv()
			if err != nil {
				recvErrCh <- err
				return
			}
			select {
			case recvCh <- req:
			case <-ctx.Done():
				return
			}
		}
	}()

	startReader := func(sub *rabbitmq.ChanSubscription) {
		subsWg.Add(1)
		go func() {
			defer subsWg.Done()
			for {
				select {
				case msg, ok := <-sub.Messages():
					if !ok {
						return
					}
					select {
					case msgCh <- rabbitMsg{delivery: msg, sub: sub}:
					case <-ctx.Done():
						return
					}
				case <-ctx.Done():
					return
				}
			}
		}()
	}

	for {
		select {
		case <-ctx.Done():
			return ctx.Err()

		case err := <-recvErrCh:
			if errors.Is(err, io.EOF) {
				return nil
			}
			return err

		case req, ok := <-recvCh:
			if !ok {
				return nil
			}

			switch req.Kind.(type) {
			case *serverpb.GetEventRequest_Subscriber:
				sub := req.GetSubscriber()
				truckID := sub.GetTruckId()
				s.logger.Info().
					Int32("truck_id", truckID).
					Str("stream", "StreamBortGetEvents").
					Msg("truck connected to stream")

				channels, err := s.app.SubscribeAll(ctx, int(truckID))
				if err != nil {
					return err
				}
				subs = append(subs, channels...)
				for _, ch := range channels {
					startReader(ch)
				}

				if s.autorepubClient == nil {
					s.logger.Warn().Msg("autorepub client is not configured, skipping suspend before subscribe")
				} else {
					dist, err := s.autorepubClient.GetDistribution(ctx)
					if err != nil {
						s.logger.Warn().Err(err).Msg("failed to get distribution before subscribe")
					} else {
						suspendedDistribution = dist
						if err := s.autorepubClient.Suspend(ctx, dist); err != nil {
							s.logger.Warn().Err(err).Msg("failed to suspend autorepub before subscribe")
						}
					}
				}

			case *serverpb.GetEventRequest_Ack:
				ack := req.GetAck()
				messageID := ack.GetMessageId()
				if delivery, ok := pending[messageID]; ok {
					if !ack.GetOk() {
						if err := delivery.Nack(false, true); err != nil {
							s.logger.Err(err).Msg("failed to nack")
						}
					} else {
						if err := delivery.Ack(false); err != nil {
							s.logger.Err(err).Msg("failed to ack")
						}
					}
					delete(pending, messageID)
				}
			}

		case msg := <-msgCh:
			if s.isDuplicateDelivery(ctx, msg.delivery) {
				continue
			}

			event, err := domain.NewEvent(msg.sub.QueueName(), msg.delivery.MessageId, msg.delivery.Body)
			if err != nil {
				s.logger.Err(err).Msg("failed to get event")
				_ = msg.delivery.Nack(false, true)
				continue
			}

			if err := stream.Send(&serverpb.GetEventResponse{
				Event: event.ToProto(),
			}); err != nil {
				return err
			}

			pending[event.MessageID] = msg.delivery
		}
	}
}
