import logging
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.db.models import Avg, Count

from .models import Review, Booking, CoopEarning, WorkerProfile

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Auto-recalculate WorkerProfile.rating when a Review is saved or deleted
# ---------------------------------------------------------------------------
@receiver(post_save, sender=Review)
def update_worker_rating_on_review_save(sender, instance, created, **kwargs):
    """Recalculate the worker's average rating and review count after each review."""
    worker_profile = instance.worker
    agg = Review.objects.filter(worker=worker_profile).aggregate(
        avg_rating=Avg("rating"),
        count=Count("id"),
    )
    worker_profile.rating = round(agg["avg_rating"] or 0, 2)
    worker_profile.total_reviews_count = agg["count"] or 0
    worker_profile.save(update_fields=["rating", "total_reviews_count", "updated_at"])
    logger.info(
        "Worker %s rating updated: %.2f (%d reviews)",
        worker_profile.user.username,
        worker_profile.rating,
        worker_profile.total_reviews_count,
    )


# ---------------------------------------------------------------------------
# Auto-create CoopEarning record when Booking status changes to COMPLETED
# ---------------------------------------------------------------------------
@receiver(pre_save, sender=Booking)
def create_earning_on_booking_complete(sender, instance, **kwargs):
    """
    If a booking is being transitioned to COMPLETED and has no earning record yet,
    create one automatically. Uses pre_save to detect the status change.
    """
    if not instance.pk:
        return  # new booking, not yet saved

    try:
        old = Booking.objects.get(pk=instance.pk)
    except Booking.DoesNotExist:
        return

    if old.status == instance.status:
        return  # status unchanged

    if instance.status != Booking.BookingStatus.COMPLETED:
        return  # not transitioning to COMPLETED

    if not instance.worker:
        return  # no worker assigned

    # Create earning record (get_or_create for safety)
    gross = instance.total_amount
    platform_fee = round(gross * 15 / 100, 2)
    coop_div = round(gross * 15 / 100, 2)
    worker_pay = round(gross * 70 / 100, 2)

    CoopEarning.objects.get_or_create(
        booking=instance,
        defaults={
            "worker": instance.worker,
            "gross_amount": gross,
            "commission_fee": platform_fee,
            "coop_dividend_pool": coop_div,
            "worker_payout": worker_pay,
        },
    )
    logger.info(
        "CoopEarning created for booking %s: gross=₹%.2f, worker_payout=₹%.2f",
        str(instance.pk)[:8],
        gross,
        worker_pay,
    )
