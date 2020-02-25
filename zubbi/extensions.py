# Copyright 2018 BMW Car IT GmbH
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import atexit
from functools import wraps

import zmq
from cachelib import NullCache, SimpleCache
from flask import current_app


def cached(key, timeout=3600):
    """Cache the return value of the decorated function with the given key.

    Key can be a String or a function.
    If key is a function, it must have the same arguments as the decorated function,
    otherwise it cannot be called successfully.
    """

    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            cache = get_cache()
            # Check if key is a function
            if callable(key):
                cache_key = key(*args, **kwargs)
            else:
                cache_key = key
            # Try to get the value from cache
            cached_val = cache.get(cache_key)
            if cached_val is None:
                # Call the original function and cache the result
                cached_val = f(*args, **kwargs)
                cache.set(cache_key, cached_val, timeout)
            return cached_val

        return wrapped

    return decorator


def get_cache():
    # Don't use caching in debug mode (mostly for development)
    if current_app.debug:
        return NullCache()
    if not hasattr(current_app, "extensions"):
        current_app.extensions = {}
    if "cache" not in current_app.extensions:
        current_app.extensions["cache"] = SimpleCache()
    return current_app.extensions["cache"]


def get_zmq_socket():
    if not hasattr(current_app, "extensions"):
        current_app.extensions = {}
    if "zmq_socket" not in current_app.extensions:
        context = zmq.Context()
        socket = context.socket(zmq.PUB)
        socket_addr = current_app.config["ZMQ_PUB_SOCKET_ADDRESS"]
        socket.bind(socket_addr)
        current_app.extensions["zmq_socket"] = socket

        # Register exit handler to properly close the socket
        atexit.register(socket.close)

    return current_app.extensions["zmq_socket"]
