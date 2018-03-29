# Smart Instant Pot Settings Tests
# Author: Tony DiCola
import unittest

from smart_instant_pot.settings import DictSettingsStore, RedisSettingsStore, Settings


class TestValues(unittest.TestCase):
    # Tests of the various Settings class value types.  These check the types
    # persist their settings and work as expected.

    # Define a test settings class with some attributes that will be used by
    # the test cases.
    class TestSettings(Settings):

        raw_value = Settings.Value()

        raw_default = Settings.Value(default=b'foo')

        raw_name = Settings.Value(name='special_name')

        int_value = Settings.IntValue()

        float_value = Settings.FloatValue()

        str_value = Settings.StrValue()

        str_encoding = Settings.StrValue(encoding='utf16')

    def setUp(self):
        # By default use an in memory dictionary setting store.
        self.store = DictSettingsStore()

    def test_raw_value_set_and_get(self):
        # Basic test of setting and getting a raw byte string value setting.
        settings = self.TestSettings(self.store)
        settings.raw_value = 10
        self.assertEqual(settings.raw_value, b'10')

    def test_raw_value_delete_and_get(self):
        # Basic test of setting, deleting, and getting a raw byte string value
        # setting.
        settings = self.TestSettings(self.store)
        settings.raw_value = 10
        del settings.raw_value
        self.assertIsNone(settings.raw_value)

    def test_key_composed_of_setting_class_and_instance_names(self):
        # Test that a key's name is composed of its parent setting class
        # and instance names separated by colons.
        settings = self.TestSettings(self.store)
        settings.raw_value = 10
        self.assertIn('TestSettings:raw_value', self.store._settings)

    def test_override_name(self):
        # Test that a setting value instance with custom name works as expected
        # and is stored under the custom name.
        settings = self.TestSettings(self.store)
        settings.raw_name = 10
        self.assertEqual(settings.raw_name, b'10')
        self.assertNotIn('TestSettings:raw_name', self.store._settings)
        self.assertIn('TestSettings:special_name', self.store._settings)

    def test_default_value_set(self):
        # Test that a setting with a default value will have its value set on
        # creation.
        settings = self.TestSettings(self.store)
        self.assertEqual(settings.raw_default, b'foo')

    def test_default_value_doesnt_override_previous_value(self):
        # Test that a setting with a default value will not override a value
        # already set in the store.
        settings = self.TestSettings(self.store)
        settings.raw_default = b'bar'
        settings = self.TestSettings(self.store)
        self.assertEqual(settings.raw_default, b'bar')

    def test_int_set_and_get(self):
        # Basic test of setting and getting an integer value setting.
        settings = self.TestSettings(self.store)
        settings.int_value = 10
        self.assertEqual(settings.int_value, 10)

    def test_int_not_set_is_none(self):
        # Test an integer that has not been set will read a value of None.

        settings = self.TestSettings(self.store)
        self.assertIsNone(settings.int_value)

    def test_float_set_and_get(self):
        # Basic test of setting and getting a float value setting.
        settings = self.TestSettings(self.store)
        settings.float_value = 3.33
        self.assertEqual(settings.float_value, 3.33)

    def test_float_not_set_is_none(self):
        # Test a float that has not been set will read a value of None.

        settings = self.TestSettings(self.store)
        self.assertIsNone(settings.float_value)

    def test_str_set_and_get(self):
        # Basic test of setting and getting a string value setting.

        settings = self.TestSettings(self.store)
        settings.str_value = 'Hello world'
        self.assertEqual(settings.str_value, 'Hello world')

    def test_str_not_set_is_none(self):
        # Test a string that has not been set will read a value of None.
        settings = self.TestSettings(self.store)
        self.assertIsNone(settings.str_value)

    def test_str_encoding(self):
        # Test a string with a specific encoding is decoded correctly.
        settings = self.TestSettings(self.store)
        settings.str_encoding = 'Hello world'.encode('utf16')
        self.assertEqual(settings.str_encoding, 'Hello world')


@unittest.skip("Redis setting integration tests must be manually run with redis.")
class TestRedisSettings(unittest.TestCase):
    # Redis-backed setting store tests.  These verify the RedisSettingsStore
    # class and require a redis instance to be running at the specified host
    # and default port 6379.

    REDIS_HOST = '172.17.0.2'

    class TestSettings(Settings):

        raw_value = Settings.Value()

        raw_default = Settings.Value(default=b'foo')

    def setUp(self):
        # Initialize a connection to the redis server.  You'll need to set the
        # host value as appropriate depending on where the redis server and
        # tests are running.
        self.store = RedisSettingsStore(host=self.REDIS_HOST)

    def test_raw_value_set_and_get(self):
        # Basic test of setting and getting a raw byte string value setting
        # in redis.
        settings = self.TestSettings(self.store)
        settings.raw_value = 10
        self.assertEqual(settings.raw_value, b'10')

    def test_raw_value_delete_and_get(self):
        # Basic test of setting, deleting, and getting a raw byte string value
        # setting.
        settings = self.TestSettings(self.store)
        settings.raw_value = 10
        del settings.raw_value
        self.assertIsNone(settings.raw_value)

    def test_default_value_set(self):
        # Test that a setting with a default value will have its value set on
        # creation.  Be sure to delete the value and re-create the store to
        # make sure it's tested as the redis store will persist state across
        # test runs.
        settings = self.TestSettings(self.store)
        del settings.raw_default
        settings = self.TestSettings(self.store)
        self.assertEqual(settings.raw_default, b'foo')

    def test_default_value_doesnt_override_previous_value(self):
        # Test that a setting with a default value will not override a value
        # already set in the store.
        settings = self.TestSettings(self.store)
        settings.raw_default = b'bar'
        settings = self.TestSettings(self.store)
        self.assertEqual(settings.raw_default, b'bar')

    def test_namespace(self):
        # Test a namespace on the settings store isolates it from other settings.
        settings = self.TestSettings(self.store)
        settings.raw_value = b'bar'
        store2 = RedisSettingsStore(namespace='test', host=self.REDIS_HOST)
        settings = self.TestSettings(store2)
        self.assertIsNone(settings.raw_value)
