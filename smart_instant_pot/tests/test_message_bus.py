# Smart Instant Pot Message Bus Tests
# Author: Tony DiCola
import unittest

from smart_instant_pot.services.message_bus import SimpleMessageBus


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
        self.assertDictEqual(callback_calls[0], {'channel': 'foo',
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
        self.assertDictEqual(callback1_calls[0], {'channel': 'foo',
                                                  'message': b'bar'})
        self.assertEqual(len(callback2_calls), 1)
        self.assertDictEqual(callback2_calls[0], {'channel': 'foo',
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
        self.assertDictEqual(callback_calls[0], {'channel': 'foo',
                                                 'message': b'bar'})

    def test_publish_no_subscribers_does_nothing(self):
        bus = SimpleMessageBus()
        callback_calls = []
        def callback(channel, message):
            callback_calls.append({'channel': channel, 'message': message})
        bus.subscribe('foo', callback)
        bus.publish('bar', 'bar')
        self.assertEqual(len(callback_calls), 0)
