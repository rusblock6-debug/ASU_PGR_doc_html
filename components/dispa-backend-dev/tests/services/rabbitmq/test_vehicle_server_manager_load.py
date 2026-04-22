"""Нагрузочные тесты для VehicleServerManager.

--load-duration задаёт только время отправки сообщений; после окончания отправки
тест ждёт обработки всех сообщений брокером. В отчёте: время отправки, время приёма (drain),
RPS отправки и реальный RPS приёма.

Запуск (из корня app/):
  pytest app/tests/services/rabbitmq/test_vehicle_server_manager_load.py -v -s
  pytest app/tests/services/rabbitmq/test_vehicle_server_manager_load.py -v -s --real-broker
  pytest app/tests/services/rabbitmq/test_vehicle_server_manager_load.py -v -s --vehicles 6 --load-duration 60

Тест с неравномерным накоплением в очередях (только --real-broker):
  pytest .../test_vehicle_server_manager_load.py::test_uneven_queues_drain_summary -v -s --real-broker
"""

import asyncio
import json
import random
import sys
import time
from collections import defaultdict
from typing import Any

import pytest
from aiormq.exceptions import AMQPConnectionError, ChannelInvalidStateError
from faststream.rabbit import Channel, RabbitBroker, RabbitQueue, TestRabbitBroker
from loguru import logger

from app.core.config import settings
from app.services.rabbitmq.server.app import VehicleServerManager

LOAD_DURATION_SEC = 300
MIN_RPS = 5
MAX_CONSECUTIVE_PER_VEHICLE = 10
DEFAULT_VEHICLE_COUNT = 4
DRAIN_TIMEOUT_SEC = 600
DRAIN_TIMEOUT_MAX_SEC = 60  # максимум ожидания drain, чтобы тест не висел
DRAIN_TIMEOUT_UNEVEN_MAX_SEC = 120  # для теста неравномерных очередей (больше сообщений)
UNEVEN_CONSUMER_WARMUP_SEC = 2.0  # время на старт всех потребителей перед замером drain
DRAIN_SETTLE_SEC = 2.0


class VehicleServerManagerWithStats(VehicleServerManager):
    """Тестовая обёртка под текущую реализацию (без буфера и воркеров).

    Считает принятые сообщения по vehicle_id и вызывает process(msg) прямо в handler.
    """

    def __init__(self, broker: RabbitBroker, vehicles: list[int] = None) -> None:
        if vehicles is None:
            vehicles = []
        super().__init__(broker, vehicles)
        self.received_by_vehicle: dict[int, int] = defaultdict(int)
        self.received_order: list[int] = []  # порядок прихода по vehicle_id

    async def add_vehicle_handler(self, vehicle_id: int) -> bool | None:
        queue_name = f"server.bort_{vehicle_id}.trip_service.dst"

        @self.broker.subscriber(
            RabbitQueue(queue_name, auto_delete=False, durable=True),
            channel=Channel(prefetch_count=1),
        )
        async def handler(msg: dict) -> None:
            logger.info("Получено сообщение", vehicle_id=vehicle_id)
            self.received_by_vehicle[vehicle_id] += 1
            self.received_order.append(vehicle_id)
            await self.process(msg)

        return True

    async def process(self, msg: dict) -> None:
        await super().process(msg)
        sys.stdout.flush()
        sys.stderr.flush()


class VehicleServerManagerWithOrderTracking(VehicleServerManagerWithStats):
    """Записывает порядок и время обработки сообщений для анализа неравномерной загрузки."""

    def __init__(self, broker: RabbitBroker, vehicles: list[int] = None) -> None:
        if vehicles is None:
            vehicles = []
        super().__init__(broker, vehicles)
        self.process_order: list[tuple[int, int, float]] = []  # (vehicle_id, vehicle_seq, timestamp)
        self.get_queue: list[int] = []

    async def process(self, msg: dict) -> None:
        vid = msg.get("vehicle_id")
        seq = msg.get("vehicle_seq", -1)
        self.process_order.append((vid, seq, time.monotonic()))
        await super().process(msg)


def _make_sample_message(vehicle_id: int, vehicle_seq: int) -> dict[str, Any]:
    """Минимальное валидное сообщение для handler (dict). vehicle_seq — порядковый номер по этой очереди."""
    return {"vehicle_id": vehicle_id, "vehicle_seq": vehicle_seq, "ts": time.time()}


