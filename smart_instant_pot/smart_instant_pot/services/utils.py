# Smart Instant Pot Service Utilities
# These are handy utility functions for services that make up the Smart Instant
# Pot project.
# Author: Tony DiCola


def build_id(*components):
    """Generate a string identifier composed of all the string components (in
    order) and concatenated with a colon ':' between them.  This is useful for
    generating an identifier or 'path' to a value in a setting store.
    """
    return ':'.join(components)

def to_bytes(val):
    """Convert a value to a string based representation stored as UTF8 bytes
    if it isn't already a byte string.  This is useful for test implementations
    that want to abide by strict interface requirements (that data is always
    stored and retrieved as bytes).
    """
    if isinstance(val, (bytes, bytearray)):
        return val
    return str(val).encode('utf8')
