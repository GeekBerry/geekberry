## concurrence 
协程并发函数

例1: 利用 concurrence 执行将协程函数转为同步执行
```python
import time
import asyncio
from geekberry import concurrence

st = time.time()
concurrence(asyncio.sleep(3))
print(int(time.time() - st), 's')  # 3 s
```

例2: 利用 concurrence 并发执行协程函数
```python
import time
import asyncio
from geekberry import concurrence

async def func(n: int):
    await asyncio.sleep(n)
    return n


st = time.time()
r0, r1, r2 = concurrence(func(0), func(1), func(2))
print(r0, r1, r2)  # 0, 1, 2  收集每个协程返回值

print(int(time.time() - st), 's')  # 2 s 可见执行时间为多个协程函数中最长者

r4 = concurrence(func(4))
print(r4)  # 4

print(int(time.time() - st), 's')  # 6 s
```

## Queue
协程信道

```python
import asyncio
import random
from geekberry import concurrence, Queue

chan = Queue(2)  # 设置信道队列尺寸, 默认为 1


async def p1():  # 生产者
    print('p1 start')

    for i in range(10):
        await chan.put(i)  # 向 Queue 中放
        print('p1', i, '...')
        await asyncio.sleep(0.3)
    chan.close()  # 关闭后将不能再放数据, 否则抛出 Queue.Closed 异常
    # 注意: 不再使用(放置数据)的信道不关闭, 会导致死锁


async def c1():  # 消费者
    print('c1 start')

    while True:
        try:
            i = await chan.get()  # 从 Queue 中取数据
            print('c1', i)
            await asyncio.sleep(random.uniform(0, 0.6))
        except Queue.Closed:
            break


concurrence(p1(), c1())
```
输出:
```
p1 start
p1 0 ...
c1 start
c1 0
p1 1 ...
c1 1
p1 2 ...
c1 2
p1 3 ...
c1 3
p1 4 ...
c1 4
p1 5 ...
c1 5
p1 6 ...
p1 7 ...
c1 6
p1 8 ...
c1 7
p1 9 ...
c1 8
c1 9
```