def _choose_next_vehicle(
    vehicles: list[int],
    last_vehicle: int | None,
    consecutive_count: int,
    max_consecutive: int,
) -> int:
    """Выбор следующей техники: произвольный порядок, но не более max_consecutive подряд от одной."""
    others = [v for v in vehicles if v != last_vehicle]
    if consecutive_count >= max_consecutive and last_vehicle is not None and others:
        return random.choice(others)  # noqa: S311
    return random.choice(vehicles)  # noqa: S311


async def _run_publisher(
    broker: RabbitBroker,
    vehicles: list[int],
    rps_total: float,
    duration_sec: float,
    sent_counts: dict[int, int],
    max_consecutive: int,
    sent_order: list[int] | None = None,
    send_events: list[tuple[float, int]] | None = None,
) -> None:
    """Публикует сообщения в произвольном порядке, RPS = rps_total.

    Не более max_consecutive подряд от одной техники.
    sent_order: порядок отправки по vehicle_id.
    send_events: если передан, в него дописываются (time.monotonic(), vehicle_id) после каждой отправки.
    """
    await broker.connect()
    interval = 1.0 / rps_total if rps_total > 0 else 1.0
    deadline = time.monotonic() + duration_sec
    next_vehicle_seq: dict[int, int] = defaultdict(int)
    last_vehicle: int | None = None
    consecutive_count = 0
    send_vehicle_queue: list[int] = []

    while time.monotonic() < deadline:
        vid = _choose_next_vehicle(
            vehicles,
            last_vehicle,
            consecutive_count,
            max_consecutive,
        )
        if vid == last_vehicle:
            consecutive_count += 1
        else:
            consecutive_count = 1
            last_vehicle = vid

        vehicle_seq = next_vehicle_seq[vid]
        next_vehicle_seq[vid] = vehicle_seq + 1
        msg = _make_sample_message(vid, vehicle_seq)
        queue = RabbitQueue(f"server.bort_{vid}.trip_service.dst")
        send_vehicle_queue.append(vid)
        if sent_order is not None:
            sent_order.append(vid)
        await broker.publish(msg, queue)
        sent_counts[vid] = sent_counts.get(vid, 0) + 1
        if send_events is not None:
            send_events.append((time.monotonic(), vid))
        await asyncio.sleep(interval)
    logger.info("Очередь на отправку", queue=send_vehicle_queue)


def _print_stats(
    vehicle_count: int,
    send_duration_sec: float,
    drain_duration_sec: float,
    sent_counts: dict[int, int],
    received_total: int,
    received_by_vehicle: dict[int, int],
    broker_mode: str,
    send_order: list[int] | None = None,
    received_order: list[int] | None = None,
) -> None:
    total_sent = sum(sent_counts.values())
    sent_rps = total_sent / send_duration_sec if send_duration_sec > 0 else 0
    # RPS приёма имеет смысл только при достаточно длинном drain; иначе получается завышение (total/0.01)
    if drain_duration_sec >= 0.5 and received_total > 0:
        drain_rps_str = f"{received_total / drain_duration_sec:.2f}"
    elif drain_duration_sec >= 0.001:
        drain_rps_str = f"— (все за {drain_duration_sec:.2f} с, RPS не показан)"
    else:
        drain_rps_str = "— (все получены до окончания отправки)"
    loss = total_sent - received_total
    loss_pct = (100.0 * loss / total_sent) if total_sent else 0

    print("\n============================================================")
    print(f"НАГРУЗОЧНЫЙ ТЕСТ: {vehicle_count} vehicle(s), брокер: {broker_mode}")
    print("============================================================  ")
    print(f"  Время отправки:       {send_duration_sec:.2f} с")
    print(f"  Время приёма (drain):  {drain_duration_sec:.2f} с")
    print(f"  Отправлено всего:     {total_sent}")
    print(f"  Получено всего:       {received_total}")
    print(f"  RPS (отправка):       {sent_rps:.2f}")
    print(f"  RPS (приём, реальный): {drain_rps_str}")
    print(f"  Потери:               {loss} ({loss_pct:.1f}%)")
    rps_send_per_q = send_duration_sec > 0
    rps_drain_per_q = drain_duration_sec >= 0.001
    for vid in sorted(sent_counts.keys()):
        s = sent_counts[vid]
        r = received_by_vehicle.get(vid, 0)
        rps_s = f"{s / send_duration_sec:.2f}" if rps_send_per_q else "—"
        rps_r = f"{r / drain_duration_sec:.2f}" if rps_drain_per_q else "—"
        print(f"    vehicle {vid}: sent={s}, received={r}, RPS(отправка)={rps_s}, RPS(приём)={rps_r}")
    _ORDER_SAMPLE = 150
    if send_order:
        n = len(send_order)
        sample = send_order[:_ORDER_SAMPLE]
        print(f"  Порядок отправки по vehicle_id (первые {min(_ORDER_SAMPLE, n)}): {sample}")
        if n > _ORDER_SAMPLE:
            print(f"    ... всего {n}")
    if received_order:
        n = len(received_order)
        sample = received_order[:_ORDER_SAMPLE]
        print(f"  Порядок получения по vehicle_id (первые {min(_ORDER_SAMPLE, n)}): {sample}")
        if n > _ORDER_SAMPLE:
            print(f"    ... всего {n}")
    sys.stdout.flush()


