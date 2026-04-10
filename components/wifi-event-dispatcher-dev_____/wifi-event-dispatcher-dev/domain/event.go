package domain

import (
	"errors"
	"fmt"
	"wifi-event-dispatcher/server/serverpb"

	"github.com/google/uuid"
)

type Event struct {
	Topic     string
	MessageID string
	Payload   []byte
}

func NewEvent(topic, messageID string, payload []byte) (*Event, error) {
	if topic == "" {
		return nil, errors.New("topic is empty")
	}

	if messageID == "" {
		msgUUID, err := uuid.NewV7()
		if err != nil {
			return nil, fmt.Errorf("generate uuid: %w", err)
		}
		messageID = msgUUID.String()
	}

	if payload == nil {
		return nil, errors.New("payload is empty")
	}

	return &Event{
		Topic:     topic,
		MessageID: messageID,
		Payload:   payload,
	}, nil
}

func (e *Event) ToProto() *serverpb.Event {
	return &serverpb.Event{
		Topic:     e.Topic,
		MessageId: e.MessageID,
		Payload:   e.Payload,
	}
}
