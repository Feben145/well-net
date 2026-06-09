import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
application = get_wsgi_application()

# ─── SAFE FREE TIER SUPERUSER AUTO-CREATION ───
try:
    import django
    django.setup()
    
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    # Safely try to query the database. If tables don't exist yet, 
    # it catches the operational error instead of crashing the build.
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@wellnet.com', 'adminpass123')
        print("🚀 Production superuser checked/created successfully!")
    else:
        print("ℹ️ Admin user already exists. Skipping creation.")
        
except Exception as e:
    # This prevents the relation "users_user" does not exist error from killing your deploy
    print(f"⚠️ Superuser setup skipped during database initialization phase: {e}")