def _queue_name(vehicle_id: int) -> str:
    return f"server.bort_{vehicle_id}.trip_service.dst"


async def _prefill_queues(
    broker_url: str,
    vehicle_counts: dict[int, int],
    make_message: Any,
    fill_events: list[tuple[float, int]] | None = None,
) -> tuple[int, list[int]]:
    """Предзаполняет очереди в RabbitMQ без запуска потребителей.

    vehicle_counts: {vehicle_id: количество сообщений}.
    fill_events: если передан, в него дописываются (time.monotonic(), vehicle_id) после каждой отправки.
    Возвращает (общее_число_отправленных, send_queue).
    """
    send_queue: list[int] = []
    try:
        from aio_pika import DeliveryMode, Message, connect_robust
    except ImportError as err:
        raise pytest.skip("aio_pika нужен для предзаполнения очередей (pip install aio_pika)") from err

    connection = await connect_robust(broker_url)
    total = 0
    try:
        channel = await connection.channel()
        for vehicle_id, count in vehicle_counts.items():
            if count <= 0:
                continue
            queue_name = _queue_name(vehicle_id)
            queue = await channel.declare_queue(queue_name, durable=True)
            await queue.purge()
            for seq in range(count):
                msg = make_message(vehicle_id, seq)
                body = json.dumps(msg).encode()
                await channel.default_exchange.publish(
                    Message(
                        body=body,
                        delivery_mode=DeliveryMode.PERSISTENT,
                        content_type="application/json",
                    ),
                    routing_key=queue_name,
                )
                total += 1
                send_queue.append(vehicle_id)
                if fill_events is not None:
                    fill_events.append((time.monotonic(), vehicle_id))
    finally:
        await connection.close()
    return total, send_queue


def _print_uneven_summary(
    vehicle_counts: dict[int, int],
    process_order: list[tuple[int, int, float]],
    received_by_vehicle: dict[int, int],
    # send_order: list[int],
    # duration_sec: float,
) -> None:
    """Сводка по обработке при неравномерной загрузке очередей."""
    total_expected = sum(vehicle_counts.values())
    total_received = sum(received_by_vehicle.values())
    t0 = process_order[0][2] if process_order else 0
    t_last = process_order[-1][2] if process_order else 0
    actual_duration = t_last - t0 if process_order else 0

    print("\n" + "=" * 60)
    print("СВОДКА: неравномерное накопление → обработка")
    print("=" * 60)
    print(f"  Ожидалось сообщений:   {total_expected}")
    print(f"  Получено:               {total_received}")
    print(f"  Время обработки:       {actual_duration:.2f} с")
    print(
        f"  RPS (фактический):      {total_received / actual_duration:.2f}" if actual_duration >= 0.01 else "  RPS: —",
    )
    print()
    print("  По очередям (vehicle_id):")
    for vid in sorted(set(vehicle_counts) | set(received_by_vehicle)):
        expected = vehicle_counts.get(vid, 0)
        received = received_by_vehicle.get(vid, 0)
        times = [t for v, s, t in process_order if v == vid]
        first_t = times[0] - t0 if times else 0
        last_t = times[-1] - t0 if times else 0
        dur = last_t - first_t if len(times) > 1 else 0
        rps = received / dur if dur >= 0.01 else (received if received else 0)
        print(
            f"    vehicle {vid}: ожидалось={expected}, получено={received}, "
            f"первый={first_t:.2f} с, последний={last_t:.2f} с, RPS={rps:.1f}",
        )
    print()
    # sample = 1000
    # order_short = [vid for vid, _, _ in process_order[:sample]]
    # print(f"Порядок отправки: (первые {min(sample, len(send_order))}): ", send_order[:sample])
    # print(f"  Порядок обработки (первые {min(sample, len(process_order))}): {order_short}")
    # if len(process_order) > sample:
    #     print(f"  ... всего {len(process_order)} сообщений")
    print("=" * 60)
    sys.stdout.flush()


