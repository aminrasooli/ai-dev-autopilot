import time

from anthropic_api_kit.ratelimit import SlidingWindowLimiter


def test_allows_up_to_limit_immediately():
    limiter = SlidingWindowLimiter(max_calls=3, window_s=60)
    start = time.monotonic()
    for _ in range(3):
        assert limiter.acquire(block=False) is True
    assert time.monotonic() - start < 0.5


def test_blocks_when_limit_reached_nonblocking():
    limiter = SlidingWindowLimiter(max_calls=1, window_s=60)
    assert limiter.acquire(block=False) is True
    assert limiter.acquire(block=False) is False


def test_window_frees_up_after_expiry():
    limiter = SlidingWindowLimiter(max_calls=1, window_s=0.2)
    assert limiter.acquire(block=False) is True
    assert limiter.acquire(block=False) is False
    time.sleep(0.25)
    assert limiter.acquire(block=False) is True
