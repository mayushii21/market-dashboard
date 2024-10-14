from functools import wraps
from typing import Any, Callable, TypeVar

from typing_extensions import Concatenate, ParamSpec

from innov8.app import app
from innov8.db_ops import data

P = ParamSpec("P")
R = TypeVar("R")


def data_access(func: Callable[Concatenate[Any, P], R]) -> Callable[P, R]:
    """Decorator which passes the db_ops.data instance as the first parameter of any function it decorates"""

    @wraps(func)
    def inner(*args: P.args, **kwargs: P.kwargs) -> R:
        return func(data, *args, **kwargs)

    return inner


# For convenience
callback = app.callback
