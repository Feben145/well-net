from django.utils import timezone
from django.db.models import Q, F
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
import uuid

from .models import Advertisement
from .serializers import AdSerializer


@api_view(["GET"])
@permission_classes([AllowAny])
def ad_list(request):
    """
    GET /api/v1/ads/
    Returns live ads safely across authenticated and unauthenticated layouts.
    """
    placement = request.query_params.get("placement", "both")
    
    # 1. Safe parsing of pagination limits
    try:
        limit = min(int(request.query_params.get("limit", 4)), 10)
    except (ValueError, TypeError):
        limit = 4

    now = timezone.now()

    # 2. Extract baseline matching records
    qs = Advertisement.objects.filter(
        is_active=True,
        payment_status__in=("paid", "complimentary"),
        starts_at__lte=now,
    ).filter(
        Q(ends_at__isnull=True) | Q(ends_at__gte=now)
    )

    # 3. Handle explicit UI layout placement conditions
    if placement in ("sidebar", "banner"):
        qs = qs.filter(Q(placement=placement) | Q(placement="both"))

    # 4. Bulletproof user medical profile restriction mapping
    if request.user and request.user.is_authenticated:
        profile = getattr(request.user, "profile", None)
        if profile:
            if not getattr(profile, "is_fasting_season", False):
                qs = qs.filter(target_fasting=False)
            if not getattr(profile, "is_pregnant", False):
                qs = qs.filter(target_pregnant=False)
            if not getattr(profile, "has_diabetes", False):
                qs = qs.filter(target_diabetes=False)
    else:
        # Prevent evaluation failures on unauthenticated requests
        qs = qs.filter(
            target_fasting=False,
            target_pregnant=False,
            target_diabetes=False
        )

    # 5. Order random subsets safely
    ads = list(qs.order_by("-priority", "?")[:limit])

    # 6. Bulk record impressions using concrete object extraction to prevent UUID parsing errors
    if ads:
        ad_ids = [a.pk for a in ads]
        Advertisement.objects.filter(pk__in=ad_ids).update(impressions=F("impressions") + 1)

    return Response(AdSerializer(ads, many=True).data, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([AllowAny])
def ad_click(request, ad_id):
    """
    POST /api/v1/ads/<id>/click/
    Handles click analytics updates across standard or customized UUID signatures.
    """
    # Sanitize input key type conversions to handle potential UUID mismatches safely
    try:
        target_id = uuid.UUID(str(ad_id)) if "-" in str(ad_id) else ad_id
    except ValueError:
        return Response({"error": "Invalid Ad ID format."}, status=status.HTTP_400_BAD_REQUEST)

    try:
        ad = Advertisement.objects.get(pk=target_id, is_active=True)
    except Advertisement.DoesNotExist:
        return Response({"error": "Ad not found."}, status=status.HTTP_404_NOT_FOUND)

    Advertisement.objects.filter(pk=target_id).update(clicks=F("clicks") + 1)
    return Response({"cta_url": ad.cta_url}, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([AllowAny])
def ad_submit(request):
    """
    POST /api/v1/ads/submit/
    Saves new campaign drafts smoothly from enterprise businesses.
    """
    data = request.data or {}

    required = ["business_name", "contact_email", "title", "category", "tier", "cta_url"]
    missing = [f for f in required if not str(data.get(f, "")).strip()]
    
    if missing:
        return Response(
            {"error": f"Missing required fields: {', '.join(missing)}"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    VALID_CATEGORIES = [c[0] for c in Advertisement.CATEGORY_CHOICES]
    VALID_TIERS = [t[0] for t in Advertisement.TIER_CHOICES]

    if data.get("category") not in VALID_CATEGORIES:
        return Response({"error": "Invalid category choice selection."}, status=status.HTTP_400_BAD_REQUEST)
    if data.get("tier") not in VALID_TIERS:
        return Response({"error": "Invalid service tier choice package."}, status=status.HTTP_400_BAD_REQUEST)

    ad = Advertisement.objects.create(
        business_name=str(data["business_name"]).strip(),
        contact_email=str(data["contact_email"]).strip(),
        contact_phone=str(data.get("contact_phone", "")).strip(),
        title=str(data["title"]).strip(),
        tagline=str(data.get("tagline", "")).strip(),
        category=data["category"],
        tier=data["tier"],
        image_url=str(data.get("image_url", "")).strip(),
        cta_url=str(data["cta_url"]).strip(),
        cta_label=str(data.get("cta_label", "Learn more")).strip() or "Learn more",
        is_active=False,
        payment_status="unpaid",
    )

    TIER_PRICES = {"basic": 5000, "standard": 12000, "premium": 25000}
    return Response({
        "success": True,
        "message": f"Your ad request has been received. Our team will contact you at {ad.contact_email} within 24 hours to confirm payment.",
        "ad_id": str(ad.pk),
        "tier": ad.tier,
        "amount_etb": TIER_PRICES.get(ad.tier, 5000),
    }, status=status.HTTP_201_CREATED)