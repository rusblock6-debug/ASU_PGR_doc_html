FROM upr-proxy.dmi-msk.ru/docker/golang:1.25-alpine AS builder
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -o /bort ./cmd/bort && \
    CGO_ENABLED=0 go build -o /server ./cmd/server

FROM alpine:3.21
COPY --from=builder /bort /bort
COPY --from=builder /server /server
