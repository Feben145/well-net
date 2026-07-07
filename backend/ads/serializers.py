"""
ads/serializers.py
"""
from rest_framework import serializers
from .models import Advertisement


class AdSerializer(serializers.ModelSerializer):
    class Meta:
        model  = Advertisement
        fields = [
            "id", "title", "tagline", "business_name",
            "category", "placement", "image_url",
            "cta_label", "cta_url", "badge",
        ]