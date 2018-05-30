import asyncio


def concurrence(*coroutines):
    loop = asyncio.get_event_loop()
    tasks = tuple(map(loop.create_task, coroutines))
    loop.run_until_complete(asyncio.wait(tasks))

    if len(coroutines) == 1:
        return tasks[0].result()
    else:
        return tuple(map(asyncio.Task.result, tasks))


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
