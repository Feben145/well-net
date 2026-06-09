import os
from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
application = get_wsgi_application()

# ─── FREE TIER SUPERUSER AUTO-CREATION ───
# This runs instantly when Gunicorn boots up the app on Render
try:
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    # Check if our admin user already exists so we don't duplicate it
    if not User.objects.filter(username='admin').exists():
        # Change 'adminpass123' to whatever secure password you want!
        User.objects.create_superuser('admin', 'admin@wellnet.com', 'adminpass123')
        print("🚀 Production superuser created successfully!")
except Exception as e:
    print(f"Superuser setup skipped or failed: {e}")
