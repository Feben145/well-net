import uuid
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models

import community.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="WellnessCircle",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=100)),
                ("name_am", models.CharField(blank=True, default="", max_length=100)),
                ("description", models.TextField(blank=True, default="")),
                ("emoji", models.CharField(default="🌿", max_length=10)),
                ("invite_code", models.CharField(default=community.models.generate_invite_code, max_length=8, unique=True)),
                ("group_gut_score", models.IntegerField(default=0)),
                ("group_streak_days", models.IntegerField(default=0)),
                ("total_meals_logged", models.IntegerField(default=0)),
                ("edir_balance_etb", models.DecimalField(decimal_places=2, default=0, max_digits=8)),
                ("edir_goal_etb", models.DecimalField(decimal_places=2, default=800, max_digits=8)),
                ("edir_target_pkg", models.CharField(default="Kuriftu Group Wellness Package", max_length=100)),
                ("is_public", models.BooleanField(default=False)),
                ("max_members", models.IntegerField(default=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("created_by", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="circles_created", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="CircleMembership",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("role", models.CharField(choices=[("admin", "Admin"), ("member", "Member")], default="member", max_length=10)),
                ("is_active", models.BooleanField(default=True)),
                ("circle_gut_score", models.IntegerField(default=0)),
                ("circle_streak", models.IntegerField(default=0)),
                ("gursha_given", models.IntegerField(default=0)),
                ("gursha_received", models.IntegerField(default=0)),
                ("edir_contributed", models.DecimalField(decimal_places=2, default=0, max_digits=7)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("circle", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="memberships", to="community.wellnesscircle")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="circle_memberships", to=settings.AUTH_USER_MODEL)),
            ],
            options={"unique_together": {("circle", "user")}},
        ),
        migrations.CreateModel(
            name="JebenaCheckin",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("date", models.DateField()),
                ("food_slug", models.CharField(max_length=60)),
                ("food_name", models.CharField(max_length=120)),
                ("food_name_am", models.CharField(blank=True, default="", max_length=120)),
                ("gut_score", models.IntegerField(default=0)),
                ("message", models.CharField(blank=True, default="", max_length=200)),
                ("mood_emoji", models.CharField(default="🌿", max_length=5)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("circle", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="checkins", to="community.wellnesscircle")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="jebena_checkins", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-date", "-created_at"], "unique_together": {("circle", "user", "date")}},
        ),
        migrations.CreateModel(
            name="GurshaChallenge",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("food_slug", models.CharField(max_length=60)),
                ("food_name", models.CharField(max_length=120)),
                ("food_name_am", models.CharField(blank=True, default="", max_length=120)),
                ("message", models.CharField(blank=True, default="", max_length=200)),
                ("status", models.CharField(choices=[("pending", "Pending"), ("accepted", "Accepted"), ("expired", "Expired"), ("declined", "Declined")], default="pending", max_length=10)),
                ("expires_at", models.DateTimeField(default=community.models.default_expiry)),
                ("points_from", models.IntegerField(default=0)),
                ("points_to", models.IntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("circle", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="gursha_challenges", to="community.wellnesscircle")),
                ("from_user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="gursha_sent", to=settings.AUTH_USER_MODEL)),
                ("to_user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="gursha_received_set", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="EdirContribution",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("amount_etb", models.DecimalField(decimal_places=2, max_digits=7)),
                ("note", models.CharField(blank=True, default="", max_length=100)),
                ("is_confirmed", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("circle", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="edir_contributions", to="community.wellnesscircle")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="edir_contributions", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name="CommunityPost",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("post_type", models.CharField(choices=[("streak", "Streak"), ("score", "Score"), ("gursha", "Gursha"), ("jebena", "Jebena"), ("kuriftu", "Kuriftu"), ("challenge", "Challenge")], max_length=15)),
                ("title", models.CharField(max_length=150)),
                ("body", models.CharField(blank=True, default="", max_length=300)),
                ("emoji", models.CharField(default="🌿", max_length=5)),
                ("score", models.IntegerField(default=0)),
                ("streak", models.IntegerField(default=0)),
                ("is_anonymous", models.BooleanField(default=False)),
                ("likes", models.IntegerField(default=0)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("circle", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="circle_posts", to="community.wellnesscircle")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="community_posts", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
