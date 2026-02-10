"""Console Interceptor module.

Intercepts Playwright page console events and parses JSON message data.
"""

from typing import Callable, Optional

from src.models import DiscordMessage


class ConsoleInterceptor:
    """Intercepts Playwright page console events and processes Discord messages.

    Listens for console.log events from the injected MutationObserver JavaScript,
    parses JSON message data, and forwards valid DiscordMessage objects to a callback.
    """

    def __init__(self, on_message: Callable[[DiscordMessage], None]):
        """Initialize the ConsoleInterceptor.

        Args:
            on_message: Callback function invoked with a DiscordMessage
                        whenever a valid message is parsed from a console event.
        """
        self.on_message = on_message

    def handle_console(self, msg) -> None:
        """Handle a Playwright ConsoleMessage event.

        Attempts to parse the console message text as JSON. If it represents
        a valid DiscordMessage, the on_message callback is invoked and a
        formatted summary is printed to the terminal.

        Non-message JSON or invalid formats are silently ignored.

        Args:
            msg: A Playwright ConsoleMessage object (has a .text property).
        """
        text = msg.text
        message = self.parse_message(text)
        if message is not None:
            # Print formatted output to terminal
            print(f"[{message.channel}] {message.author} ({message.timestamp}): {message.content}")
            self.on_message(message)

    @staticmethod
    def parse_message(json_str: str) -> Optional[DiscordMessage]:
        """Parse a JSON string into a DiscordMessage.

        Delegates to DiscordMessage.from_json() for actual parsing and validation.

        Args:
            json_str: A JSON string to parse.

        Returns:
            A DiscordMessage instance if the JSON is valid, or None if the input
            is not a valid Discord message format.
        """
        return DiscordMessage.from_json(json_str)

    @staticmethod
    def serialize_message(message: DiscordMessage) -> str:
        """Serialize a DiscordMessage to a JSON string.

        Delegates to DiscordMessage.to_json() for actual serialization.

        Args:
            message: The DiscordMessage to serialize.

        Returns:
            A JSON string representation of the message.
        """
        return message.to_json()
