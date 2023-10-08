from innov8.app import app
from innov8.db_ops import data


# Define a decorator which passes the data_instance as the first parameter
# of any function it decorates
def data_access(func):
    def inner(*args, **kwargs):
        return func(data, *args, **kwargs)

    return inner


# For convenience
callback = app.callback
