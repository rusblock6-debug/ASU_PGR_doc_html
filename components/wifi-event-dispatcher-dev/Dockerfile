
FROM registry.dmi-msk.ru/base-images:golang-master AS builder

WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
RUN CGO_ENABLED=0 go build -o /bort ./cmd/bort && \
    CGO_ENABLED=0 go build -o /server ./cmd/server

FROM registry.dmi-msk.ru/base-images:alpine-master
COPY --from=builder /bort /bort
COPY --from=builder /server /server
