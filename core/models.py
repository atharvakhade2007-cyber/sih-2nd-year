import uuid
import math
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from django.utils import timezone


# ---------------------------------------------------------------------------
# Haversine distance helper (used for geo-matching workers to bookings)
# ---------------------------------------------------------------------------
def haversine_km(lat1, lon1, lat2, lon2):
    """
    Returns the great-circle distance in kilometres between two GPS points
    using the Haversine formula.
    """
    if any(v is None for v in [lat1, lon1, lat2, lon2]):
        return 0.0  # treat as zero distance when coords missing (show all jobs)
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lon2 - lon1)
    a = math.sin(d_phi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ---------------------------------------------------------------------------
# 1. CustomUser
# ---------------------------------------------------------------------------
class CustomUser(AbstractUser):
    """
    Custom User Model extending AbstractUser for KaamConnect Platform.
    Supports role-based access control for Customers, Service Providers,
    Cooperative Administrators, and Platform Administrators.
    """

    class Role(models.TextChoices):
        CUSTOMER = "CUSTOMER", _("Customer")
        PROVIDER = "PROVIDER", _("Service Provider")
        COOP_ADMIN = "COOP_ADMIN", _("Cooperative Administrator")
        PLATFORM_ADMIN = "PLATFORM_ADMIN", _("Platform Administrator")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(_("email address"), unique=True, db_index=True)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.CUSTOMER,
        db_index=True,
        help_text=_("Designates the role of the user within the platform."),
    )
    phone_number = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        db_index=True,
        help_text=_("Contact phone number."),
    )
    profile_picture = models.ImageField(
        upload_to="profile_pics/",
        blank=True,
        null=True,
        help_text=_("User profile image."),
    )
    bio = models.TextField(blank=True, help_text=_("Short bio or user description."))
    city = models.CharField(max_length=100, blank=True, help_text=_("City of residence."))
    pincode = models.CharField(max_length=10, blank=True, help_text=_("PIN / ZIP code."))
    latitude = models.FloatField(
        null=True, blank=True, help_text=_("GPS latitude for proximity-based matching.")
    )
    longitude = models.FloatField(
        null=True, blank=True, help_text=_("GPS longitude for proximity-based matching.")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    REQUIRED_FIELDS = ["email", "role"]

    class Meta:
        verbose_name = _("User")
        verbose_name_plural = _("Users")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["role", "is_active"]),
            models.Index(fields=["email"]),
        ]

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    @property
    def is_provider(self):
        return self.role == self.Role.PROVIDER

    @property
    def is_coop_admin(self):
        return self.role == self.Role.COOP_ADMIN

    @property
    def is_customer(self):
        return self.role == self.Role.CUSTOMER


