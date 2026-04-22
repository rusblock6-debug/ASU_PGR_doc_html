"""Утилита для формирования имён очередей бортов."""


def queue_name(bort_id: int, service_name: str) -> str:
    """Формирует имя AMQP-очереди для борта.

    Args:
        bort_id: идентификатор борта
        service_name: имя сервиса (graph, enterprise, auth, trip)

    Returns:
        Имя очереди в формате server.bort_{N}.cdc_{service}.src

    Examples:
        >>> queue_name(1, "graph")
        'server.bort_1.cdc_graph.src'
        >>> queue_name(42, "enterprise")
        'server.bort_42.cdc_enterprise.src'
    """
    return f"server.bort_{bort_id}.cdc_{service_name}.src"
