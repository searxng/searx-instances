import pytest
import searxinstances.update


@pytest.mark.parametrize('url,expected', [
    ('searx.me', 'https://searx.me'),
    ('searx.onion', 'http://searx.onion'),
    ('searx.i2p', 'http://searx.i2p'),
    ('//searx.me', 'https://searx.me'),
    ('//searx.onion', 'http://searx.onion'),
    ('//searx.i2p', 'http://searx.i2p'),
    ('https://searx.me', 'https://searx.me'),
    ('http://searx.me', None),
    ('https://searx.onion', None),
    ('http://searx.onion', 'http://searx.onion'),
    ('https://searx.i2p', None),
    ('http://searx.i2p', 'http://searx.i2p'),
    ('http://searx.i2p', 'http://searx.i2p'),
    ('https://探す.com/', 'https://xn--88j075m.com'),
    ('HTTPS://SEARX.ME/about', 'https://searx.me/about'),
    ('https://searx.me/search?q=test', 'https://searx.me/search'),
    ('https://searx.me#anchor', 'https://searx.me')
    ])
def test_normalize_url(url, expected):
    assert searxinstances.update.normalize_url(url) == expected
