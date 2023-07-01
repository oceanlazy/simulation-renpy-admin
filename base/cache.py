import base64
import pickle

from django.core.cache.backends.base import DEFAULT_TIMEOUT
from django.core.cache.backends.db import DatabaseCache
from django.db import connection


class LocalMemoryDatabaseCache(DatabaseCache):
    def __init__(self, table, params):
        super().__init__(table, params)
        with connection.cursor() as cursor:
            cursor.execute('SELECT cache_key, value FROM cache_table')  # noqa
            self.cache = {
                cache_key: pickle.loads(base64.b64decode(connection.ops.process_clob(value).encode()))
                for cache_key, value in cursor.fetchall()
            }
        self.key_func = self.key_function

    @staticmethod
    def key_function(key, *_):
        return key

    def get(self, key, default=None, version=None):
        return self.cache.get(key)

    def set(self, key, value, timeout=DEFAULT_TIMEOUT, version=None):
        self.cache[key] = value
        super().set(key, value, timeout, version)

    def clear(self):
        self.cache = {}
        super().clear()
