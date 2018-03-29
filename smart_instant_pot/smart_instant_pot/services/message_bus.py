# Smart Instant Pot Message Bus
# This defines a simple redis-backed message bus for publish/subscribe pattern
# notifications.  This is used for communication across services through a
# common message bus broker.
# Author: Tony DiCola
import abc

import redis

from smart_instant_pot.services.utils import build_id, to_bytes


class MessageBus(abc.ABC):
    """Generic interface for a message bus.  This allows publishing and
    subscribing to channels, where each channel is identified by a string
    name and messages are generic byte strings.
    """

    @abc.abstractmethod
    def publish(self, channel, message):
        """Publish a message to anyone subscribed to the specified channel.
        """
        pass

    @abc.abstractmethod
    def subscribe(self, channel, callback):
        """Subscribe for notification of new messages on the specified
        channel.  Provide a callback function which will be invoked with
        two parameters, the channel name (as a string) and the message data
        (as a byte string).
        """
        pass

    @abc.abstractmethod
    def unsubscribe(self, channel, callback):
        """Unsubscribe a callback function from being invoked on new messages
        to the specified channel.
        """
        pass


class SimpleMessageBus(MessageBus):
    """Simple message bus interface implementation that operates only within
    a single Python process.  Useful for testing components without a proper
    message bus running, or for very simple decoupling of components in the
    same codebase & process.
    """

    def __init__(self):
        # Store a dict with channel name as key and set of subscribed callbacks
        # as the value.  When messages are published they can be sent to all
        # the registered callbacks.
        self._bus = {}

    def publish(self, channel, message):
        # Enumerate all the callbacks for the specified channel and invoke them.
        message = to_bytes(message)
        if channel in self._bus:
            for cb in self._bus[channel]:
                cb(channel, message)

    def subscribe(self, channel, callback):
        # Add this callback to the list of callbacks for this channel if it
        # isn't already there.
        self._bus.setdefault(channel, set()).add(callback)

    def unsubscribe(self, channel, callback):
        # Remove the specified callback if it's registered with the channel.
        if channel in self._bus:
            self._bus[channel].discard(callback)
