"""
ads/views.py
"""
from django.utils import timezone
from django.db.models import Q, F
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from .models import Advertisement
from .serializers import AdSerializer


@api_view(["GET"])
@permission_classes([AllowAny])
def ad_list(request):
    """
    GET /api/v1/ads/
    Returns live ads, optionally filtered by placement.
    Applies user-level targeting when the request is authenticated.
    Query params:
      placement = sidebar | banner | both (default: both)
      limit     = int (default: 4)
    """
    placement = request.query_params.get("placement", "both")
    limit     = min(int(request.query_params.get("limit", 4)), 10)
    now       = timezone.now()

    qs = Advertisement.objects.filter(
        is_active          = True,
        payment_status__in = ("paid", "complimentary"),
        starts_at__lte = now,
    ).filter(
        Q(ends_at__isnull=True) | Q(ends_at__gte=now)
    )

    # Placement filter
    if placement in ("sidebar", "banner"):
        qs = qs.filter(Q(placement=placement) | Q(placement="both"))

    # User targeting — only applied when authenticated
    if request.user.is_authenticated:
        profile = getattr(request.user, "profile", None)
        if profile:
            if not getattr(profile, "is_fasting_season", False):
                qs = qs.filter(target_fasting=False)
            if not getattr(profile, "is_pregnant", False):
                qs = qs.filter(target_pregnant=False)
            if not getattr(profile, "has_diabetes", False):
                qs = qs.filter(target_diabetes=False)
    else:
        # Anonymous users: exclude ads targeted at specific health conditions
        qs = qs.filter(
            target_fasting=False,
            target_pregnant=False,
            target_diabetes=False,
        )

    ads = qs.order_by("-priority", "?")[:limit]

    # Record impressions in bulk
    Advertisement.objects.filter(
        id__in=[a.id for a in ads]
    ).update(impressions=F("impressions") + 1)

    return Response(AdSerializer(ads, many=True).data)


@api_view(["POST"])
@permission_classes([AllowAny])
def ad_click(request, ad_id):
    """
    POST /api/v1/ads/<id>/click/
    Increments click counter. Called by the frontend when user taps CTA.
    Returns the ad's cta_url so the frontend can open it.
    """
    try:
        ad = Advertisement.objects.get(id=ad_id, is_active=True)
    except Advertisement.DoesNotExist:
        return Response({"error": "Ad not found."}, status=404)

    Advertisement.objects.filter(id=ad_id).update(
        clicks=F("clicks") + 1
    )
    return Response({"cta_url": ad.cta_url})


@api_view(["POST"])
@permission_classes([AllowAny])
def ad_submit(request):
    """
    POST /api/v1/ads/submit/
    Public endpoint — businesses submit their ad request.
    Creates an Advertisement with payment_status='unpaid' and is_active=False.
    Lands in Django admin for review → payment confirmation → activation.
    No authentication required so any business can submit without an account.
    """
    data = request.data

    required = ["business_name", "contact_email", "title", "category", "tier", "cta_url"]
    missing  = [f for f in required if not data.get(f, "").strip()]
    if missing:
        return Response(
            {"error": f"Missing required fields: {', '.join(missing)}"},
            status=400,
        )

    VALID_CATEGORIES = [c[0] for c in Advertisement.CATEGORY_CHOICES]
    VALID_TIERS      = [t[0] for t in Advertisement.TIER_CHOICES]

    if data["category"] not in VALID_CATEGORIES:
        return Response({"error": "Invalid category."}, status=400)
    if data["tier"] not in VALID_TIERS:
        return Response({"error": "Invalid tier."}, status=400)

    ad = Advertisement.objects.create(
        business_name   = data["business_name"].strip(),
        contact_email   = data["contact_email"].strip(),
        contact_phone   = data.get("contact_phone", "").strip(),
        title           = data["title"].strip(),
        tagline         = data.get("tagline", "").strip(),
        category        = data["category"],
        tier            = data["tier"],
        image_url       = data.get("image_url", "").strip(),
        cta_url         = data["cta_url"].strip(),
        cta_label       = data.get("cta_label", "Learn more").strip() or "Learn more",
        # Always starts inactive and unpaid — admin reviews and activates
        is_active       = False,
        payment_status  = "unpaid",
    )
    # amount_etb, priority, ends_at auto-set by model.save()

    TIER_PRICES = {"basic": 5000, "standard": 12000, "premium": 25000}
    return Response({
        "success": True,
        "message": "Your ad request has been received. Our team will contact you at "
                   f"{ad.contact_email} within 24 hours to confirm payment and next steps.",
        "ad_id":       str(ad.id),
        "tier":        ad.tier,
        "amount_etb":  TIER_PRICES.get(ad.tier, 5000),
    }, status=201)