include .env
export

.PHONY: test coverage run-bort run-server

run-bort:
	go run ./cmd/bort

run-server:
	go run ./cmd/server

test:
	go test -race ./...

COVER_PKGS = wifi-event-dispatcher/domain/...,wifi-event-dispatcher/bort/internal/application/...,wifi-event-dispatcher/server/internal/...,wifi-event-dispatcher/internal/config/...,wifi-event-dispatcher/internal/dedup/...,wifi-event-dispatcher/internal/redis/...,wifi-event-dispatcher/internal/fx/dedup/...

coverage:
	go test -race -coverprofile=coverage.out -covermode=atomic -coverpkg=$(COVER_PKGS) ./...
	go tool cover -func=coverage.out

test-report:
	go test -race -json ./... > test-report.json || true

sonar-artifacts: coverage test-report
