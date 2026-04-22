#!/usr/bin/env python3
"""Скрипт для эмуляции работы Trip Service через API.

Позволяет имитировать события State Machine и создание рейсов.
"""

import json
import sys
import time
from typing import Any

import requests
from loguru import logger

# Настройка логирования для скрипта
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <level>{message}</level>",
    level="INFO",
    colorize=True,
)

# Конфигурация
API_BASE_URL = "http://localhost:8000"
VEHICLE_ID = "BELAZ-001"


class TripSimulator:
    """Симулятор работы Trip Service."""

    def __init__(self, base_url: str = API_BASE_URL, vehicle_id: str = VEHICLE_ID):
        self.base_url = base_url
        self.vehicle_id = vehicle_id
        self.session = requests.Session()

    def _api_call(self, method: str, endpoint: str, **kwargs) -> dict[str, Any]:
        """Вызов API endpoint."""
        url = f"{self.base_url}{endpoint}"
        try:
            response = self.session.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error("API Error", error=str(e))
            if hasattr(e, "response") and e.response is not None:
                logger.error("API Response", response=e.response.text)
            raise

    def get_state(self) -> dict[str, Any]:
        """Получить текущее состояние State Machine."""
        return self._api_call("GET", "/api/state")

    def set_state(self, new_state: str, reason: str = "simulation", comment: str = "") -> dict[str, Any]:
        """Установить состояние State Machine."""
        data = {
            "new_state": new_state,
            "reason": reason,
            "comment": comment,
        }
        return self._api_call("POST", "/api/state/transition", json=data)

    def get_active_task(self) -> dict[str, Any] | None:
        """Получить активное задание."""
        result = self._api_call("GET", "/api/active/task")
        return result if result.get("task_id") else None

    def get_active_trip(self) -> dict[str, Any] | None:
        """Получить активный рейс."""
        result = self._api_call("GET", "/api/active/trip")
        return result if result.get("internal_trip_id") else None

    def get_trips(self) -> dict[str, Any]:
        """Получить список рейсов."""
        return self._api_call("GET", "/api/trips")

    def complete_active_trip(self, reason: str = "simulation") -> dict[str, Any]:
        """Завершить активный рейс."""
        data = {
            "reason": reason,
            "comment": "Завершено через симулятор",
        }
        return self._api_call("PUT", "/api/active/trip/complete", json=data)

    def print_status(self):
        """Вывести текущий статус системы."""
        logger.info("=" * 60)
        logger.info("CURRENT SYSTEM STATUS")
        logger.info("=" * 60)

        # State Machine
        try:
            state = self.get_state()
            # API возвращает упрощенный формат: {"state": "idle", ...}
            current_state = state.get("state", "unknown")
            logger.info("State Machine status", state=current_state)

            # Проверяем last_tag_id из упрощенного формата
            if state.get("last_tag_id"):
                logger.info("Last tag", point_id=state["last_tag_id"])
            else:
                logger.info("Current tag: no data")
        except Exception as e:
            logger.error("Failed to get State Machine", error=str(e))

        # Active Task
        try:
            active_task = self.get_active_task()
            if active_task:
                logger.info(
                    "Active task found",
                    task_id=active_task["task_id"],
                    route=f"{active_task['start_point_id']} → {active_task['stop_point_id']}",
                    status=active_task["status"],
                )
            else:
                logger.info("No active task")
        except Exception as e:
            logger.error("Failed to get active task", error=str(e))

        # Active Trip
        try:
            active_trip = self.get_active_trip()
            if active_trip:
                logger.info(
                    "Active trip found",
                    trip_id=active_trip["internal_trip_id"][:8],
                    trip_type=active_trip["trip_type"],
                    from_point=active_trip.get("from_point_id", "N/A"),
                    to_point=active_trip.get("to_point_id", "N/A"),
                )
            else:
                logger.info("No active trip")
        except Exception as e:
            logger.error("Failed to get active trip", error=str(e))

        # Trips history
        try:
            trips = self.get_trips()
            logger.info("Total trips", count=trips.get("total", 0))
        except Exception as e:
            logger.error("Failed to get trips history", error=str(e))

        logger.info("=" * 60)

    def simulate_trip_start(self):
        """Эмулировать начало рейса.

        Последовательность:
        1. Проверить наличие активного задания
        2. Установить current_tag на start_point задания (через Redis напрямую)
        3. Перевести State Machine в 'loading'
        4. Это создаст trip в PostgreSQL
        """
        logger.info("=" * 60)
        logger.info("TRIP START SIMULATION")
        logger.info("=" * 60)

        # Шаг 1: Проверяем активное задание
        logger.info("[1/4] Checking active task...")
        active_task = self.get_active_task()

        if not active_task:
            logger.error("No active task found! Create shift_task first.")
            logger.error("Use: curl -X POST http://localhost:8000/api/shift-tasks ...")
            return False

        logger.info(
            "Active task found",
            task_id=active_task["task_id"],
            route=f"{active_task['start_point_id']} → {active_task['stop_point_id']}",
        )

        # Шаг 2: Устанавливаем метку на start_point АВТОМАТИЧЕСКИ
        logger.info("[2/4] Setting tag on loading point...", point_id=active_task["start_point_id"])

        import subprocess

        tag_data = {
            "point_id": active_task["start_point_id"],
            "point_type": "loading_zone",
            "timestamp": time.time(),
        }
        tag_json = json.dumps(tag_data)

        try:
            result = subprocess.run(  # noqa: S603
                [  # noqa: S607
                    "docker",
                    "exec",
                    "dispatching-redis",
                    "redis-cli",
                    "SET",
                    f"trip-service:vehicle:{self.vehicle_id}:current_tag",
                    tag_json,
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                logger.info("Tag set successfully", point_id=active_task["start_point_id"])
            else:
                logger.warning("Failed to set tag", error=result.stderr, note="Trip will be created as 'unplanned'")
        except Exception as e:
            logger.warning("Failed to set tag", error=str(e), note="Trip will be created as 'unplanned'")

        # Шаг 3: Проверяем текущее состояние
        logger.info("[3/4] Checking current State Machine state...")
        state = self.get_state()
        current_state = state.get("state", "unknown")
        logger.info("Current state", state=current_state)

        # Шаг 4: Переводим в loading
        logger.info("[4/4] Transitioning to 'loading' state...")
        logger.info("This will create a trip in PostgreSQL!")

        try:
            result = self.set_state(
                new_state="loading",
                reason="simulation_trip_start",
                comment="Trip start simulation via script",
            )
            logger.info("Transition completed", message=result.get("message", "Transition executed"))
        except Exception as e:
            logger.error("State transition error", error=str(e))
            return False

        # Проверяем что рейс создался
        logger.info("[Check] Waiting for trip creation...")
        time.sleep(1)

        active_trip = self.get_active_trip()
        if active_trip:
            logger.info(
                "Trip created successfully!",
                trip_id=active_trip["internal_trip_id"],
                trip_type=active_trip["trip_type"],
                task_id=active_trip.get("task_id", "N/A"),
            )
        else:
            logger.warning("Trip not found in Redis, but may be created in PostgreSQL")

        logger.info("=" * 60)
        logger.info("TRIP START SIMULATION COMPLETED")
        logger.info("=" * 60)

        return True

    def simulate_trip_complete(self):
        """Эмулировать завершение рейса.

        Последовательность:
        1. Проверить наличие активного рейса
        2. Установить current_tag на stop_point задания
        3. Перевести State Machine в 'unloading'
        4. Это завершит trip и вычислит аналитику
        """
        logger.info("=" * 60)
        logger.info("TRIP END SIMULATION")
        logger.info("=" * 60)

        # Шаг 1: Проверяем активный рейс
        logger.info("[1/4] Checking active trip...")
        active_trip = self.get_active_trip()

        if not active_trip:
            logger.error("No active trip found! Create a trip first.")
            return False

        logger.info(
            "Active trip found",
            trip_id=active_trip["internal_trip_id"][:8],
            trip_type=active_trip["trip_type"],
        )

        # Шаг 2: Устанавливаем метку на stop_point АВТОМАТИЧЕСКИ
        logger.info("[2/4] Setting tag on unloading point...")
        active_task = self.get_active_task()

        if active_task:
            stop_point = active_task["stop_point_id"]
            logger.info(f"   Целевая точка: {stop_point}")

            import subprocess

            tag_data = {
                "point_id": stop_point,
                "point_type": "unloading_zone",
                "timestamp": time.time(),
            }
            tag_json = json.dumps(tag_data)

            try:
                result = subprocess.run(  # noqa: S603
                    [  # noqa: S607
                        "docker",
                        "exec",
                        "dispatching-redis",
                        "redis-cli",
                        "SET",
                        f"trip-service:vehicle:{self.vehicle_id}:current_tag",
                        tag_json,
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0:
                    logger.info(f"SUCCESS: Метка установлена: {stop_point}")
                else:
                    logger.info(f"WARNING:  Ошибка установки метки: {result.stderr}")
            except Exception as e:
                logger.info(f"WARNING:  Не удалось установить метку: {e}")
        else:
            logger.info("WARNING:  Нет активного задания, разгрузка будет без метки")

        # Шаг 3: Проверяем текущее состояние
        logger.info("\n[3/4] Проверка текущего состояния State Machine...")
        state = self.get_state()
        current_state = state.get("state", "unknown")
        logger.info(f"   Текущее состояние: {current_state}")

        # Шаг 4: Переводим в unloading
        logger.info("\n[4/4] Переход в состояние 'unloading'...")
        logger.info("   Это завершит trip и вычислит аналитику!")

        try:
            result = self.set_state(
                new_state="unloading",
                reason="simulation_trip_complete",
                comment="Эмуляция завершения рейса через скрипт",
            )
            logger.info(f"SUCCESS: {result.get('message', 'Переход выполнен')}")
        except Exception as e:
            logger.info(f"ERROR: Ошибка перехода состояния: {e}")
            return False

        # Проверяем что рейс завершился
        logger.info("\n[Проверка] Ожидание завершения рейса...")
        time.sleep(1)

        active_trip_after = self.get_active_trip()
        if not active_trip_after:
            logger.info("SUCCESS: Рейс завершен успешно!")
        else:
            logger.info("WARNING:  Рейс все еще активен")

        logger.info("\n" + "=" * 60)
        logger.info("SUCCESS: ЭМУЛЯЦИЯ ЗАВЕРШЕНИЯ РЕЙСА ЗАВЕРШЕНА")
        logger.info("=" * 60 + "\n")

        return True


def main():
    """Главная функция."""
    simulator = TripSimulator()

    while True:
        logger.info("\n" + "=" * 60)
        logger.info("SIMULATOR: TRIP SERVICE SIMULATOR")
        logger.info("=" * 60)
        logger.info("\n1. STATUS: Показать текущий статус")
        logger.info("2. START: Начать рейс (loading) ")
        logger.info("3. END: Завершить рейс (unloading) ")
        logger.info("4. STATE: Изменить состояние вручную")
        logger.info("5. TASK: Получить список рейсов")
        logger.info("0. 🚪 Выход")
        logger.info("=" * 60)

        choice = input("\nВыберите действие (0-5): ").strip()

        if choice == "0":
            logger.info("\nEXIT: Выход из симулятора")
            break

        elif choice == "1":
            simulator.print_status()

        elif choice == "2":
            simulator.simulate_trip_start()
            simulator.print_status()

        elif choice == "3":
            simulator.simulate_trip_complete()
            simulator.print_status()

        elif choice == "4":
            logger.info("\nДоступные состояния:")
            logger.info("  - idle")
            logger.info("  - moving_empty")
            logger.info("  - stopped_empty")
            logger.info("  - loading")
            logger.info("  - moving_loaded")
            logger.info("  - stopped_loaded")
            logger.info("  - unloading")

            new_state = input("\nВведите новое состояние: ").strip()
            comment = input("Комментарий (опционально): ").strip()

            try:
                result = simulator.set_state(new_state, comment=comment)
                logger.info(f"\nSUCCESS: Состояние изменено: {result['old_state']} → {result['new_state']}")
            except Exception as e:
                logger.info(f"\nERROR: Ошибка: {e}")

        elif choice == "5":
            try:
                trips = simulator.get_trips()
                logger.info(f"\nCOUNT: Всего рейсов: {trips.get('total', 0)}")
                logger.info("\nПоследние рейсы:")
                for trip in trips.get("items", [])[:5]:
                    from_p = trip.get("from_point_id", "N/A")
                    to_p = trip.get("to_point_id", "N/A")
                    logger.info(
                        f"Trip: {trip['internal_trip_id'][:8]} | {trip['trip_type']} | {from_p} -> {to_p}",
                    )
            except Exception as e:
                logger.info(f"ERROR: Ошибка: {e}")

        else:
            logger.info("ERROR: Неверный выбор")


if __name__ == "__main__":
    logger.info("""
╔══════════════════════════════════════════════════════════════════════════╗
║                     TRIP SERVICE SIMULATOR                                ║
║                                                                           ║
║  Эмулятор работы Trip Service для создания и завершения рейсов          ║
║  через API endpoints                                                      ║
╚══════════════════════════════════════════════════════════════════════════╝
    """)

    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n\nEXIT: Прервано пользователем")
    except Exception as e:
        logger.info(f"\nERROR: Критическая ошибка: {e}")
        import traceback

        traceback.print_exc()
