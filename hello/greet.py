"""Pure greeting function for the hello CLI."""


def greet(name: str = "world", shout: bool = False) -> str:
    """Return ``Hello, <name>!``; uppercase it when ``shout`` is true.

    An empty or whitespace-only name falls back to ``world``.
    """
    name = name.strip() or "world"
    message = f"Hello, {name}!"
    return message.upper() if shout else message