# ---------------------------------------------------------------------------
# 2. WorkerProfile
# ---------------------------------------------------------------------------
class WorkerProfile(models.Model):
    """
    Profile extension for users registered as Service Providers (Workers).
    Tracks skill sets, availability status, cooperative verification status,
    ratings, geographic location, and membership info.
    """

    class AvailabilityStatus(models.TextChoices):
        AVAILABLE = "AVAILABLE", _("Available")
        BUSY = "BUSY", _("Busy")
        OFFLINE = "OFFLINE", _("Offline")

    class VerificationStatus(models.TextChoices):
        PENDING = "PENDING", _("Pending Verification")
        VERIFIED = "VERIFIED", _("Verified")
        REJECTED = "REJECTED", _("Rejected")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name="worker_profile",
        limit_choices_to={"role": CustomUser.Role.PROVIDER},
    )
    coop_member_id = models.CharField(
        max_length=50,
        unique=True,
        blank=True,
        null=True,
        help_text=_("Cooperative membership identifier code."),
    )
    # Skills stored as list of ServiceCategory slugs, e.g. ["plumbing", "electrical"]
    skills = models.JSONField(
        default=list,
        help_text=_("List of ServiceCategory slugs this worker is skilled in."),
    )
    availability_status = models.CharField(
        max_length=20,
        choices=AvailabilityStatus.choices,
        default=AvailabilityStatus.OFFLINE,
        db_index=True,
    )
    verification_status = models.CharField(
        max_length=20,
        choices=VerificationStatus.choices,
        default=VerificationStatus.PENDING,
        db_index=True,
    )
    hourly_rate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0.00)],
        help_text=_("Base hourly rate for services rendered."),
    )
    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0.00), MaxValueValidator(5.00)],
        db_index=True,
        help_text=_("Average rating out of 5.00."),
    )
    total_reviews_count = models.PositiveIntegerField(default=0)
    service_radius_km = models.PositiveIntegerField(
        default=10,
        help_text=_("Maximum service coverage distance in kilometers."),
    )
    latitude = models.FloatField(
        null=True, blank=True, help_text=_("Worker's home/base GPS latitude.")
    )
    longitude = models.FloatField(
        null=True, blank=True, help_text=_("Worker's home/base GPS longitude.")
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Worker Profile")
        verbose_name_plural = _("Worker Profiles")
        ordering = ["-rating", "-total_reviews_count"]
        indexes = [
            models.Index(fields=["availability_status", "verification_status"]),
            models.Index(fields=["rating"]),
        ]

    def __str__(self):
        return f"Worker: {self.user.get_full_name() or self.user.username} [{self.get_verification_status_display()}]"

    def distance_to(self, lat, lon):
        """Returns distance in km from worker base to a given point."""
        return haversine_km(self.latitude, self.longitude, lat, lon)


# ---------------------------------------------------------------------------
# 3. ServiceCategory
# ---------------------------------------------------------------------------
class ServiceCategory(models.Model):
    """
    Taxonomy for grouping related gig services (e.g. Home Care, Repair, Maintenance).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=100, unique=True, db_index=True)
    slug = models.SlugField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text=_("Icon or CSS class identifier."))

    class Meta:
        verbose_name = _("Service Category")
        verbose_name_plural = _("Service Categories")
        ordering = ["name"]

    def __str__(self):
        return self.name


# ---------------------------------------------------------------------------
# 4. Service
# ---------------------------------------------------------------------------
class Service(models.Model):
    """
    Catalogue of services provided by the cooperative.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200, db_index=True)
    slug = models.SlugField(max_length=200, unique=True)
    category = models.ForeignKey(
        ServiceCategory,
        on_delete=models.PROTECT,
        related_name="services",
        help_text=_("Category under which this service falls."),
    )
    description = models.TextField()
    base_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.00)],
        db_index=True,
        help_text=_("Standard starting price in INR."),
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text=_("Whether service is available for booking."),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Service")
        verbose_name_plural = _("Services")
        ordering = ["title"]
        indexes = [
            models.Index(fields=["category", "is_active"]),
            models.Index(fields=["base_price"]),
        ]

    def __str__(self):
        return f"{self.title} - ₹{self.base_price}"


