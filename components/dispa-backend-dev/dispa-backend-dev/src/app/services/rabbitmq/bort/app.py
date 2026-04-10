"""Приложение FastStream для обработки сообщений на борту."""

from typing import TYPE_CHECKING, Any

from faststream import AckPolicy, FastStream
from faststream.rabbit import Channel, RabbitBroker, RabbitMessage, RabbitQueue

from app.core.config import settings
from app.core.redis_client import redis_client
from app.services.rabbitmq.config.logger import get_logger
from app.services.rabbitmq.config.retry_middleware import RetryExponentialBackoffMiddleware
from app.services.rabbitmq.main import publisher_manager
from app.services.rabbitmq.messages import MessageHandlerRouter, type_message_handlers
from app.services.rabbitmq.normilizer import normalize_message_payload

if TYPE_CHECKING:
    from faststream.rabbit.subscriber import RabbitSubscriber

logger = get_logger()

broker = RabbitBroker(settings.rabbit.url)
broker.add_middleware(RetryExponentialBackoffMiddleware)
app = FastStream(broker)


class VehicleBortManager:
    """Менеджер обработки сообщений на борту техники."""

    def __init__(self, broker: RabbitBroker) -> None:
        self.broker = broker
        self.vehicle_id = settings.vehicle_id
        self.queue = f"server.bort_{self.vehicle_id}.trip.dst"
        self._subscriber: RabbitSubscriber | None = None  # Сохраняем ссылку на подписчика
        self._is_subscribed = False  # Флаг, что подписка уже создана
        self.message_handler = MessageHandlerRouter(type_message_handlers)

    async def bort_handler(self) -> bool | None:
        """Создает подписку на сообщения от сервера."""
        if self._is_subscribed:
            logger.info(
                "Подписка уже создана для техники",
                vehicle_id=self.vehicle_id,
                queue_name=self.queue,
            )
            return True

        logger.info(
            "Создание подписчика для техники",
            vehicle_id=self.vehicle_id,
            queue_name=self.queue,
            broker_has_connection=hasattr(self.broker, "_connection") and self.broker._connection is not None,
            broker_subscribers_count=len(getattr(self.broker, "subscribers", [])),
        )

        subscriber = self.broker.subscriber(
            RabbitQueue(
                self.queue,
                auto_delete=False,
                durable=True,
            ),
            channel=Channel(prefetch_count=1),
            ack_policy=AckPolicy.NACK_ON_ERROR,
        )

        @subscriber
        async def handler(raw_msg: Any, rabbit_message: RabbitMessage) -> None:
            msg = normalize_message_payload(raw_msg)
            response = False
            if msg is None:
                logger.warning(
                    "Пропущено сообщение с неподдерживаемым payload",
                    queue_name=self.queue,
                    payload_type=type(raw_msg).__name__,
                )
                await rabbit_message.reject()
                return
            logger.info(
                "Получено сообщение на борту",
                vehicle_id=self.vehicle_id,
                message_data=msg.get("message_data"),
                message_id=msg["payload"].get("id"),
                queue_name=self.queue,
            )
            if msg.get("response") == "success":
                logger.info("Получено подтверждение доставки на борту", message_id=msg["payload"].get("id"))
                return
            try:
                response = await self.message_handler.dispatch(msg)
            except Exception as exc:
                logger.exception("Ошибка обработки сообщения", exc=exc)
                await rabbit_message.reject()
                return
            if publisher_manager is None:
                logger.error("Publisher manager is not initialized")
                return
            if response:
                await publisher_manager.success_publish(
                    {"response": "success", "id": msg["message_data"].get("id_message")},
                    int(self.vehicle_id),
                )

        self._subscriber = subscriber
        logger.info(
            "Подписчик создан и сохранен",
            vehicle_id=self.vehicle_id,
            subscriber_type=type(subscriber).__name__,
            has_start_method=hasattr(subscriber, "start"),
        )

        try:
            if hasattr(self.broker, "_connection") and self.broker._connection is not None:
                logger.info("Брокер уже имеет соединение, пытаемся запустить подписчика явно")
                if hasattr(self.broker, "subscribers") and self.broker.subscribers:
                    last_subscriber = self.broker.subscribers[-1]
                    logger.info(
                        "Найден последний подписчик брокера",
                        subscriber_type=type(last_subscriber).__name__,
                        total_subscribers=len(self.broker.subscribers),
                    )
                    if hasattr(last_subscriber, "start"):
                        await last_subscriber.start()
                        logger.info("Подписчик явно запущен", vehicle_id=self.vehicle_id, queue_name=self.queue)
                    else:
                        logger.warning(
                            "Подписчик не имеет метода start()",
                            vehicle_id=self.vehicle_id,
                            subscriber_type=type(last_subscriber).__name__,
                        )
                else:
                    logger.warning(
                        "Брокер не имеет подписчиков или атрибута subscribers",
                        vehicle_id=self.vehicle_id,
                        has_subscribers_attr=hasattr(self.broker, "subscribers"),
                        broker_attributes=dir(self.broker),
                    )
            else:
                logger.info(
                    "Брокер еще не имеет соединения, подписчик будет запущен при старте брокера",
                    vehicle_id=self.vehicle_id,
                    broker_connection_state=getattr(self.broker, "_connection", None),
                )
        except Exception as e:
            logger.warning(
                "Не удалось явно запустить подписчика",
                vehicle_id=self.vehicle_id,
                error=str(e),
                error_type=type(e).__name__,
            )

        self._is_subscribed = True

        return True


manager = VehicleBortManager(broker)


@app.after_startup
async def startup() -> None:
    """Запуск подписки на сообщения при старте приложения."""
    await redis_client.connect()
    logger.info(
        "FastStream приложение запущено, инициализируем подписчика",
        vehicle_id=manager.vehicle_id,
        queue_name=manager.queue,
    )
    try:
        result = await manager.bort_handler()
        logger.info(
            "Подписчик инициализирован",
            result=result,
            vehicle_id=manager.vehicle_id,
            queue_name=manager.queue,
        )
    except Exception as e:
        logger.error(
            "Ошибка при инициализации подписчика",
            vehicle_id=manager.vehicle_id,
            error=str(e),
            error_type=type(e).__name__,
        )
        raise


@app.on_shutdown
async def shutdown() -> None:
    """Отключение Redis при завершении FastStream приложения."""
    await redis_client.disconnect()
