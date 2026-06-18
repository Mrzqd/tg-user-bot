from bot.handlers.listener import register_listener_handlers  # noqa: F401
from bot.handlers.commands import register_command_handlers  # noqa: F401
from bot.handlers.admin import register_admin_handlers  # noqa: F401
from bot.handlers.reactions import register_reaction_handlers  # noqa: F401

_registered = False


def register_all_handlers() -> None:
    global _registered
    if _registered:
        return
    register_listener_handlers()
    register_command_handlers()
    register_admin_handlers()
    register_reaction_handlers()
    _registered = True
