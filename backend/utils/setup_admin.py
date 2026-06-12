#!/usr/bin/env python
import os
import sys
import django
from pathlib import Path

# Force Python to find 'config' and your apps relative to this script's location
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Initialize Django settings configuration safely
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

def create_admin():
    from django.contrib.auth import get_user_model
    User = get_user_model()
    try:
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@wellnet.com', 'adminpass123')
            print("🚀 Production superuser checked/created successfully!")
        else:
            print("ℹ️ Admin user already exists.")
    except Exception as e:
        print(f"⚠️ Script execution skipped: {e}")

if __name__ == '__main__':
    create_admin()