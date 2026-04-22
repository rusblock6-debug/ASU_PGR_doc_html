"""Исключения для обработки сообщений RabbitMQ."""


class MessageHandlerError(ValueError):
    """Базовая ошибка для обработки сообщений."""


class UnknownMessageTypeError(MessageHandlerError):
    """Сообщение содержит неизвестный `type_message`."""


class MessageHandlerNotFoundError(MessageHandlerError):
    """Для `type_message` не найден зарегистрированный обработчик."""
