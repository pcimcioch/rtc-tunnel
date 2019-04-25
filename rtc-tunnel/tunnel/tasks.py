import asyncio


class Tasks:
    def __init__(self):
        self._tasks = set()

    def start_task(self, coro):
        task = asyncio.ensure_future(coro)
        self._clear_done()
        self._tasks.add(task)

    def _clear_done(self):
        self._tasks = set([x for x in self._tasks if not x.done()])

    async def close_async(self):
        for task in self._tasks:
            await task
        self._tasks.clear()