# ---------------------------------------------------------------------------
# 5. Booking
# ---------------------------------------------------------------------------
class Booking(models.Model):
    """
    Core transactional record representing a service booking request.
    Worker assignment is FIRST-COME, FIRST-SERVED from a geo-filtered pool.
    """

    class BookingStatus(models.TextChoices):
        PENDING = "PENDING", _("Pending")
        ACCEPTED = "ACCEPTED", _("Accepted")
        IN_PROGRESS = "IN_PROGRESS", _("In Progress")
        COMPLETED = "COMPLETED", _("Completed")
        CANCELLED = "CANCELLED", _("Cancelled")

    class PaymentStatus(models.TextChoices):
        UNPAID = "UNPAID", _("Unpaid")
        PAID = "PAID", _("Paid")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name="customer_bookings",
        limit_choices_to={"role": CustomUser.Role.CUSTOMER},
    )
    # Worker is NULL until a worker accepts (first-come, first-served)
    worker = models.ForeignKey(
        WorkerProfile,
        on_delete=models.PROTECT,
        related_name="worker_bookings",
        null=True,
        blank=True,
    )
    service = models.ForeignKey(
        Service,
        on_delete=models.PROTECT,
        related_name="bookings",
    )
    scheduled_time = models.DateTimeField(db_index=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    job_accepted_at = models.DateTimeField(null=True, blank=True, help_text=_("Timestamp when a worker accepted the job."))
    status = models.CharField(
        max_length=20,
        choices=BookingStatus.choices,
        default=BookingStatus.PENDING,
        db_index=True,
    )
    payment_status = models.CharField(
        max_length=10,
        choices=PaymentStatus.choices,
        default=PaymentStatus.UNPAID,
        db_index=True,
    )
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.00)],
        help_text=_("Total agreed transaction cost for the service."),
    )
    service_address = models.TextField(help_text=_("Location where service is to be rendered."))
    special_instructions = models.TextField(blank=True)
    # Customer GPS at time of booking (for geo-matching workers)
    customer_latitude = models.FloatField(null=True, blank=True)
    customer_longitude = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Booking")
        verbose_name_plural = _("Bookings")
        ordering = ["-scheduled_time"]
        indexes = [
            models.Index(fields=["customer", "status"]),
            models.Index(fields=["worker", "status"]),
            models.Index(fields=["scheduled_time"]),
            models.Index(fields=["status"]),
            models.Index(fields=["payment_status"]),
        ]

    def __str__(self):
        return f"Booking #{str(self.id)[:8]} — {self.service.title} ({self.get_status_display()})"

    @property
    def status_step(self):
        """Returns 1-4 integer for step-tracker UI progress."""
        step_map = {
            self.BookingStatus.PENDING: 1,
            self.BookingStatus.ACCEPTED: 2,
            self.BookingStatus.IN_PROGRESS: 3,
            self.BookingStatus.COMPLETED: 4,
        }
        return step_map.get(self.status, 1)

    @property
    def platform_fee(self):
        return round(self.total_amount * 15 / 100, 2)

    @property
    def coop_fee(self):
        return round(self.total_amount * 15 / 100, 2)

    @property
    def worker_earning(self):
        return round(self.total_amount * 70 / 100, 2)


