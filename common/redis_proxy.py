from django.conf import settings
from redis.sentinel import Sentinel
import redis
import json

class RedisProxy:
    
    def __init__(self, db_name, redis_key_expiry=settings.REDIS_KEY_EXPIRY, socket_timeout=0.5):
        self.hostname = settings.REDIS_SENTINAL_SERVER["HOST"]
        self.port = settings.REDIS_SENTINAL_SERVER["PORT"]
        self.db = settings.REDIS_SENTINAL_SERVER[db_name]
        self.password = settings.REDIS_SENTINAL_SERVER["PASSWORD"]
        self.master_name = settings.REDIS_SENTINAL_SERVER["MASTER_NAME"]
        self.key_expiry = redis_key_expiry
        self.socket_timeout = socket_timeout
        self.redis_client = self.get_client()

    def get_client(self):
        for _ in range(3):
            try:
                sentinal = Sentinel([(self.hostname, self.port)], socket_timeout=self.socket_timeout, db=self.db)
                self.redis_client = sentinal.master_for(self.master_name, password=self.password)
                return self.redis_client
            except:
                pass
        raise redis.ConnectionError()
    
    def set(self, key, value, ex=None):
        try:
            self.redis_client.set(key, value, ex if ex else self.key_expiry)
        except redis.RedisError as err:
            raise Exception(str(err))
        
    def lset(self, key, value, ex=None):
        try:
            self.redis_client.lpush(key, value)
            self.redis_client.expire(name=key, time=ex if ex else self.key_expiry)
        except redis.RedisError as err:
            raise Exception(str(err))
        
    def lsetindex(self, key, value, index, ex=None):
        try:
            self.redis_client.lset(key, index, value)
            self.redis_client.expire(name=key, time=ex if ex else self.key_expiry)
        except redis.RedisError as err:
            raise Exception(str(err))

    def ldel(self, key, value, del_from=0):
        try:
            return self.redis_client.lrem(key, del_from, value)
        except redis.RedisError as err:
            raise Exception(str(err))

    def lget(self, key, default=[]):
        try:
            value = self.redis_client.lrange(key, 0, -1)
            return value if value else default
        except redis.RedisError as err:
            raise Exception(str(err))

    def get(self, key, default=None):
        try:
            value = self.redis_client.get(key)
            return value.decode() if value else default
        except redis.RedisError as err:
            raise Exception(str(err))

    def hset(self, name, key, value, ex=None):
        try:
            self.redis_client.hset(name, key, value)
            self.redis_client.expire(name=name, time=ex if ex else self.key_expiry)
        except redis.RedisError as err:
            raise Exception(str(err))

    def hmset(self, name, mapping, ex=None):
        try:
            self.redis_client.hset(name, mapping)
            self.redis_client.expire(name=name, time=ex if ex else self.key_expiry)
        except redis.RedisError as err:
            raise Exception(str(err))

    def hmget(self, name, keys):
        try:
            return self.redis_client.hmget(name, keys)
        except redis.RedisError as err:
            raise Exception(str(err))

    def hget(self, name, key, default=None):
        try:
            value = self.redis_client.hget(name=name, key=key)
            return value.decode() if value else default
        except redis.RedisError as err:
            raise Exception(str(err))

    def hgetall(self, name, default=None):
        try:
            value = self.redis_client.hgetall(name=name)
            return {k.decode(): v.decode() for k, v in value.items()}
        except redis.RedisError as err:
            raise Exception(str(err))

    def hdel(self, name, key):
        try:
            return self.redis_client.hdel(name, key)
        except redis.RedisError as err:
            raise Exception(str(err))

    def delete(self, key):
        try:
            key = [key] if not isinstance(key, list) else key
            return self.redis_client.delete(*key)
        except redis.RedisError as err:
            raise Exception(str(err))

    def get_or_set(self, key, model):
        res = self.get(key)
        if res:
            return json.loads(res)
        data = [item for item in model.objects.all().values(*model.CACHE_FIELDS)]
        data_cache.set(key, json.dumps(data))
        return data
    
    def eval(self, script, keys, args):
        try:
            lua_script = self.redis_client.register_script(script)
            values = lua_script(keys=keys, args=args)
            return values
        except redis.RedisError as err:
            raise Exception(str(err))

    def zcount(self, key, min, max):
        try:
            return self.redis_client.zcount(key, min, max)
        except redis.RedisError as err:
            raise Exception(str(err))

    def zrem(self, name, member):
        try:
            return self.redis_client.zrem(name, member)
        except redis.RedisError as err:
            raise Exception(str(err))

    def zadd(self, name, mapping):
        try:
            return self.redis_client.zadd(name, mapping)
        except redis.RedisError as err:
            raise Exception(str(err))

    def keys(self, pattern):
        try:
            return self.redis_client.keys(pattern)
        except redis.RedisError as err:
            raise Exception(str(err))

    def zscore(self, key, member):
        try:
            return self.redis_client.zscore(key, member)
        except redis.RedisError as err:
            raise Exception(str(err))

    def zrange(self, name, start, end, withscores=False):
        try:
            if withscores:
                return self.redis_client.zrange(name, start, end, withscores=withscores)
            else:
                return self.redis_client.zrange(name, start, end)
        except redis.RedisError as err:
            raise Exception(str(err))

    
def get_redis_instance(db="DATA_DB"):
    return RedisProxy(db)

data_cache = get_redis_instance()

