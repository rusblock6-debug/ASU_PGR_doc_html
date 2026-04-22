package domain

import (
	"fmt"
	"strings"
)

// ToDestinationTopic transforms a source routing key to a destination routing key
// by replacing the ".src" suffix with ".dst".
func ToDestinationTopic(src string) string {
	return strings.Replace(src, ".src", ".dst", 1)
}

// ServerQueueName returns the queue name used by the server to consume events
// sent from a specific truck's service.
// Format: "server.bort_{truckID}.{service}.src"
func ServerQueueName(truckID int, service string) string {
	return fmt.Sprintf("server.bort_%d.%s.src", truckID, service)
}

// BortQueueName returns the queue name used by the bort to consume events
// sent from the server for a specific service.
// Format: "bort_{truckID}.server.{service}.src"
func BortQueueName(truckID int, service string) string {
	return fmt.Sprintf("bort_%d.server.%s.src", truckID, service)
}

// ServerQueuePattern returns a regex matching all server-side queues for a given truckID.
func ServerQueuePattern(truckID int) string {
	return fmt.Sprintf(`^server\.bort_%d\..*\.src$`, truckID)
}

// BortQueuePattern returns a regex matching all bort-side queues for a given truckID.
func BortQueuePattern(truckID int) string {
	return fmt.Sprintf(`^bort_%d\.server\..*\.src$`, truckID)
}
