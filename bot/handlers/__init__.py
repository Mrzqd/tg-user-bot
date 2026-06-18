from bot.handlers.listener import register_listener_handlers  # noqa: F401
from bot.handlers.commands import register_command_handlers  # noqa: F401
from bot.handlers.admin import register_admin_handlers  # noqa: F401


def register_all_handlers() -> None:
    register_listener_handlers()
    register_command_handlers()
    register_admin_handlers()
