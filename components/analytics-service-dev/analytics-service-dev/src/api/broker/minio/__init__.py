from faststream.rabbit import RabbitRouter

from . import events

router = RabbitRouter()

router.include_routers(
    events.router,
)