def _plot_fill_drain(
    fill_events: list[tuple[float, int]],
    process_order: list[tuple[int, int, float]],
    t0: float,
    vehicles: list[int],
    out_path: str | None = None,
) -> None:
    """Строит график: по X -- время (с), по Y -- количество сообщений.

    Два подграфика: заполнение очередей (prefill) и разбор очередей (drain) по каждой очереди.
    """
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        logger.warning("matplotlib не установлен, график fill/drain не строится (pip install matplotlib)")
        return

    if not fill_events or not process_order:
        logger.warning("Недостаточно данных для графика fill/drain")
        return

    vehicles_sorted = sorted(vehicles)
    colors = plt.cm.tab10.colors
    vid_to_color = {vid: colors[i % len(colors)] for i, vid in enumerate(vehicles_sorted)}

    fig, (ax_fill, ax_drain) = plt.subplots(2, 1, figsize=(12, 8), sharex=False)
    fig.suptitle("Заполнение и разбор очередей по времени")

    # Заполнение: по каждой очереди кумулятивное количество во времени
    fill_sorted = sorted(fill_events, key=lambda x: x[0])
    for vid in vehicles_sorted:
        events_v = [(t, 1) for t, v in fill_sorted if v == vid]
        if not events_v:
            continue
        ts = [0.0] + [t - t0 for t, _ in events_v]
        cum = list(range(0, len(events_v) + 1))
        ax_fill.step(ts, cum, where="post", label=f"vehicle {vid}", color=vid_to_color[vid], alpha=0.9)
    ax_fill.set_ylabel("Количество сообщений (накоплено)")
    ax_fill.set_xlabel("Время (с)")
    ax_fill.set_title("Заполнение очередей (prefill)")
    ax_fill.legend(loc="upper left")
    ax_fill.grid(True, alpha=0.3)

    # Разбор: по каждой очереди кумулятивное количество во времени
    for vid in vehicles_sorted:
        events_v = [(t, s) for v, s, t in process_order if v == vid]
        if not events_v:
            continue
        events_v.sort(key=lambda x: x[0])
        ts = [t - t0 for t, _ in events_v]
        cum = list(range(1, len(events_v) + 1))
        ax_drain.step(ts, cum, where="post", label=f"vehicle {vid}", color=vid_to_color[vid], alpha=0.9)
    ax_drain.set_ylabel("Количество сообщений (обработано)")
    ax_drain.set_xlabel("Время (с)")
    ax_drain.set_title("Разбор очередей (drain)")
    ax_drain.legend(loc="upper left")
    ax_drain.grid(True, alpha=0.3)

    plt.tight_layout()
    if out_path:
        plt.savefig(out_path, dpi=150, bbox_inches="tight")
        logger.info("График сохранён: {}", out_path)
    else:
        plt.savefig("fill_drain_queues.png", dpi=150, bbox_inches="tight")
        logger.info("График сохранён: fill_drain_queues.png")
    plt.close(fig)
    sys.stdout.flush()


