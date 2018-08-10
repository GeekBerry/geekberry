from .concurrence import concurrence, Queue


def cache_property(func):
    # @wraps ??? 是否需要?
    def wrapper(*args, **kwargs):
        try:
            return getattr(wrapper, 'return')
        except AttributeError:
            ret = func(*args, **kwargs)
            setattr(wrapper, 'return', ret)
            return ret

    return property(wrapper)  # 只给出 getter
