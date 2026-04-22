"""MQTT application helper that plugs FastAPI-style dependencies into handlers."""

import asyncio
import inspect
import json
import threading
from collections.abc import Awaitable, Callable
from contextlib import suppress
from typing import Any, get_type_hints
from uuid import uuid4

from loguru import logger
from paho.mqtt import client as mqtt_client
from pydantic import BaseModel, TypeAdapter

from src.core.config import get_settings
from src.core.database.postgres.session import reset_session_context, set_session_context

from .dependency_resolver import DependencyResolver
from .mqtt_router import MQTTRouter, Subscription

settings = get_settings()


class MQTTApp:
    """Wrapper around paho-mqtt client configured for our dependency system."""

    def __init__(self, *, client_prefix: str, client: mqtt_client.Client | None = None) -> None:
        self.client = client or self._build_client(client_prefix=client_prefix)
        self.router = MQTTRouter()
        self._registered: bool = False
        self._loop: asyncio.AbstractEventLoop | None = None
        self._loop_thread: threading.Thread | None = None
        self._loop_ready: threading.Event | None = None
        self._loop_lock = threading.Lock()

    def include_router(self, router: MQTTRouter) -> None:
        """Merge subscriptions from ``router`` into the application router."""
        self.router.include_router(router)

    def setup(self, *, start_loop: bool = True) -> None:
        """Bind callbacks/register subs and optionally start the MQTT network loop."""
        if self._registered:
            return

        self.client.on_connect = self._on_connect

        # В paho можно повесить callback на конкретный фильтр топика
        for sub in self.router.subscriptions:
            self.client.message_callback_add(sub.topic, self._wrap_handler(sub))

        # fallback если прилетит что-то, на что нет callback_add
        self.client.on_message = self._on_message_fallback

        self._registered = True

        if start_loop:
            self.run_forever()

    def run_forever(self) -> None:
        """Run the MQTT network loop until disconnect and shut everything down."""
        try:
            self.client.loop_forever(retry_first_connection=True)
        except KeyboardInterrupt:
            logger.info("MQTT loop interrupted, shutting down")
        finally:
            self.shutdown()

    def disconnect(self) -> None:
        """Request MQTT client disconnect (safe to call multiple times)."""
        with suppress(Exception):
            self.client.disconnect()

    def shutdown(self) -> None:
        """Disconnect client and stop background handler loop."""
        self.disconnect()
        self._stop_background_loop()

    def _stop_background_loop(self) -> None:
        loop = self._loop
        thread = self._loop_thread
        if not loop or not thread:
            return

        if loop.is_closed():
            self._loop = None
            self._loop_thread = None
            self._loop_ready = None
            return

        def _stop_loop() -> None:
            loop.stop()

        loop.call_soon_threadsafe(_stop_loop)
        thread.join(timeout=5)
        self._loop = None
        self._loop_thread = None
        self._loop_ready = None

    @classmethod
    def _build_client(cls, client_prefix: str) -> mqtt_client.Client:
        unique_suffix = uuid4().hex[:8]
        client_id = f"dump-service-{client_prefix}-{unique_suffix}"
        client = mqtt_client.Client(
            client_id=client_id,
            protocol=mqtt_client.MQTTv5,
        )
        logger.debug("Initialized MQTT client {id}", id=client_id)
        client.connect(
            host=settings.NANOMQ_HOST,
            port=settings.NANOMQ_PORT,
            keepalive=settings.NANOMQ_KEEPALIVE,
        )
        return client

    def _on_connect(
        self,
        client: mqtt_client.Client,
        _userdata: Any,
        _flags: dict[str, Any],
        reason_code: int,
        _properties: Any | None = None,
    ) -> None:
        if reason_code != 0:
            logger.error("MQTT connection failed with code {reason_code}", reason_code=reason_code)
            return

        # подписываемся на все фильтры из роутера
        subs = self.router.subscriptions
        logger.info("MQTT connected, subscribing to {count} topic(s)", count=len(subs))
        for sub in subs:
            client.subscribe(sub.topic, qos=sub.qos)
            logger.info("Subscribed: {topic} qos={qos}", topic=sub.topic, qos=sub.qos)

    def _wrap_handler(
        self,
        sub: Subscription,
    ) -> Callable[[mqtt_client.Client, Any, mqtt_client.MQTTMessage], None]:
        sig = inspect.signature(sub.handler)
        params = list(sig.parameters.values())

        # ожидаем (payload, topic, qos, msg)
        payload_param = params[0] if params else None
        hints = get_type_hints(sub.handler)
        payload_type = hints.get(payload_param.name) if payload_param else None

        # подготовим адаптер для pydantic/типов
        adapter = None
        if payload_type is not None and BaseModel is not None:
            adapter = TypeAdapter(payload_type)

        def cb(
            _client: mqtt_client.Client,
            _userdata: Any,
            msg: mqtt_client.MQTTMessage,
        ) -> None:
            raw: bytes = msg.payload or b""

            try:
                data = self.decode_json(raw)  # dict/list/...
            except Exception:
                # logger.debug(
                #     "Invalid JSON topic={topic} qos={qos} payload={p}",
                #     topic=msg.topic,
                #     qos=msg.qos,
                #     p=(raw[:200] if raw else b""),
                # )
                return

            try:
                payload = adapter.validate_python(data) if adapter else data
            except Exception:
                # pydantic ValidationError сюда тоже попадёт
                # logger.debug(
                #     "Payload validation failed topic={topic} err={err} data={data}",
                #     topic=msg.topic,
                #     err=str(e),
                #     data=(data if isinstance(data, (dict, list)) else str(data)),
                # )
                return

            handler_coro = self._handle_message(sub, payload, msg)
            self._run_async(handler_coro, msg.topic)

        return cb

    async def _handle_message(
        self,
        sub: Subscription,
        payload: Any,
        msg: mqtt_client.MQTTMessage,
    ) -> None:
        resolver = DependencyResolver()
        context = set_session_context(str(uuid4()))
        try:
            try:
                await resolver.call(
                    sub.handler,
                    (payload, msg.topic, msg.qos, msg),
                )
            except Exception:
                logger.exception("Error in handler topic={topic}", topic=msg.topic)
            finally:
                await resolver.aclose()
        finally:
            reset_session_context(context=context)

    def _run_async(self, awaitable: Awaitable[Any], topic: str) -> None:
        loop = self._ensure_loop()

        async def runner() -> None:
            try:
                await awaitable
            except Exception:
                logger.exception("Error in async handler topic={topic}", topic=topic)

        asyncio.run_coroutine_threadsafe(runner(), loop)

    def _ensure_loop(self) -> asyncio.AbstractEventLoop:
        if self._loop and self._loop_ready and self._loop_ready.is_set():
            return self._loop

        with self._loop_lock:
            if self._loop and self._loop_ready and self._loop_ready.is_set():
                return self._loop

            ready = threading.Event()
            loop = asyncio.new_event_loop()
            thread = threading.Thread(target=self._loop_worker, args=(loop, ready))
            thread.start()
            ready.wait()

            self._loop = loop
            self._loop_thread = thread
            self._loop_ready = ready
            return loop

    @staticmethod
    def _loop_worker(loop: asyncio.AbstractEventLoop, ready: threading.Event) -> None:
        asyncio.set_event_loop(loop)
        ready.set()
        loop.run_forever()

    @classmethod
    def _on_message_fallback(
        cls,
        _client: mqtt_client.Client,
        _userdata: Any,
        msg: mqtt_client.MQTTMessage,
    ) -> None:
        # если вдруг прилетело что-то "мимо"
        payload = msg.payload.decode(errors="ignore") if msg.payload else ""
        logger.warning("Unhandled message topic=%s qos=%s payload=%s", msg.topic, msg.qos, payload)

    @classmethod
    def decode_json(cls, payload: bytes) -> Any:
        """Decode MQTT payload into JSON-friendly Python structures."""
        # утилита на будущее
        # нужно будет try/except и накинуть ошибки приложения
        str_json = payload.decode("utf-8")
        str_json = str_json.replace(":<no value>", ":null")
        try:
            return json.loads(str_json)
        except Exception:
            logger.exception("Error decoding")