@pytest.mark.asyncio
async def test_vehicle_server_manager_load(request: pytest.FixtureRequest) -> None:
    """Нагрузка: сообщения на N vehicles в произвольном порядке (не более 10 подряд от одной).

    RPS не менее 5.
    --load-duration: длительность отправки в секундах (по умолчанию из LOAD_DURATION_SEC).
    --vehicles N: количество техники (по умолчанию 4).
    --real-broker: использовать реальный RabbitMQ (иначе in-memory).
    """
    duration_sec = request.config.getoption("--load-duration", default=LOAD_DURATION_SEC) or LOAD_DURATION_SEC
    vehicle_count = request.config.getoption("--vehicles", default=DEFAULT_VEHICLE_COUNT) or DEFAULT_VEHICLE_COUNT
    use_real_broker = request.config.getoption("--real-broker", default=False)

    vehicles = list(range(1, vehicle_count + 1))
    rps_total = max(MIN_RPS, 1.0)
    sent_counts: dict[int, int] = defaultdict(int)
    broker_mode = "real (RabbitMQ)" if use_real_broker else "in-memory"

    if use_real_broker:
        broker_url = getattr(settings.rabbit, "url", None) or "amqp://guest:guest@localhost:5672/"
        broker = RabbitBroker(broker_url)
        try:
            await broker.connect()
        except (AMQPConnectionError, ChannelInvalidStateError) as e:
            pytest.skip(
                f"Реальный RabbitMQ недоступен ({broker_url}): {e}. "
                "Запустите брокер или используйте тест без --real-broker (in-memory).",
            )
        await asyncio.sleep(0.5)
        publish_broker = broker
    else:
        broker = RabbitBroker()
        publish_broker = None
    manager = VehicleServerManagerWithOrderTracking(broker, vehicles=[])
    for vid in vehicles:
        await manager._add_vehicle(vid)
    consumer_task = asyncio.create_task(broker.start())

    sent_order: list[int] = []
    send_events: list[tuple[float, int]] = []
    t0_ref: list[float] = [0.0]

    async def _run_test(br: RabbitBroker) -> None:
        time_send_start = time.monotonic()
        print("TIME_SEND_START: ", time_send_start)
        t0_ref[0] = time_send_start
        await _run_publisher(
            br,
            vehicles,
            rps_total,
            duration_sec,
            sent_counts,
            MAX_CONSECUTIVE_PER_VEHICLE,
            sent_order=sent_order,
            send_events=send_events,
        )
        total_sent_so_far = sum(sent_counts.values())
        print("TOTAL_SENT_SO_FAR", total_sent_so_far)
        send_duration_sec = time.monotonic() - time_send_start
        print("SEND_DURATION_SEC", send_duration_sec)

        drain_timeout_sec = min(DRAIN_TIMEOUT_MAX_SEC, max(10, duration_sec * 5))
        print("DRAIN_TIMEOUT_SEC", drain_timeout_sec)
        drain_deadline = time.monotonic() + drain_timeout_sec
        print("DRAIN_DEADLINE", drain_deadline)
        while time.monotonic() < drain_deadline:
            received_total = sum(manager.received_by_vehicle.values())
            print("RECEIVED_TOTAL", received_total)
            if received_total >= total_sent_so_far:
                break
            await asyncio.sleep(0.01)
        time_drain_end = time.monotonic()
        print("TIME_DRAIN_END", time_drain_end)
        await asyncio.sleep(DRAIN_SETTLE_SEC)

        time_send_end = time_send_start + send_duration_sec
        print("TIME_SEND_END", time_send_end)
        drain_duration_sec = max(0.01, time_drain_end - time_send_end)
        print("DRAIN_DURATION_SEC", drain_duration_sec)
        received_total = sum(manager.received_by_vehicle.values())
        print("RECEIVED_TOTAL", received_total)
        received_by_vehicle = dict(manager.received_by_vehicle)
        print("RECEIVED_BY_VEHICLE", received_by_vehicle)
        total_sent = sum(sent_counts.values())
        print("TOTAL_SENT", total_sent)
        received_order = list(manager.received_order)
        print("RECEIVED_ORDER", received_order)

        _print_stats(
            vehicle_count,
            send_duration_sec,
            drain_duration_sec,
            sent_counts,
            received_total,
            received_by_vehicle,
            broker_mode,
            send_order=sent_order,
            received_order=received_order,
        )
        _plot_fill_drain(send_events, getattr(manager, "process_order", []), t0_ref[0], vehicles)
        assert received_total >= total_sent * 0.99, f"Потери: получено {received_total}, отправлено {total_sent}"

    try:
        if use_real_broker:
            await _run_test(publish_broker)
        else:
            manager.vehicles = vehicles
            await manager._handle_vehicles()
            await asyncio.sleep(0.2)
            async with TestRabbitBroker(broker) as br:
                await _run_test(br)
    finally:
        logger.info("Очередь получения", queue=getattr(manager, "get_queue", []))
        if use_real_broker:
            try:
                await broker.stop()
            except Exception:  # noqa: S110
                pass
            try:
                await asyncio.wait_for(consumer_task, timeout=5.0)
            except (asyncio.CancelledError, TimeoutError, Exception):  # noqa: S110
                pass
            if not consumer_task.done():
                consumer_task.cancel()
                try:
                    await consumer_task
                except (asyncio.CancelledError, Exception):  # noqa: S110
                    pass


