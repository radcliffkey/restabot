import asyncio
import time
import pytest
from typing import NoReturn

from restabot.util import parallel_process


async def _async_square(n: int) -> int:
    """Simple async function that squares a number after a short delay."""
    await asyncio.sleep(0.01)  # Simulate some async work
    return n * n


async def _async_fail(n: int) -> NoReturn:
    """Simple async function that always raises an exception."""
    await asyncio.sleep(0.01)
    raise ValueError(f"Failed for {n}")


async def _async_square_or_fail(n: int) -> int:
    """Async function that squares even numbers and fails for odd numbers."""
    await asyncio.sleep(0.01)
    if n % 2 == 0:
        return n * n
    else:
        raise ValueError(f"Failed for odd number {n}")


@pytest.mark.asyncio
async def test_parallel_process_success():
    """Test parallel_process with a function that always succeeds."""
    items = list(range(5))
    results = await parallel_process(items, _async_square, max_concurrency=2)
    assert len(results) == len(items)
    assert all(isinstance(r, int) for r in results)
    assert sorted(results) == [0, 1, 4, 9, 16]


@pytest.mark.asyncio
async def test_parallel_process_with_exceptions():
    """Test parallel_process handles exceptions correctly."""
    items = list(range(5))
    results = await parallel_process(items, _async_square_or_fail, max_concurrency=3)

    assert len(results) == len(items)
    success_results = [r for r in results if isinstance(r, int)]
    exceptions = [e for e in results if isinstance(e, Exception)]

    assert sorted(success_results) == [0, 4, 16]  # Squares of 0, 2, 4
    assert len(exceptions) == 2  # Failures for 1, 3

    assert all(isinstance(e, ValueError) for e in exceptions)
    exception_messages = [str(e) for e in exceptions]
    assert exception_messages == ["Failed for odd number 1", "Failed for odd number 3"]


@pytest.mark.asyncio
async def test_parallel_process_all_fail():
    """Test parallel_process when all tasks fail."""
    items = list(range(3))
    results = await parallel_process(items, _async_fail, max_concurrency=2)
    assert len(results) == len(items)
    assert all(isinstance(e, ValueError) for e in results)
    exception_messages = [str(e) for e in results]
    assert exception_messages == ["Failed for 0", "Failed for 1", "Failed for 2"]


@pytest.mark.asyncio
async def test_parallel_process_empty_list():
    """Test parallel_process with an empty input list."""
    items = []
    results = await parallel_process(items, _async_square, max_concurrency=5)
    assert results == []


@pytest.mark.asyncio
async def test_parallel_process_concurrency_limit():
    """Test that concurrency is respected (indirectly by timing)."""
    items = list(range(10))
    delay = 0.1

    async def delayed_square(n: int) -> int:
        await asyncio.sleep(delay)
        return n * n

    # Test with low concurrency
    start_time_low = time.monotonic()
    results_low = await parallel_process(items, delayed_square, max_concurrency=2)
    end_time_low = time.monotonic()
    duration_low = end_time_low - start_time_low

    # Test with high concurrency
    start_time_high = time.monotonic()
    results_high = await parallel_process(items, delayed_square, max_concurrency=5)
    end_time_high = time.monotonic()
    duration_high = end_time_high - start_time_high

    expected_results = [i * i for i in items]
    assert sorted(results_low) == expected_results
    assert sorted(results_high) == expected_results

    # Assert that higher concurrency leads to faster execution (within reason)
    # Expected duration for concurrency 2: ~ (10 tasks / 2 concurrency) * 0.1s = 0.5s
    # Expected duration for concurrency 5: ~ (10 tasks / 5 concurrency) * 0.1s = 0.2s
    # Allow some buffer for overhead
    assert duration_high < (len(items) * delay / 5) * 1.1
    assert duration_high < 0.5 * duration_low  # High concurrency should be noticeably faster

    # Test with concurrency 1 (sequential execution)
    start_time_seq = time.monotonic()
    results_seq = await parallel_process(items, delayed_square, max_concurrency=1)
    end_time_seq = time.monotonic()
    duration_seq = end_time_seq - start_time_seq

    assert sorted(results_seq) == expected_results
    assert duration_seq > (len(items) * delay) * 0.9  # Should be close to total delay
    assert duration_seq > duration_low * 1.5  # Sequential should be significantly slower
