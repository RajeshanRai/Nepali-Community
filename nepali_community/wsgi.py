import os
import sys

# Add your project directory to sys.path
path = '/home/rajeshan/nepali_community'
if path not in sys.path:
    sys.path.append(path)

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nepali_community.settings')

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()