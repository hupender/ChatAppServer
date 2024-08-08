from django.conf import settings
from redis.sentinel import Sentinel
import redis

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
                sentinal = Sentinel([self.hostname, self.port], socket_timeout=self.socket_timeout, db=self.db)
                self.redis_client = sentinal.master_for(self.master_name, password=self.password)
                return self.redis_client
            except:
                pass
        raise redis.ConnectionError()
    


data_cache = RedisProxy("DATA_DB")

