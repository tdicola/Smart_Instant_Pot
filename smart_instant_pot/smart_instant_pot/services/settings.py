# Smart Instant Pot Settings
# This defines a simple redis-backed global settings & configuration store
# for the Smart Insant Pot project services.  This is used for things like
# service discovery/registry and general service configuration.
# Author: Tony DiCola
import abc
import configparser

import redis

from smart_instant_pot.services.utils import build_id, to_bytes


class SettingsStore(abc.ABC):
    """Generic interface for a settings store that will store settings as
    key, value pairs.  Each key is a string and each value is a raw byte string.
    Provides a simpler interface for getting and setting values based on their
    key.  Settings instances are written to talk to this generic interface so
    they're not couple to any specific concrete backing store type (like redis,
    a simple in-memory dictionary, etc).
    """

    @abc.abstractmethod
    def set(self, key, val):
        """Set a key to the provided value.  Key must be a string and val can
        be any Python value that can be serialized to a byte string.
        """
        pass

    @abc.abstractmethod
    def set_default(self, key, val):
        """Set a key to the provided default value if it isn't already set."""
        pass

    @abc.abstractmethod
    def get(self, key):
        """Get the value of the specified key.  Key must be a string and the
        returned value is expected to be a byte string.  If the specified key is
        not in the store then None should be returned.
        """
        pass

    @abc.abstractmethod
    def delete(self, key):
        """Delete any value associated with the specified string key."""
        pass


class DictSettingsStore(SettingsStore):
    """Settings store that persists settings in memory with a simple Python
    dictionary.  Will never persist or save settings between program execution.
    """

    def __init__(self):
        self._settings = {}

    def set(self, key, val):
        self._settings[key] = to_bytes(val)

    def set_default(self, key, val):
        self._settings.setdefault(key, to_bytes(val))

    def get(self, key):
        return self._settings.get(key, None)

    def delete(self, key):
        try:
            del self._settings[key]
        except KeyError:
            # Ignore missing key error--the value wasn't set.
            pass


class ConfigSettingsStore(SettingsStore):
    """Settings store that reads and writes settings values to a
    configparser-based INI format file.
    """

    def __init__(self, config_file, namespace=None):
        self._config_file = config_file
        self._config = configparser.ConfigParser()
        self._config.read_file(self._config_file)
        self._namespace = namespace

    def _config_components(self, key):
        # Return the configparser parent section and child option name for the
        # specified setting key.  Will ensure the parent section exists and
        # create it if necessary.  A 2-tuple of the configparser section object
        # and child option name (as a string) are returned.
        # First break the key into its component parts, the setting class name
        # and the setting name.  We use these parts to identify the section
        # and option inside the config file where this value is stored.
        section, option = key.split(':')
        if self._namespace is not None:
            # Put the namespace in front of the section name (separated by a
            # configparser safe period delimeter) if it was set.
            section = '{0}.{1}'.format(self._namespace, section)
        # Ensure the section exists in the config file.
        if not self._config.has_section(section):
            self._config.add_section(section)
        return self._config[section], option

    def _to_str(self, val):
        # Ensure the provided value is a UTF8 string representation that can
        # be stored in the config file.  Will convert byte and bytes objects to
        # UTF8 strings.
        if isinstance(val, str):
            return val
        if isinstance(val, (bytes, bytearray)):
            return val.decode('utf8')
        else:
            return str(val)

    def set(self, key, val):
        section, option = self._config_components(key)
        section[option] = self._to_str(val)

    def set_default(self, key, val):
        section, option = self._config_components(key)
        section.setdefault(option, self._to_str(val))

    def get(self, key):
        section, option = self._config_components(key)
        val = section.get(option, None)
        if val is not None:
            val = to_bytes(val)
        return val

    def delete(self, key):
        section, option = self._config_components(key)
        try:
            del section[option]
        except KeyError:
            # Ignore missing key error--the value wasn't set.
            pass

    def write(self):
        """Write the current settings back to the config file."""
        # Seek back to start of the file, write current settings, then
        # truncate any remaining old data from the file.
        self._config_file.seek(0)
        self._config.write(self._config_file)
        self._config_file.truncate()


class RedisSettingsStore(SettingsStore):
    """Settings store that persists settings in a redis server.  Depending on
    how redis is configued this may or may not persist settings after the
    program finishes. On creation specify any redis-py StrictRedis keyword
    arguments like host, port, etc. to access the redis server.  Specify an
    optional namespace string value to use in front of setting keys to isolate
    them from other data on the redis server.
    """

    def __init__(self, namespace=None, **kwarg):
        self._namespace = namespace
        self._redis = redis.StrictRedis(**kwarg)

    def _key(self, key):
        # Append an optional namespace to a key so that it's isolated from
        # other data in redis.
        if self._namespace is not None:
            return build_id(self._namespace, key)
        return key

    def set(self, key, val):
        self._redis.set(self._key(key), val)

    def set_default(self, key, val):
        self._redis.set(self._key(key), val, nx=True)

    def get(self, key):
        return self._redis.get(self._key(key))

    def delete(self, key):
        self._redis.delete(self._key(key))