@pytest.mark.asyncio
async def test_uneven_queues_drain_summary(request: pytest.FixtureRequest) -> None:
    """Неравномерное накопление в очередях.

    Предзаполняем очереди (например 1->100, 2->0, 3->300),
    включаем приём, анализируем порядок обработки и выводим сводку.
    Только с реальным RabbitMQ (--real-broker).
    """
    use_real_broker = request.config.getoption("--real-broker", default=False)
    use_vehicles = request.config.getoption("--vehicles", default=True)
    if not use_real_broker:
        pytest.skip("Тест неравномерных очередей требует --real-broker (реальный RabbitMQ)")

    broker_url = getattr(settings.rabbit, "url", None) or "amqp://guest:guest@localhost:5672/"
    vehicle_counts = {}
    vehicles = []
    for _ in range(1, use_vehicles + 1):
        vehicle_counts[_] = random.randint(100, 1000)  # noqa: S311
        vehicles.append(_)
    if not vehicles:
        vehicles = list(vehicle_counts.keys())
    total_expected = sum(vehicle_counts.values())

    fill_events: list[tuple[float, int]] = []
    t0 = time.monotonic()
    try:
        total_send, send_queue = await _prefill_queues(
            broker_url,
            vehicle_counts,
            _make_sample_message,
            fill_events=fill_events,
        )
        logger.info("Очереди заполнены:", vehicle_counts=vehicle_counts, total_send=total_send)
        await asyncio.sleep(5)
    except Exception as e:
        pytest.skip(f"Не удалось предзаполнить очереди: {e}")

    broker = RabbitBroker(broker_url)
    manager = VehicleServerManagerWithOrderTracking(broker, vehicles=vehicles)
    try:
        await broker.connect()
    except (AMQPConnectionError, ChannelInvalidStateError) as e:
        pytest.skip(f"Реальный RabbitMQ недоступен ({broker_url}): {e}")

    time_start = time.monotonic()
    await manager._handle_vehicles()
    process_time = time.monotonic() - time_start
    print("Время выполнения handle_vehicles: ", process_time)
    consumer_task = asyncio.create_task(broker.start())
    await asyncio.sleep(
        UNEVEN_CONSUMER_WARMUP_SEC * use_vehicles,
    )  # Если доставляются не все сообщения поиграться со значением

    _print_uneven_summary(
        vehicle_counts,
        manager.process_order,
        dict(manager.received_by_vehicle),
    )
    _plot_fill_drain(fill_events, manager.process_order, t0, vehicles)

    consumer_task.cancel()
    try:
        await asyncio.wait_for(consumer_task, timeout=5.0)
    except (asyncio.CancelledError, TimeoutError, Exception):  # noqa: S110
        pass
    try:
        await broker.stop()
    except Exception:  # noqa: S110
        pass

    received_total = sum(manager.received_by_vehicle.values())
    if received_total < total_expected * 0.99 and consumer_task.done() and not consumer_task.cancelled():
        exc = consumer_task.exception()
        if exc is not None:
            logger.error("Потребитель упал с исключением: {}", exc)
    assert received_total >= total_expected * 0.99, (
        f"Потери: получено {received_total}, ожидалось {total_expected}. "
        "При раннем завершении consumer проверьте логи (исключение потребителя)."
    )