# ---------------------------------------------------------------------------
# 6. CoopEarning
# ---------------------------------------------------------------------------
class CoopEarning(models.Model):
    """
    Financial breakdown ledger for each completed booking.
    Split: Platform 15% | Coop 15% | Worker 70%.
    """

    class PayoutStatus(models.TextChoices):
        PENDING = "PENDING", _("Pending Distribution")
        PROCESSING = "PROCESSING", _("Processing")
        PAID = "PAID", _("Paid Out")
        RETAINED = "RETAINED", _("Retained in Dividend Pool")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.OneToOneField(
        Booking,
        on_delete=models.PROTECT,
        related_name="earning_record",
    )
    worker = models.ForeignKey(
        WorkerProfile,
        on_delete=models.PROTECT,
        related_name="coop_earnings",
    )
    gross_amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.00)])
    commission_fee = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.00)])
    coop_dividend_pool = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.00)])
    worker_payout = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.00)])
    payout_status = models.CharField(
        max_length=20,
        choices=PayoutStatus.choices,
        default=PayoutStatus.PENDING,
        db_index=True,
    )
    payout_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Coop Earning Record")
        verbose_name_plural = _("Coop Earning Records")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["worker", "payout_status"]),
            models.Index(fields=["payout_status"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return f"Earning for #{str(self.booking.id)[:8]} — Payout: ₹{self.worker_payout}"


# ---------------------------------------------------------------------------
# 7. Review
# ---------------------------------------------------------------------------
class Review(models.Model):
    """
    Post-completion customer review for a worker on a specific booking.
    Stored separately for history; triggers WorkerProfile.rating recalculation.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.OneToOneField(
        Booking,
        on_delete=models.PROTECT,
        related_name="review",
        help_text=_("Each completed booking can have exactly one review."),
    )
    customer = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name="given_reviews",
        limit_choices_to={"role": CustomUser.Role.CUSTOMER},
    )
    worker = models.ForeignKey(
        WorkerProfile,
        on_delete=models.PROTECT,
        related_name="received_reviews",
    )
    rating = models.PositiveSmallIntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text=_("Rating from 1 (worst) to 5 (best)."),
    )
    comment = models.TextField(blank=True, help_text=_("Optional written feedback."))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Review")
        verbose_name_plural = _("Reviews")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["worker"]),
            models.Index(fields=["customer"]),
        ]

    def __str__(self):
        return f"Review by {self.customer.username} → {self.worker.user.username} ({self.rating}★)"


# ---------------------------------------------------------------------------
# 8. Payment
# ---------------------------------------------------------------------------
class Payment(models.Model):
    """
    Simulated payment record linked to a completed booking.
    In production this would store a real gateway transaction ID.
    """

    class Status(models.TextChoices):
        PENDING = "PENDING", _("Pending")
        COMPLETED = "COMPLETED", _("Completed")
        FAILED = "FAILED", _("Failed")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    booking = models.OneToOneField(
        Booking,
        on_delete=models.PROTECT,
        related_name="payment",
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.00)])
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    transaction_ref = models.UUIDField(
        default=uuid.uuid4,
        unique=True,
        help_text=_("Simulated unique transaction reference."),
    )
    paid_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Payment")
        verbose_name_plural = _("Payments")
        ordering = ["-created_at"]

    def __str__(self):
        return f"Payment {str(self.transaction_ref)[:8]} — ₹{self.amount} ({self.get_status_display()})"


# ---------------------------------------------------------------------------
# 9. JobPosting (Marketplace)
# ---------------------------------------------------------------------------
class JobPosting(models.Model):
    """
    Customer-created custom job request posted to the marketplace.
    Workers within the relevant category and radius can express interest.
    """

    class PostingStatus(models.TextChoices):
        OPEN = "OPEN", _("Open")
        ASSIGNED = "ASSIGNED", _("Assigned")
        CLOSED = "CLOSED", _("Closed")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name="job_postings",
        limit_choices_to={"role": CustomUser.Role.CUSTOMER},
    )
    category = models.ForeignKey(
        ServiceCategory,
        on_delete=models.PROTECT,
        related_name="job_postings",
    )
    title = models.CharField(max_length=200)
    description = models.TextField()
    preferred_date = models.DateField(null=True, blank=True)
    budget_estimate = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0.00)],
    )
    service_address = models.TextField(blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    status = models.CharField(
        max_length=20,
        choices=PostingStatus.choices,
        default=PostingStatus.OPEN,
        db_index=True,
    )
    assigned_worker = models.ForeignKey(
        WorkerProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_postings",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = _("Job Posting")
        verbose_name_plural = _("Job Postings")
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["category", "status"]),
        ]

    def __str__(self):
        return f"Job: {self.title} by {self.customer.username} [{self.get_status_display()}]"


# ---------------------------------------------------------------------------
# 10. JobInterest
# ---------------------------------------------------------------------------
class JobInterest(models.Model):
    """
    A worker's expression of interest in a marketplace JobPosting.
    Customer reviews interested workers and selects one.
    """

    class InterestStatus(models.TextChoices):
        PENDING = "PENDING", _("Pending Review")
        SELECTED = "SELECTED", _("Selected")
        REJECTED = "REJECTED", _("Rejected")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    posting = models.ForeignKey(
        JobPosting,
        on_delete=models.CASCADE,
        related_name="interests",
    )
    worker = models.ForeignKey(
        WorkerProfile,
        on_delete=models.CASCADE,
        related_name="job_interests",
    )
    status = models.CharField(
        max_length=20,
        choices=InterestStatus.choices,
        default=InterestStatus.PENDING,
        db_index=True,
    )
    message = models.TextField(blank=True, help_text=_("Optional note from worker."))
    expressed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = _("Job Interest")
        verbose_name_plural = _("Job Interests")
        ordering = ["expressed_at"]
        # One worker can only express interest once per posting
        unique_together = [("posting", "worker")]
        indexes = [
            models.Index(fields=["posting", "status"]),
        ]

    def __str__(self):
        return f"{self.worker.user.username} → {self.posting.title} [{self.get_status_display()}]"