class Settings:
    """Base class for a service's settings.  Inherit from this class and add
    class attributes of type Value, IntValue, FloatValue, and StrValue to
    define the attributes that make up the settings.  When an instance of this
    class is created it must be provided with a backing store which will be
    used to read and write attribute values.
    """

    class Value:
        """General setting value descriptor.  Each instance of this on a
        Settings class defines a setting value that's stored as a simple byte
        string with no validation or modification.  Can specify an optional
        default value which will be set if the setting has no previously set
        value in the backing store.  The name of this setting will be set to
        the instance name, but can be overridden with the name keyword.
        """

        def __init__(self, default=None, name=None):
            self.default = default
            self._value_name = name

        def _key(self, obj):
            # Generate a key to identify this setting in the setting store.
            # This is composed of the parent Settings class name and this
            # value's name (either explicitly set or implicitly set to the instance
            # name).
            return build_id(obj._settings_name, self._value_name)

        def __set_name__(self, obj, attr_name):
            # Function called by Python (3.6+) or the base Settings class (fallback
            # for earlier Python versions) to tell this descriptor its instance
            # name.  The instance name is used to form the key name if an explicit
            # name wasn't provided when the attribute was created.
            if self._value_name is None:
                self._value_name = attr_name

        def __get__(self, obj, type=None):
            # Descriptor read/access.  This just grabs the value from the
            # setting store.
            return obj._store.get(self._key(obj))

        def __set__(self, obj, val):
            # Descriptor write/set.  This just sets the value in the setting
            # store.
            obj._store.set(self._key(obj), val)

        def __delete__(self, obj):
            # Descriptor delete.  This removes the value in the setting store.
            obj._store.delete(self._key(obj))

    class IntValue(Value):
        """An integer settings value descriptor.  Reading this value will return
        an integer value instead of a byte string (or None if it's not set).
        """

        def __get__(self, obj, type=None):
            # Call base value get and convert result to integer (if a value
            # exists).
            val = super().__get__(obj, type)
            if val is not None:
                return int(val)
            return val

    class FloatValue(Value):
        """A floating point settings value descriptor.  Reading this value will
        return a float value instead of a byte string (or None if it's not set).
        """

        def __get__(self, obj, type=None):
            val = super().__get__(obj, type)
            if val is not None:
                return float(val)
            return val

    class StrValue(Value):
        """A string settings value descriptor.  Reading this value will return a
        string value instead of a byte string (or None if it's not set).  You
        can optionally provide the string encoding to use when decoding the
        byte value to string (the default is 'utf8' for UTF8 strings).
        """

        def __init__(self, encoding='utf8', **kwargs):
            super().__init__(**kwargs)
            self._encoding = encoding

        def __get__(self, obj, type=None):
            val = super().__get__(obj, type)
            if val is not None:
                return val.decode(self._encoding)
            return val

    class BoolValue(Value):
        """A boolean settings value descriptor.  Reading this value will return a
        bool value instead of a byte string (or None if it's not set).
        """

        def __init__(self, encoding='utf8', **kwargs):
            super().__init__(**kwargs)
            self._encoding = encoding

        def __set__(self, obj, val):
            val = 'True' if val else 'False'
            super().__set__(obj, val)

        def __get__(self, obj, type=None):
            val = super().__get__(obj, type)
            if val is not None:
                return True if val == b'True' else False
            return val

    def __init__(self, store=None, name=None):
        # Default to an isolated in memory dictionary settings store if none is
        # provided.  This is great for simple use cases that don't need durable
        # settings.
        if store is None:
            store = DictSettingsStore()
        self._store = store
        # Use the name of this class instance if no explicit name is specified.
        if name is None:
            name = self.__class__.__name__
        self._settings_name = name
        # Enumerate all the Value attributes on this instance and set their
        # name (so they can generate key strings) and set any default value in
        # the setting store.
        for name, attr in filter(lambda x: isinstance(x[1], Settings.Value),
                                 vars(self.__class__).items()):
            # Tell the descriptor instance what its instance name is so it can
            # update its key value if necessary.
            attr.__set_name__(self, name)
            # Check if the descriptor has a default value and set it in the
            # store.
            if attr.default is not None:
                self._store.set_default(attr._key(self), attr.default)
