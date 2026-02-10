"""Channel Filter module.

Filters Discord messages based on target channel configuration.
"""

import logging
from typing import Optional

from src.models import DiscordMessage

logger = logging.getLogger(__name__)


class ChannelFilter:
    """Filters messages based on whether their channel is in the target channel list.

    The filter checks incoming messages against a configured list of target channel
    names. Only messages from channels in the target list are passed through.
    If the target list is empty, a warning is logged and all messages are rejected.
    """

    def __init__(self, target_channels: list[str]) -> None:
        """Initialize the ChannelFilter.

        Args:
            target_channels: List of channel names to monitor. Messages from
                channels not in this list will be filtered out.
        """
        self.target_channels = target_channels

    def should_process(self, channel_name: str) -> bool:
        """Determine whether a channel should be processed.

        Checks if the given channel name exists in the target channel list.
        If the target list is empty, logs a warning and returns False.

        Args:
            channel_name: The name of the channel to check.

        Returns:
            True if the channel is in the target list, False otherwise.
        """
        if not self.target_channels:
            logger.warning(
                "Target channel list is empty. No messages will be processed."
            )
            return False

        return channel_name in self.target_channels

    def filter_message(self, message: DiscordMessage) -> Optional[DiscordMessage]:
        """Filter a DiscordMessage based on its channel.

        If the message's channel is in the target channel list, the message is
        returned. Otherwise, None is returned.

        Args:
            message: The DiscordMessage to filter.

        Returns:
            The original message if it passes the filter, or None if it is rejected.
        """
        if self.should_process(message.channel):
            return message
        return None
