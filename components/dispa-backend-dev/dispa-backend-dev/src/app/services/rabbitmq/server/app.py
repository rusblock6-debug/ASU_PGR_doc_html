"""Приложение FastStream для обработки сообщений на сервере."""

import asyncio
import contextlib
import re
from typing import Any

import httpx
from faststream import AckPolicy, FastStream
from faststream.rabbit import Channel, RabbitBroker, RabbitMessage, RabbitQueue

from app.core.config import settings
from app.services.rabbitmq.config.logger import get_logger
from app.services.rabbitmq.config.retry_middleware import RetryExponentialBackoffMiddleware
from app.services.rabbitmq.main import publisher_manager
from app.services.rabbitmq.messages import MessageHandlerRouter, type_message_handlers
from app.services.rabbitmq.normilizer import normalize_message_payload

logger = get_logger()


broker = RabbitBroker(settings.rabbit.url)
broker.add_middleware(RetryExponentialBackoffMiddleware)
app = FastStream(broker)


class VehicleServerManager:
    """Менеджер подписок на сообщения от техники на сервере.

    Логика:
    - add_vehicle_handler вызывается только через add_with_sem (семафор vehicle_capacity)
    - каждая add_with_sem выполняется в своей корутине
    - входящие сообщения в handler ставятся в очередь: одновременно обрабатывается
      не более capacity сообщений (message_semaphore).
    """

    def __init__(self, broker: RabbitBroker) -> None:
        self.broker = broker
        self.vehicles: list[int] = []
        self.vehicle_capacity = 2
        self.worker_count = 10
        self.vehicle_semaphore = asyncio.Semaphore(self.vehicle_capacity)
        self.start_vehicles_handler = False
        self._add_handler_task: asyncio.Task[None] | None = None
        self._queue_name_pattern = re.compile(r"^bort_(\d+)\.server\.trip\.dst")
        self._subscribers: dict[int, Any] = {}  # Храним подписчиков по vehicle_id
        self.message_handler = MessageHandlerRouter(type_message_handlers)

    async def add_vehicle_handler(self, vehicle_id: int) -> bool | None:
        """Создает подписку на сообщения от единицы техники.

        Вызывается только через add_with_sem.
        """
        queue_name = f"bort_{vehicle_id}.server.trip.dst"

        logger.info(
            "Создание подписчика для техники",
            vehicle_id=vehicle_id,
            queue_name=queue_name,
            broker_has_connection=hasattr(self.broker, "_connection") and self.broker._connection is not None,
            broker_subscribers_count=len(getattr(self.broker, "subscribers", [])),
        )

        # Сохраняем ссылку на подписчика, чтобы можно было его явно запустить
        subscriber = self.broker.subscriber(
            RabbitQueue(
                queue_name,
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
                    vehicle_id=vehicle_id,
                    queue_name=queue_name,
                    payload_type=type(raw_msg).__name__,
                )
                await rabbit_message.reject()
                return

            logger.info("Получено сообщение на сервере", vehicle_id=vehicle_id, queue_name=queue_name, message=msg)
            if msg.get("response") == "success":
                logger.info("Получено подтверждение доставки на сервере", message_id=msg.get("id"))
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
                    vehicle_id,
                )

        # Сохраняем ссылку на подписчика
        self._subscribers[vehicle_id] = subscriber

        logger.info(
            "Подписчик создан для техники",
            vehicle_id=vehicle_id,
            queue_name=queue_name,
            subscriber_stored=vehicle_id in self._subscribers,
            total_subscribers_stored=len(self._subscribers),
        )

        # Пытаемся явно запустить подписчика, если брокер уже запущен
        try:
            # Проверяем, запущен ли брокер
            if hasattr(self.broker, "_connection") and self.broker._connection is not None:
                # Получаем последнего добавленного подписчика
                if hasattr(self.broker, "subscribers") and self.broker.subscribers:
                    last_subscriber = self.broker.subscribers[-1]
                    # Пытаемся запустить подписчика
                    if hasattr(last_subscriber, "start"):
                        await last_subscriber.start()
                        logger.info("Подписчик явно запущен", vehicle_id=vehicle_id, queue_name=queue_name)
                    else:
                        logger.warning(
                            "Подписчик не имеет метода start()",
                            vehicle_id=vehicle_id,
                            subscriber_type=type(last_subscriber).__name__,
                        )
                else:
                    logger.warning(
                        "Брокер не имеет подписчиков или атрибута subscribers",
                        vehicle_id=vehicle_id,
                        has_subscribers_attr=hasattr(self.broker, "subscribers"),
                    )
            else:
                logger.info(
                    "Брокер еще не имеет соединения, подписчик будет запущен при старте брокера",
                    vehicle_id=vehicle_id,
                )
        except Exception as e:
            logger.warning("Не удалось явно запустить подписчика", vehicle_id=vehicle_id, error=str(e))

        return True

    async def add_with_sem(self, vehicle_id: int) -> None:
        """Все вызовы add_vehicle_handler — через семафор, каждая в своей корутине."""
        async with self.vehicle_semaphore:
            result = await self.add_vehicle_handler(vehicle_id)
            if result:
                logger.info(
                    "Подписчик успешно создан для техники",
                    vehicle_id=vehicle_id,
                )
            else:
                logger.warning(
                    "Не удалось создать подписчика для техники",
                    vehicle_id=vehicle_id,
                )

    async def _get_queues(self) -> set[int]:
        """Получение vehicle_id из существующих очередей брокера.

        Из имени вида `server.bort_1.trip.src` извлекается `1`.
        """
        url = f"http://{settings.rabbit.host}:1{settings.rabbit.port}/api/queues/%2F"
        auth = (settings.rabbit.user, settings.rabbit.password)

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(url, auth=auth)
                r.raise_for_status()
                data = r.json()
                vehicle_ids: set[int] = set()
                for line in data:
                    queue_name = line.get("name")
                    if not isinstance(queue_name, str):
                        continue
                    match = self._queue_name_pattern.match(queue_name)
                    if match:
                        vehicle_ids.add(int(match.group(1)))
                return vehicle_ids
        except httpx.ConnectError as e:
            logger.warning(
                "Не удалось подключиться к RabbitMQ HTTP API",
                url=url,
                error=str(e),
                hint="Убедитесь, что RabbitMQ Management Plugin установлен и доступен на порту 15672",
            )
            return set()
        except httpx.HTTPStatusError as e:
            logger.warning(
                "Ошибка HTTP при запросе к RabbitMQ API",
                url=url,
                status_code=e.response.status_code,
                error=str(e),
            )
            return set()
        except Exception as e:
            logger.warning(
                "Неожиданная ошибка при получении очередей из RabbitMQ",
                url=url,
                error=str(e),
            )
            return set()

    async def _add_vehicle(self, vehicle_id: int) -> None:
        """Вызывается для добавления новой техники.

        Метод для использования в роуте.
        """
        if vehicle_id in self.vehicles:
            logger.info("Для данной техники уже существует подписка", vehicle_id=vehicle_id)
            return
        await self.add_with_sem(vehicle_id)
        self.vehicles.append(vehicle_id)
        logger.info("Техника добавлена в список", vehicle_id=vehicle_id, list=self.vehicles)
        return

    async def _handle_vehicles(self) -> None:
        """Метод инициализации обнаруженной техники."""
        discovered_vehicle_ids = await self._get_queues()
        set_vehicles = set(self.vehicles)
        difference_vehicles = discovered_vehicle_ids - set_vehicles
        if not difference_vehicles:
            logger.debug("Новой техники не обнаружено")
            return
        logger.info(
            "Обнаружена новая техника для подписки",
            new_vehicles=sorted(difference_vehicles),
            existing_vehicles=sorted(self.vehicles),
        )
        for vehicle_id in sorted(difference_vehicles):
            if vehicle_id not in self.vehicles:
                await self._add_vehicle(vehicle_id)
        return

    async def _add_handler_loop(self) -> None:
        """Фоновый цикл добавления новой техники."""
        while self.start_vehicles_handler:
            await self._handle_vehicles()
            await asyncio.sleep(settings.rabbit.handler_delay)

    def start_add_handler(self) -> None:
        """Старт хэндлера на добавление новой техники.

        Запускается как фоновая задача и не блокирует startup.
        """
        if self._add_handler_task is not None and not self._add_handler_task.done():
            return
        self.start_vehicles_handler = True
        self._add_handler_task = asyncio.create_task(
            self._add_handler_loop(),
            name="rabbitmq-server-add-handler",
        )

    async def stop_add_handler(self) -> None:
        """Остановка фонового хэндлера.

        Вызывается при shutdown брокера/приложения.
        """
        self.start_vehicles_handler = False
        if self._add_handler_task is None:
            return
        self._add_handler_task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await self._add_handler_task
        self._add_handler_task = None

    async def remove_vehicle(self, vehicle_id: int) -> bool:
        """Удаление техники вместе с очередью.

        Метод для вызова через роут.
        """
        if vehicle_id not in self.vehicles:
            return False

        async with self.vehicle_semaphore:
            queue_get_name = f"server.bort_{vehicle_id}.trip.dst"
            queue_send_name = f"server.bort_{vehicle_id}.trip.src"
            get_queue_drop = False
            send_queue_drop = False
            try:
                for sub in getattr(self.broker, "subscribers", []):
                    q = getattr(sub, "queue", None)

                    if get_queue_drop and send_queue_drop:
                        break

                    if q is not None and getattr(q, "name", None) == queue_get_name:
                        await sub.stop()
                        logger.info("Consumer остановлен", queue=queue_get_name)
                        get_queue_drop = True
                    elif q is not None and getattr(q, "name", None) == queue_send_name:
                        await sub.stop()
                        logger.info("Consumer остановлен", queue=queue_send_name)
                        send_queue_drop = True

                # Удаляем подписчика из словаря
                if vehicle_id in self._subscribers:
                    del self._subscribers[vehicle_id]

                conn = getattr(self.broker, "_connection", None)
                if conn is not None:
                    channel = await conn.channel()
                    try:
                        await channel.queue_delete(queue_get_name)
                        logger.info("Очередь удалена", queue=queue_get_name, vehicle_id=vehicle_id)
                        await channel.queue_delete(queue_send_name)
                        logger.info("Очередь удалена", queue=queue_send_name, vehicle_id=vehicle_id)
                    finally:
                        await channel.close()

            except Exception as e:
                logger.warning(
                    "Не удалось удалить очередь RabbitMQ",
                    vehicle_id=vehicle_id,
                    error=str(e),
                )
            self.vehicles.remove(vehicle_id)
            logger.info("Техника удалена", vehicle_id=vehicle_id)
            return True


manager = VehicleServerManager(broker)


@app.after_startup
async def startup() -> None:
    """Запуск фонового хэндлера при старте приложения."""
    manager.start_add_handler()


@app.on_shutdown
async def shutdown() -> None:
    """Остановка фонового хэндлера при завершении приложения."""
    await manager.stop_add_handler()
