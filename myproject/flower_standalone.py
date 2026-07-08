"""
Lightweight Standalone Flower launcher.
Completely bypasses Django app initialization to avoid blocking Tornado event loop.
Usage: python flower_standalone.py
"""
import os
from celery import Celery

# Create a minimal Celery app that connects to the broker directly.
# This prevents Celery/Flower from initializing Django settings and loading models/database connections.
app = Celery('myproject')
app.config_from_object({
    'broker_url': 'redis://localhost:6000/0',
    'result_backend': 'redis://localhost:6000/0',
})

if __name__ == '__main__':
    # Launch flower
    app.start(['flower', '--', '--port=5555', '--address=0.0.0.0'])
