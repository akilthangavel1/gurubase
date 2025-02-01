import os
from celery import Celery

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gurubase.settings')

app = Celery('gurubase')

# Load task modules from all registered Django app configs.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps
app.autodiscover_tasks()

# Configure periodic tasks
app.conf.beat_schedule = {
    'update-historical-data-every-5-minutes': {
        'task': 'dashboard.tasks.update_historical_data',
        'schedule': 300.0,  # 300 seconds = 5 minutes
    },
} 