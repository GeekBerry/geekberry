import asyncio
import queue


def concurrence(*coroutines):
    loop = asyncio.get_event_loop()
    tasks = tuple(map(loop.create_task, coroutines))
    loop.run_until_complete(asyncio.wait(tasks))

    if len(coroutines) == 1:
        return tasks[0].result()
    else:
        return tuple(map(asyncio.Task.result, tasks))


class Queue:
    class Closed(Exception):
        pass

    def __init__(self, maxsize: int = 1, delay=0):
        assert isinstance(maxsize, int) and maxsize >= 1
        self._quque = queue.Queue(maxsize)
        self._opened = True
        self._delay = delay

    def full(self):
        return self._quque.full()

    async def put(self, value):
        if self._opened:
            while self.full():
                await asyncio.sleep(self._delay)
            self._quque.put_nowait(value)
        else:
            raise Queue.Closed()

    def empty(self):
        return self._quque.empty()

    async def get(self):
        while self.empty():
            if self._opened:
                await asyncio.sleep(self._delay)
            else:
                raise Queue.Closed()

        return self._quque.get_nowait()

    def close(self):
        """ 不再接受消息 """
        self._opened = False


if __name__ == '__main__' and 1:
    import random

    chan = Queue(2)


    async def p1():
        print('p1 start')

        for i in range(10):
            await chan.put(i)
            print('p1', i, '...')
            await asyncio.sleep(1)
        chan.close()


    async def c1():
        print('c1 start')

        while True:
            try:
                i = await chan.get()
                print('c1', i)
                await asyncio.sleep(random.uniform(0, 0.6))
            except Queue.Closed:
                break

        print('c1 stop')


    concurrence(p1(), c1())

if __name__ == '__main__' and 0:
    import time


    async def func(n: int):
        await asyncio.sleep(n)
        return n


    st = time.time()
    r0, r1, r2 = concurrence(func(0), func(1), func(2))
    print(r0, r1, r2)  # 0, 1, 2

    print(int(time.time() - st), 's')  # 2 s

    r4 = concurrence(func(4))
    print(r4)  # 4

    print(int(time.time() - st), 's')  # 6 s
