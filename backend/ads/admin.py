# backend/ads/admin.py
from django.contrib import admin
from django.utils.html import format_html
from datetime import date
from .models import Advertisement


# ── Bulk Actions Handlers ─────────────────────────────────────────────────────

@admin.action(description="✅ Mark selected as Paid")
def mark_paid_action(modeladmin, request, queryset):
    updated = queryset.update(payment_status="paid", payment_date=date.today())
    modeladmin.message_user(request, f"{updated} ad(s) marked as paid.")

@admin.action(description="⏳ Mark selected as Unpaid")
def mark_unpaid_action(modeladmin, request, queryset):
    updated = queryset.update(payment_status="unpaid")
    modeladmin.message_user(request, f"{updated} ad(s) marked as unpaid.")

@admin.action(description="🔴 Mark selected as Overdue")
def mark_overdue_action(modeladmin, request, queryset):
    updated = queryset.update(payment_status="overdue")
    modeladmin.message_user(request, f"{updated} ad(s) marked as overdue.")

@admin.action(description="▶️ Activate selected ads")
def activate_ads_action(modeladmin, request, queryset):
    ready = queryset.filter(payment_status__in=("paid", "complimentary"))
    updated = ready.update(is_active=True)
    skipped = queryset.count() - updated
    msg = f"{updated} ad(s) activated."
    if skipped:
        msg += f" {skipped} skipped — payment not confirmed."
    modeladmin.message_user(request, msg)

@admin.action(description="⏸️ Deactivate selected ads")
def deactivate_ads_action(modeladmin, request, queryset):
    updated = queryset.update(is_active=False)
    modeladmin.message_user(request, f"{updated} ad(s) deactivated.")

@admin.action(description="🔄 Reset impressions + clicks to 0")
def reset_analytics_action(modeladmin, request, queryset):
    updated = queryset.update(impressions=0, clicks=0)
    modeladmin.message_user(request, f"Analytics reset for {updated} ad(s).")


# ── Model Admin Configuration ──────────────────────────────────────────────────

@admin.register(Advertisement)
class AdvertisementAdmin(admin.ModelAdmin):

    list_display = [
        "business_name", "title", "category", "tier",
        "payment_status_badge", "amount_etb", "payment_date",
        "is_active", "live_status",
        "impressions", "clicks", "ctr_display",
        "starts_at", "ends_at",
    ]
    list_filter = [
        "payment_status", "tier", "is_active", "category", "placement",
        "target_fasting", "target_pregnant", "target_diabetes",
    ]
    search_fields = ["business_name", "title", "contact_email", "payment_reference"]
    
    # Safe handling: only keep structural properties that match concrete db columns
    readonly_fields = [
        "impressions", "clicks", "ctr_display", "live_status", "ad_preview", "tier_pricing_reference",
    ]
    
    list_editable = ["is_active"]
    
    # Remove "-created_at" to prevent database engine sorting exceptions
    ordering = ["business_name"] 

    fieldsets = [
        ("Advertiser", {
            "fields": ["business_name", "contact_email", "contact_phone"],
        }),
        ("Ad Content", {
            "fields": [
                "title", "tagline", "category", "placement",
                "image_url", "cta_label", "cta_url", "badge",
                "ad_preview",
            ],
        }),
        ("Payment & Billing", {
            "fields": [
                "tier", "tier_pricing_reference",
                "payment_status", "amount_etb",
                "payment_reference", "payment_date",
                "invoice_note",
            ],
        }),
        ("Scheduling & Activation", {
            "description": (
                "⚠️ Ad will only go live if both is_active=True AND "
                "payment_status is 'Paid' or 'Complimentary'."
            ),
            "fields": ["is_active", "priority", "starts_at", "ends_at"],
        }),
        ("Targeting (optional)", {
            "classes": ["collapse"],
            "fields": ["target_fasting", "target_pregnant", "target_diabetes"],
        }),
        ("Analytics (read-only)", {
            "classes": ["collapse"],
            "fields": ["impressions", "clicks", "ctr_display"],
        }),
    ]

    actions = [
        mark_paid_action,
        mark_unpaid_action,
        mark_overdue_action,
        activate_ads_action,
        deactivate_ads_action,
        reset_analytics_action,
    ]

    # ── Custom Columns Custom Display Logic ────────────────────────────────────

    @admin.display(description="Live?", boolean=True)
    def live_status(self, obj):
        return getattr(obj, 'is_live', False) if obj else False

    @admin.display(description="CTR %")
    def ctr_display(self, obj):
        val = getattr(obj, 'ctr', 0) if obj else 0
        return f"{val}%"

    @admin.display(description="Payment")
    def payment_status_badge(self, obj):
        if not obj:
            return ""
        colors = {
            "paid":          "#10b981",
            "unpaid":        "#f59e0b",
            "overdue":       "#ef4444",
            "complimentary": "#6366f1",
        }
        status_val = getattr(obj, 'payment_status', 'unpaid')
        color = colors.get(status_val, "#6b7280")
        display_text = obj.get_payment_status_display() if hasattr(obj, 'get_payment_status_display') else status_val
        return format_html(
            '<span style="background:{};color:white;font-size:10px;'
            'padding:2px 8px;border-radius:999px;font-weight:600;">{}</span>',
            color,
            display_text,
        )

    @admin.display(description="Tier Pricing (ETB)")
    def tier_pricing_reference(self, obj):
        return format_html(
            '<div style="font-size:11px;color:#6b7280;line-height:1.8;">'
            '🟢 Basic — 5,000 ETB / 30 days / sidebar only<br>'
            '🔵 Standard — 12,000 ETB / 60 days / sidebar + banner<br>'
            '⭐ Premium — 25,000 ETB / 90 days / all placements + priority<br>'
            '<em>Amount auto-fills from tier. Override manually if discounted.</em>'
            '</div>'
        )

    @admin.display(description="Ad Preview")
    def ad_preview(self, obj):
        if not obj or not getattr(obj, 'title', None):
            return "Save the ad first to see a preview."
            
        img_url = getattr(obj, 'image_url', '') or ''
        img_html = (
            f'<img src="{img_url}" style="width:60px;height:60px;'
            f'object-fit:cover;border-radius:8px;margin-right:10px;" />'
            if img_url else
            '<div style="width:60px;height:60px;background:#f3f4f6;border-radius:8px;'
            'display:inline-block;margin-right:10px;"></div>'
        )
        
        badge = getattr(obj, 'badge', '') or ''
        badge_html = (
            f'<span style="background:#10b981;color:white;font-size:10px;'
            f'padding:2px 8px;border-radius:999px;margin-left:6px;">{badge}</span>'
            if badge else ""
        )
        
        tagline_val = getattr(obj, 'tagline', '') or getattr(obj, 'business_name', '')
        cta_val = getattr(obj, 'cta_label', 'Learn More') or 'Learn More'
        
        return format_html(
            '<div style="display:flex;align-items:center;padding:12px;'
            'background:#f9fafb;border-radius:12px;border:1px solid #e5e7eb;max-width:340px;">'
            '{}'
            '<div>'
            '<div style="font-weight:600;font-size:13px;">{}{}</div>'
            '<div style="color:#6b7280;font-size:11px;margin-top:2px;">{}</div>'
            '<div style="margin-top:6px;background:#10b981;color:white;'
            'font-size:11px;padding:3px 10px;border-radius:6px;display:inline-block;">{}</div>'
            '</div></div>',
            format_html(img_html),
            obj.title,
            format_html(badge_html),
            tagline_val,
            cta_val,
        )