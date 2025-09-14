import asyncio
import time
import traceback
import logging

logger = logging.getLogger(__name__)

async def rerun_on_exception(coro, *args, **kwargs):
    """Restart coroutine by waiting an exponential time deplay"""
    max_sleep = 1 * 60  # sleep for at most 1 mins until rerun
    reset = 3 * 60  # reset after 3 minutes running successfully
    init_sleep = 1  # always start with sleeping for 1 second

    next_sleep = init_sleep
    while True:
        start_t = int(time.monotonic())  # seconds

        try:
            return await coro(*args, **kwargs)
        except asyncio.CancelledError:
            raise
        except Exception:
            traceback.print_exc()

        end_t = int(time.monotonic())  # seconds

        if end_t - start_t < reset:
            sleep_t = next_sleep
            next_sleep = min(max_sleep, next_sleep * 2)  # double sleep time
        else:
            next_sleep = init_sleep  # reset sleep time
            sleep_t = next_sleep

        logging.warning(f"Restarting coroutine in {sleep_t} seconds")
        await asyncio.sleep(sleep_t)

def store_reference_to_task(task: asyncio.Task, task_set: set[asyncio.Task]):
    task_set.add(task)
    task.add_done_callback(task_set.discard)
