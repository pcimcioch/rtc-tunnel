import asyncio


class Tasks:
    def __init__(self):
        self._tasks = set()
        self._cancellable_tasks = set()

    def start_task(self, coro):
        task = asyncio.ensure_future(coro)
        self._clear_done()
        self._tasks.add(task)

    def start_cancellable_task(self, coro):
        task = asyncio.ensure_future(coro)
        self._clear_done()
        self._cancellable_tasks.add(task)

    def _clear_done(self):
        self._tasks = set([x for x in self._tasks if not x.done()])
        self._cancellable_tasks = set([x for x in self._cancellable_tasks if not x.done()])

    async def close_async(self):
        for task in self._cancellable_tasks:
            task.cancel()

        for task in self._tasks:
            await task
        for task in self._cancellable_tasks:
            await task

        self._tasks.clear()
        self._cancellable_tasks.clear()