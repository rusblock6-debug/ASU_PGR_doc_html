package application

import (
	"sync"

	amqp "github.com/rabbitmq/amqp091-go"
)

type pendingDeliveries struct {
	mu   sync.Mutex
	byID map[string]amqp.Delivery
}

func newPendingDeliveries() *pendingDeliveries {
	return &pendingDeliveries{
		byID: make(map[string]amqp.Delivery),
	}
}

func (p *pendingDeliveries) add(messageID string, delivery amqp.Delivery) {
	p.mu.Lock()
	defer p.mu.Unlock()
	p.byID[messageID] = delivery
}

func (p *pendingDeliveries) remove(messageID string) {
	p.mu.Lock()
	defer p.mu.Unlock()
	delete(p.byID, messageID)
}

func (p *pendingDeliveries) take(messageID string) (amqp.Delivery, bool) {
	p.mu.Lock()
	defer p.mu.Unlock()

	delivery, ok := p.byID[messageID]
	if !ok {
		return amqp.Delivery{}, false
	}

	delete(p.byID, messageID)
	return delivery, true
}

func (p *pendingDeliveries) drain() []amqp.Delivery {
	p.mu.Lock()
	defer p.mu.Unlock()

	deliveries := make([]amqp.Delivery, 0, len(p.byID))
	for messageID, delivery := range p.byID {
		deliveries = append(deliveries, delivery)
		delete(p.byID, messageID)
	}

	return deliveries
}
