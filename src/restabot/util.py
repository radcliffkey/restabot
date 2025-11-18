import asyncio
import logging
from typing import Awaitable, Callable, Iterable, TypeVar

R = TypeVar('R')
T = TypeVar('T')

LOG = logging.getLogger(f'{__package__}.util')

MAX_RETRIES = 3
INITIAL_RETRY_DELAY = 1.0
RETRY_BACKOFF_MULTIPLIER = 2.0


async def parallel_process(
        items: Iterable[T],
        afunc: Callable[[T], Awaitable[R]],
        max_concurrency: int
) -> list[R | Exception]:
    """
    Asynchronously process a collection of items with a specified concurrency limit.

    :param items: The collection of items to process.
    :param afunc: An asynchronous function to apply to each item.
    :param max_concurrency: The maximum number of concurrent executions allowed.
    :return: A list of results or exceptions from processing each item.
             The order of results corresponds to the order of the input items.
    """
    semaphore = asyncio.Semaphore(max_concurrency)
    tasks = []

    async def process_item_with_semaphore(item):
        async with semaphore:
            return await afunc(item)

    for item in items:
        task = asyncio.create_task(process_item_with_semaphore(item))
        tasks.append(task)

    return await asyncio.gather(*tasks, return_exceptions=True)


async def retry_with_exponential_backoff(
        func: Callable[[], Awaitable[R]],
        max_retries: int = MAX_RETRIES,
        initial_delay: float = INITIAL_RETRY_DELAY,
        backoff_multiplier: float = RETRY_BACKOFF_MULTIPLIER,
) -> R:
    """
    Retry an async function with exponential backoff.

    :param func: The async function to retry (should be a coroutine function).
    :param max_retries: Maximum number of retry attempts.
    :param initial_delay: Initial delay in seconds before the first retry.
    :param backoff_multiplier: Multiplier for exponential backoff.
    :return: The result of the function call.
    :raises: The last exception if all retries are exhausted.
    """
    delay = initial_delay
    last_exception: Exception | None = None

    for attempt in range(max_retries + 1):
        try:
            return await func()
        except Exception as e:
            last_exception = e
            if attempt < max_retries:
                LOG.warning(f'Attempt {attempt + 1} failed: {type(e).__name__}: {e}. Retrying in {delay:.1f}s...')
                await asyncio.sleep(delay)
                delay *= backoff_multiplier
            else:
                LOG.error(f'All {max_retries + 1} attempts failed. Last error: {type(e).__name__}: {e}')

    if last_exception is not None:
        raise last_exception
    raise RuntimeError('Retry function completed without exception or return value')
