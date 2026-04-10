FROM dockerhub.timeweb.cloud/rabbitmq:4.2-management-alpine

COPY config/enabled_plugins /etc/rabbitmq/enabled_plugins
COPY config/rabbitmq.server.conf /etc/rabbitmq/rabbitmq.conf
COPY config/definitions.json /etc/rabbitmq/definitions.json
