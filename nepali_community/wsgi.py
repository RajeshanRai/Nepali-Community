import os
import sys

from pathlib import Path

# Add your project directory to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
project_path = str(BASE_DIR)
if project_path not in sys.path:
    sys.path.append(project_path)

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'nepali_community.settings')

from django.core.wsgi import get_wsgi_application
application = get_wsgi_application()