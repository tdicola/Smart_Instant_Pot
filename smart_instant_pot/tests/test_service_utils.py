# Smart Instant Pot Service Utilities Tests
# Author: Tony DiCola
import unittest

import smart_instant_pot.services.utils as service_utils


class TestBuildId(unittest.TestCase):

    def test_multiple_words_concatenated_with_colon(self):
        result = service_utils.build_id('foo', 'bar', 'baz')
        self.assertEqual('foo:bar:baz', result)

    def test_null(self):
        result = service_utils.build_id()
        self.assertEqual('', result)

    def test_single_word(self):
        result = service_utils.build_id('foo')
        self.assertEqual('foo', result)


class TestToBytes(unittest.TestCase):

    def test_string(self):
        self.assertEqual(service_utils.to_bytes('foo'), b'foo')

    def test_number(self):
        self.assertEqual(service_utils.to_bytes(123), b'123')

    def test_bytes(self):
        self.assertEqual(service_utils.to_bytes(b'bar'), b'bar')
