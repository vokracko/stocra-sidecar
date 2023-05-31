import asyncio
from typing import Coroutine

ABANDONED_TASKS = set()


def create_task_safely(coroutine: Coroutine) -> None:
    task = asyncio.create_task(coroutine)
    ABANDONED_TASKS.add(task)
    task.add_done_callback(ABANDONED_TASKS.discard)
