import os
from django.conf import settings
from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatApp.settings')

def get_redis_broker():
    password = settings.REDIS_SENTINAL_SERVER["PASSWORD"]
    host = settings.REDIS_SENTINAL_SERVER["HOST"]
    port = settings.REDIS_SENTINAL_SERVER["PORT"]
    broker_db = settings.REDIS_SENTINAL_SERVER["BROKER_DB"]
    
    addr = f"sentinel://:{password}@{host}:{port}/{broker_db}"
    return addr

CELERY_REDIS_BROKER = get_redis_broker()
CELERY_RESULT_BACKEND = CELERY_REDIS_BROKER

app = Celery('chatApp', backend=CELERY_RESULT_BACKEND, broker=CELERY_REDIS_BROKER)

app.conf.broker_transport_options = {"master_name": "mymaster"}
app.conf.result_backend_transport_options = {"master_name": "mymaster"}

# Load task modules from all registered Django apps.
app.autodiscover_tasks()
