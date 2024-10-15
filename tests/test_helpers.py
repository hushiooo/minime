import pytest

from src.helpers import DEFAULT_LENGTH, URL_SAFE_CHARS, encode, shorten_url

EXAMPLE_URL = "https://www.example.com"
LONG_URL_SUFFIX = "a" * 1000
SPECIAL_CHARS = "!@#$%^&*()"

ENCODE_TEST_CASES = [
    (0, "0"),
    (1, "1"),
    (10, "A"),
    (35, "Z"),
    (36, "a"),
    (61, "z"),
    (62, "10"),
    (1000000, "4C92"),
]


# Tests encode
@pytest.mark.parametrize("number, expected", ENCODE_TEST_CASES)
def test_encode(number, expected):
    assert encode(number) == expected


def test_encode_all_chars():
    for i, char in enumerate(URL_SAFE_CHARS):
        assert encode(i) == char


def test_encode_max_value():
    max_value = len(URL_SAFE_CHARS) ** DEFAULT_LENGTH - 1
    encoded = encode(max_value)
    assert len(encoded) <= DEFAULT_LENGTH


# Tests shorten_url
@pytest.mark.parametrize(
    "url",
    [
        EXAMPLE_URL,
        f"https://www.{LONG_URL_SUFFIX}.com",
        f"https://example.com/path?param=value&special={SPECIAL_CHARS}",
        "",
    ],
)
def test_shorten_url_properties(url):
    shortened = shorten_url(url)
    assert len(shortened) == DEFAULT_LENGTH
    assert all(char in URL_SAFE_CHARS for char in shortened)


def test_shorten_url_consistency():
    assert shorten_url(EXAMPLE_URL) == shorten_url(EXAMPLE_URL)


def test_shorten_url_different_urls():
    url1 = EXAMPLE_URL
    url2 = "https://www.example.org"
    assert shorten_url(url1) != shorten_url(url2)
