"""
Service-layer functions for KaamConnect business logic.
"""
import logging
from decimal import Decimal

from django.db.models import Q, F, Value
from django.db.models.functions import Coalesce

from .models import (
    WorkerProfile,
    Service,
    ServiceCategory,
    Booking,
    haversine_km,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Intelligent Worker Matching Algorithm
# ---------------------------------------------------------------------------
def get_recommended_workers(service, customer_lat=None, customer_lon=None, limit=10):
    """
    Rank WorkerProfile objects for a given service using a weighted score:

        Skill Match   – 40 %
        Distance      – 25 %
        Rating        – 20 %
        Availability  – 15 %

    Parameters
    ----------
    service : Service
        The service being booked (used to match against worker skills).
    customer_lat, customer_lon : float | None
        GPS coordinates of the customer at booking time.
    limit : int
        Maximum number of workers to return.

    Returns
    -------
    list[dict]
        Each dict contains a WorkerProfile instance and its composite score.
    """
    category_slug = service.category.slug

    # Start with all verified workers who have at least one skill
    workers = WorkerProfile.objects.filter(
        verification_status=WorkerProfile.VerificationStatus.VERIFIED,
    ).exclude(
        skills=[],
    ).select_related("user")

    # Pre-filter: keep only workers whose skills list includes this category
    # (SQLite JSON containment; for Postgres we'd use JSONField__contains)
    candidates = []
    for wp in workers:
        if category_slug in wp.skills:
            candidates.append(wp)

    if not candidates:
        # Broaden: return all verified workers regardless of skill match
        candidates = list(workers[:50])

    scored = []
    for wp in candidates:
        # ── Skill Match (40 %) ──
        skill_score = 1.0 if category_slug in wp.skills else 0.0

        # ── Distance (25 %) ──
        distance_score = 0.5  # default when coords unavailable
        if customer_lat is not None and customer_lon is not None and wp.latitude and wp.longitude:
            dist_km = haversine_km(customer_lat, customer_lon, wp.latitude, wp.longitude)
            radius = max(wp.service_radius_km, 1)
            if dist_km <= radius:
                distance_score = max(0.0, 1.0 - (dist_km / radius))
            else:
                distance_score = 0.0  # outside radius

        # ── Rating (20 %) ──
        rating_score = float(wp.rating) / 5.0 if wp.rating else 0.0

        # ── Availability (15 %) ──
        avail_map = {
            WorkerProfile.AvailabilityStatus.AVAILABLE: 1.0,
            WorkerProfile.AvailabilityStatus.BUSY: 0.5,
            WorkerProfile.AvailabilityStatus.OFFLINE: 0.0,
        }
        availability_score = avail_map.get(wp.availability_status, 0.0)

        composite = (
            skill_score * 0.40
            + distance_score * 0.25
            + rating_score * 0.20
            + availability_score * 0.15
        )

        scored.append(
            {
                "worker": wp,
                "score": round(composite, 4),
                "skill_score": round(skill_score, 2),
                "distance_score": round(distance_score, 2),
                "rating_score": round(rating_score, 2),
                "availability_score": round(availability_score, 2),
            }
        )

    # Sort descending by composite score
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:limit]


# ---------------------------------------------------------------------------
# Available Bookings for Worker (geo + skill filtered)
# ---------------------------------------------------------------------------
def get_available_bookings_for_worker(worker_profile):
    """
    Returns list of PENDING, unassigned bookings that match the worker's
    skills (by ServiceCategory slug) and are within service_radius_km.
    """
    pending = Booking.objects.filter(
        status=Booking.BookingStatus.PENDING,
        worker__isnull=True,
    ).select_related("service__category", "customer").order_by("scheduled_time")

    # Filter by category skill match
    if worker_profile.skills:
        pending = pending.filter(service__category__slug__in=worker_profile.skills)

    # Filter by geographic radius in Python (SQLite doesn't support geo queries natively)
    if worker_profile.latitude and worker_profile.longitude:
        filtered = []
        for booking in pending:
            dist = haversine_km(
                worker_profile.latitude,
                worker_profile.longitude,
                booking.customer_latitude,
                booking.customer_longitude,
            )
            if dist <= worker_profile.service_radius_km:
                filtered.append(booking)
        return filtered

    return list(pending)


# ---------------------------------------------------------------------------
# Earnings Calculations
# ---------------------------------------------------------------------------
def calculate_worker_earnings(worker_profile):
    """Aggregate earnings summary for a worker."""
    from django.db.models import Sum, Q
    from .models import CoopEarning

    earnings = CoopEarning.objects.filter(worker=worker_profile)

    total_lifetime = earnings.aggregate(total=Sum("worker_payout"))["total"] or Decimal("0.00")
    pending_payout = earnings.filter(
        payout_status=CoopEarning.PayoutStatus.PENDING
    ).aggregate(total=Sum("worker_payout"))["total"] or Decimal("0.00")

    # Current month earnings
    from django.utils import timezone

    now = timezone.now()
    monthly = earnings.filter(
        created_at__year=now.year, created_at__month=now.month
    ).aggregate(total=Sum("worker_payout"))["total"] or Decimal("0.00")

    # Dividend shares (coop_fee portion from bookings this worker completed)
    dividend_shares = earnings.aggregate(
        total=Sum("coop_dividend_pool")
    )["total"] or Decimal("0.00")

    return {
        "total_lifetime": total_lifetime,
        "pending_payout": pending_payout,
        "monthly_earnings": monthly,
        "dividend_shares": dividend_shares,
    }


def calculate_booking_fees(total_amount):
    """Return the fee breakdown for a given total amount."""
    gross = Decimal(str(total_amount))
    platform_fee = (gross * Decimal("0.15")).quantize(Decimal("0.01"))
    coop_fee = (gross * Decimal("0.15")).quantize(Decimal("0.01"))
    worker_payout = (gross * Decimal("0.70")).quantize(Decimal("0.01"))
    return {
        "gross": gross,
        "platform_fee": platform_fee,
        "coop_fee": coop_fee,
        "worker_payout": worker_payout,
    }
