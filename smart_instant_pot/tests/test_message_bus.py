# Smart Instant Pot Message Bus Tests
# Author: Tony DiCola
import time
import unittest

from smart_instant_pot.services.message_bus import SimpleMessageBus, RedisThreadedMessageBus


class TestSimpleMessageBus(unittest.TestCase):

    def test_subscribe_and_publish_one_subscriber(self):
        # Test basic subscribe and publish to a channel works.
        bus = SimpleMessageBus()
        callback_calls = []
        def callback(channel, message):
            callback_calls.append({'channel': channel, 'message': message})
        bus.subscribe('foo', callback)
        bus.publish('foo', 'bar')
        self.assertEqual(len(callback_calls), 1)
        self.assertDictEqual(callback_calls[0], {'channel': b'foo',
                                                 'message': b'bar'})

    def test_subscribe_and_publish_multi_subscriber(self):
        # Test multiple subscribers receive the same published message.
        bus = SimpleMessageBus()
        callback1_calls = []
        def callback1(channel, message):
            callback1_calls.append({'channel': channel, 'message': message})
        callback2_calls = []
        def callback2(channel, message):
            callback2_calls.append({'channel': channel, 'message': message})
        bus.subscribe('foo', callback1)
        bus.subscribe('foo', callback2)
        bus.publish('foo', 'bar')
        self.assertEqual(len(callback1_calls), 1)
        self.assertDictEqual(callback1_calls[0], {'channel': b'foo',
                                                  'message': b'bar'})
        self.assertEqual(len(callback2_calls), 1)
        self.assertDictEqual(callback2_calls[0], {'channel': b'foo',
                                                  'message': b'bar'})

    def test_subscribe_then_unsubscribe_and_publish(self):
        # Test unsubscribe removes a subscriber from future notifications.
        bus = SimpleMessageBus()
        callback_calls = []
        def callback(channel, message):
            callback_calls.append({'channel': channel, 'message': message})
        bus.subscribe('foo', callback)
        bus.publish('foo', 'bar')
        bus.unsubscribe('foo', callback)
        bus.publish('foo', 'baz')
        self.assertEqual(len(callback_calls), 1)
        self.assertDictEqual(callback_calls[0], {'channel': b'foo',
                                                 'message': b'bar'})

    def test_publish_no_subscribers_does_nothing(self):
        # Test publish does nothing when no subscribers are on the channel.
        bus = SimpleMessageBus()
        callback_calls = []
        def callback(channel, message):
            callback_calls.append({'channel': channel, 'message': message})
        bus.subscribe('foo', callback)
        bus.publish('bar', 'bar')
        self.assertEqual(len(callback_calls), 0)


#@unittest.skip("Redis message bus integration tests must be manually run with redis.")
class TestRedisThreadedMessageBus(unittest.TestCase):

    REDIS_HOST = 'redis'

    DELIVER_DELAY = 2.0  # Time to wait for messages to be delivered.
                         # Simple but not ideal (consider polling for expected
                         # state).

    def setUp(self):
        self._bus = RedisThreadedMessageBus(namespace='test',
                                            host=self.REDIS_HOST)

    def tearDown(self):
        self._bus.deinit()
        self._bus = None

    def test_subscribe_and_publish_one_subscriber(self):
        # Test basic subscribe and publish to a channel works.
        callback_calls = []
        def callback(channel, message):
            callback_calls.append({'channel': channel, 'message': message})
        self._bus.subscribe('foo', callback)
        self._bus.publish('foo', 'bar')
        time.sleep(self.DELIVER_DELAY)
        self.assertEqual(len(callback_calls), 1)
        self.assertDictEqual(callback_calls[0], {'channel': b'foo',
                                                 'message': b'bar'})

    def test_subscribe_and_publish_multi_subscriber(self):
        # Test multiple subscribers receive the same published message.
        callback1_calls = []
        def callback1(channel, message):
            callback1_calls.append({'channel': channel, 'message': message})
        callback2_calls = []
        def callback2(channel, message):
            callback2_calls.append({'channel': channel, 'message': message})
        self._bus.subscribe('foo', callback1)
        self._bus.subscribe('foo', callback2)
        self._bus.publish('foo', 'bar')
        time.sleep(self.DELIVER_DELAY)
        self.assertEqual(len(callback1_calls), 1)
        self.assertDictEqual(callback1_calls[0], {'channel': b'foo',
                                                  'message': b'bar'})
        self.assertEqual(len(callback2_calls), 1)
        self.assertDictEqual(callback2_calls[0], {'channel': b'foo',
                                                  'message': b'bar'})

    def test_subscribe_then_unsubscribe_and_publish(self):
        # Test unsubscribe removes a subscriber from future notifications.
        callback_calls = []
        def callback(channel, message):
            callback_calls.append({'channel': channel, 'message': message})
        self._bus.subscribe('foo', callback)
        self._bus.publish('foo', 'bar')
        self._bus.unsubscribe('foo', callback)
        self._bus.publish('foo', 'baz')
        time.sleep(self.DELIVER_DELAY)
        self.assertEqual(len(callback_calls), 1)
        self.assertDictEqual(callback_calls[0], {'channel': b'foo',
                                                 'message': b'bar'})

    def test_publish_no_subscribers_does_nothing(self):
        # Test publish does nothing when no subscribers are on the channel.
        callback_calls = []
        def callback(channel, message):
            callback_calls.append({'channel': channel, 'message': message})
        self._bus.subscribe('foo', callback)
        self._bus.publish('bar', 'bar')
        time.sleep(self.DELIVER_DELAY)
        self.assertEqual(len(callback_calls), 0)
