"""Фикстуры и опции для тестов RabbitMQ."""

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--load-duration",
        type=float,
        default=None,
        help="Длительность нагрузочного теста в секундах (по умолчанию 300).",
    )
    parser.addoption(
        "--vehicles",
        type=int,
        default=1,
        help="Количество единиц техники (очередей) для нагрузочного теста (по умолчанию 4).",
    )
    parser.addoption(
        "--real-broker",
        action="store_true",
        default=False,
        help="Использовать реальный RabbitMQ вместо in-memory (нужен запущенный брокер, URL из настроек).",
    )
