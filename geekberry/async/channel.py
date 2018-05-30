import asyncio
import queue


class Channel:
    class Closed(Exception):
        pass

    def __init__(self, maxsize: int = 1):
        assert isinstance(maxsize, int) and maxsize >= 1
        self.__quque = queue.Queue(maxsize)
        self.__opened = True

    async def put(self, value):
        if self.__opened:
            while self.__quque.full():
                await asyncio.sleep(0)
            self.__quque.put_nowait(value)
        else:
            raise Channel.Closed()

    async def get(self):
        while self.__quque.empty() and self.__opened:
            await asyncio.sleep(0)

        try:
            return self.__quque.get_nowait()
        except queue.Empty:
            raise Channel.Closed()

    def close(self):
        self.__opened = False


if __name__ == '__main__':
    import random
    from geekberry import concurrence

    chan = Channel(2)


    async def p1():
        print('p1 start')

        for i in range(10):
            await chan.put(i)
            print('p1', i, '...')
            await asyncio.sleep(0.3)
        chan.close()


    async def c1():
        print('c1 start')

        while True:
            try:
                i = await chan.get()
                print('c1', i)
                await asyncio.sleep(random.uniform(0, 0.6))
            except Channel.Closed:
                break


    concurrence(p1(), c1())

    # p1 start
    # p1 0 ...
    # c1 start
    # c1 0
    # p1 1 ...
    # c1 1
    # p1 2 ...
    # c1 2
    # p1 3 ...
    # c1 3
    # p1 4 ...
    # c1 4
    # p1 5 ...
    # c1 5
    # p1 6 ...
    # p1 7 ...
    # c1 6
    # p1 8 ...
    # c1 7
    # p1 9 ...
    # c1 8
    # c1 9
