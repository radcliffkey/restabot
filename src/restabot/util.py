import asyncio
from typing import Awaitable, Callable, Iterable, TypeVar

R = TypeVar('R')
T = TypeVar('T')


async def parallel_process(
        items: Iterable[T],
        afunc: Callable[[T], Awaitable[R]],
        max_concurrency: int
) -> list[R | Exception]:
    """
    Asynchronously process a collection of items with a specified concurrency limit.

    :param items: The collection of items to process.
    :type items: Iterable[T]
    :param afunc: An asynchronous function to apply to each item.
    :type afunc: Callable[[T], Awaitable[R]]
    :param max_concurrency: The maximum number of concurrent executions allowed.
    :type max_concurrency: int
    :return: A list of results or exceptions from processing each item.
             The order of results corresponds to the order of the input items.
    :rtype: list[R | Exception]
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
