import xxhash
from cachetools import LFUCache, cached

URL_SAFE_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
BASE = len(URL_SAFE_CHARS)
DEFAULT_LENGTH = 7


def encode(number: int, base: int = BASE) -> str:
    """Encode an integer to a given base string."""

    if number == 0:
        return URL_SAFE_CHARS[0]

    encoding = ""
    while number:
        number, remainder = divmod(number, base)
        encoding = URL_SAFE_CHARS[remainder] + encoding
    return encoding


@cached(LFUCache(maxsize=1000))
def shorten_url(url: str) -> str:
    """Generate a shortened URL code."""

    hash_int = xxhash.xxh64(url).intdigest()

    max_value = BASE**DEFAULT_LENGTH - 1
    hash_int = hash_int % max_value

    encoded = encode(hash_int)
    return encoded.rjust(DEFAULT_LENGTH, URL_SAFE_CHARS[0])
