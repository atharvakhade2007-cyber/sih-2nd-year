import uuid
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _


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


class WorkerProfile(models.Model):
    """
    Profile extension for users registered as Service Providers (Workers).
    Tracks skill sets, availability status, cooperative verification status,
    ratings, and membership info.
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
    skills = models.JSONField(
        default=list,
        help_text=_("List of skill tags or categories (e.g. ['Plumbing', 'Electrical'])."),
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
        return f"Worker Profile: {self.user.get_full_name() or self.user.username} [{self.get_verification_status_display()}]"


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
        help_text=_("Standard starting price in INR/local currency."),
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


class Booking(models.Model):
    """
    Core transactional record representing a service booking request between
    a Customer and a Worker.
    """

    class BookingStatus(models.TextChoices):
        PENDING = "PENDING", _("Pending")
        ACCEPTED = "ACCEPTED", _("Accepted")
        IN_PROGRESS = "IN_PROGRESS", _("In Progress")
        COMPLETED = "COMPLETED", _("Completed")
        CANCELLED = "CANCELLED", _("Cancelled")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(
        CustomUser,
        on_delete=models.PROTECT,
        related_name="customer_bookings",
        limit_choices_to={"role": CustomUser.Role.CUSTOMER},
    )
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
    status = models.CharField(
        max_length=20,
        choices=BookingStatus.choices,
        default=BookingStatus.PENDING,
        db_index=True,
    )
    total_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.00)],
        help_text=_("Total agreed transaction cost for the service."),
    )
    service_address = models.TextField(help_text=_("Location where service is to be rendered."))
    special_instructions = models.TextField(blank=True, help_text=_("Customer instructions or notes."))
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
        ]

    def __str__(self):
        return f"Booking #{str(self.id)[:8]} - {self.service.title} ({self.get_status_display()})"


class CoopEarning(models.Model):
    """
    Financial breakdown ledger logging payouts, platform/cooperative commission fees,
    and dividend allocations for each completed service booking.
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
    gross_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.00)],
        help_text=_("Total revenue collected from booking."),
    )
    commission_fee = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.00)],
        help_text=_("Platform operation & maintenance commission fee."),
    )
    coop_dividend_pool = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.00)],
        help_text=_("Amount funneled to cooperative member dividend pool for profit distribution."),
    )
    worker_payout = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.00)],
        help_text=_("Net direct payout to service provider."),
    )
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
        return f"Coop Earning for Booking #{str(self.booking.id)[:8]} - Payout: ₹{self.worker_payout}"
