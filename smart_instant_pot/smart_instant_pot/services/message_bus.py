# Smart Instant Pot Message Bus
# This defines a simple redis-backed message bus for publish/subscribe pattern
# notifications.  This is used for communication across services through a
# common message bus broker.
# Author: Tony DiCola
import abc
import threading
import time

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
        two parameters, the channel name and the message data (both as byte
        strings).
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
                cb(to_bytes(channel), message)

    def subscribe(self, channel, callback):
        # Add this callback to the list of callbacks for this channel if it
        # isn't already there.
        self._bus.setdefault(channel, set()).add(callback)

    def unsubscribe(self, channel, callback):
        # Remove the specified callback if it's registered with the channel.
        if channel in self._bus:
            self._bus[channel].discard(callback)


class RedisThreadedMessageBus(MessageBus):
    """Redis-backed message bus implementation using a thread to process and
    deliver messages in the background.  Uses a redis server and its pubsub
    support to send and receive messages.  You must pass in any redis-py
    StrictRedis keyword arguments like host and port to initialize the instance.
    You can optionally specify a namespace that will be appended to channel
    names to help isolated them from other data in the redis server.
    """

    def __init__(self, namespace=None, **kwarg):
        self._namespace = namespace
        self._callbacks = {}
        self._callbacks_lock = threading.Lock()
        self._redis = redis.StrictRedis(**kwarg)
        # Setup pubsub connection and subscribe to all channels in the namespace
        # for this instance.  We do this because redis-py doesn't handle adding
        # new subscriptions well (its sockets are blocking and the threading
        # model has issues too), so we just subscribe to everything and filter
        # out channels we care about when messages are received.
        self._pubsub = self._redis.pubsub(ignore_subscribe_messages=True)
        sub_channel = self._channel('*', as_bytes=False)
        self._pubsub.psubscribe(**{sub_channel: self._callback})
        self._thread = self._pubsub.run_in_thread(sleep_time=0.001)

    def _callback(self, data):
        # Main callback that will be invoked by redis-py when a message is
        # received.  This grabs the channel and message, then looks for any
        # subscribed callback functions and calls them.  Note that this will
        # run in a background thread so it needs to be careful to syncronize
        # access to data structures like the callback dictionary.
        if data is not None and 'channel' in data and 'data' in data:
            channel = data['channel']
            message = data['data']
            with self._callbacks_lock:
                if channel in self._callbacks:
                    for cb in self._callbacks[channel]:
                        cb(channel, message)

    def _channel(self, channel, as_bytes=True):
        # Construct a channel name using any specified namespace.
        if self._namespace is not None:
            channel = build_id(self._namespace, channel)
        if as_bytes:
            return to_bytes(channel)
        return channel

    def deinit(self):
        """Unregister all callbacks and close connections with the redis server.
        This is useful when finished with the message bus and you want to
        ensure no future message callbacks are fired.
        """
        if self._thread is not None:
            self._thread.stop()
            self._thread = None
        with self._callbacks_lock:
            if self._callbacks is not None:
                self._callbacks = None

    def __del__(self):
        self.deinit()

    def publish(self, channel, message):
        channel = self._channel(channel)
        self._redis.publish(channel, message)

    def subscribe(self, channel, callback):
        # Add this callback to the list of callbacks for this channel if it
        # isn't already there.
        channel = self._channel(channel)
        with self._callbacks_lock:
            self._callbacks.setdefault(channel, set()).add(callback)

    def unsubscribe(self, channel, callback):
        # Remove the specified callback if it's registered with the channel.
        channel = self._channel(channel)
        with self._callbacks_lock:
            if channel in self._callbacks:
                self._callbacks[channel].discard(callback)
