import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'gurubase.settings')

app = Celery('gurubase')

# Load task modules from all registered Django app configs.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps
app.autodiscover_tasks()

# Configure periodic tasks
app.conf.beat_schedule = {
    'update-historical-data-during-market-hours': {
        'task': 'dashboard.tasks.update_historical_data',
        'schedule': crontab(
            minute='*/5',
            hour='9-15',  # 9 AM to 3 PM
            day_of_week='1-5'  # Monday to Friday
        ),
        'options': {
            'expires': 300  # Task expires after 5 minutes
        }
    },
} 