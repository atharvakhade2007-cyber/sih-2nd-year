import logging
from functools import wraps
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.http import HttpResponseForbidden, JsonResponse
from django.views.decorators.http import require_POST
from django.db import transaction
from django.db.models import Sum, Count, Q, Avg
from django.utils import timezone
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import (
    CustomUser, WorkerProfile, ServiceCategory, Service,
    Booking, CoopEarning, Review, Payment, JobPosting, JobInterest,
    haversine_km,
)

logger = logging.getLogger(__name__)


# =============================================================================
# HELPERS
# =============================================================================

def role_required(*allowed_roles):
    """Decorator enforcing role-based access."""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            if request.user.role not in allowed_roles and not request.user.is_superuser:
                messages.error(request, "You are not authorized to access this page.")
                return HttpResponseForbidden("Access Denied: Insufficient Role Permissions")
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def smart_redirect_by_role(user):
    """Returns a redirect response appropriate for the user's role."""
    if user.role == CustomUser.Role.PROVIDER:
        return redirect('core:worker_dashboard')
    if user.role in (CustomUser.Role.COOP_ADMIN, CustomUser.Role.PLATFORM_ADMIN):
        return redirect('core:coop_admin_dashboard')
    return redirect('core:customer_dashboard')


def get_available_bookings_for_worker(worker_profile):
    """
    Returns queryset of PENDING, unassigned bookings that:
      1. Match the worker's skills (by ServiceCategory slug)
      2. Are within the worker's service_radius_km (Haversine formula)
    If worker has no skills set, returns all unassigned pending bookings.
    """
    pending = Booking.objects.filter(
        status=Booking.BookingStatus.PENDING,
        worker__isnull=True,
    ).select_related('service__category', 'customer').order_by('scheduled_time')

    # Filter by category skill match
    if worker_profile.skills:
        pending = pending.filter(service__category__slug__in=worker_profile.skills)

    # Filter by geographic radius in Python (SQLite doesn't support geo queries)
    if worker_profile.latitude and worker_profile.longitude:
        filtered = []
        for booking in pending:
            dist = haversine_km(
                worker_profile.latitude, worker_profile.longitude,
                booking.customer_latitude, booking.customer_longitude,
            )
            if dist <= worker_profile.service_radius_km:
                filtered.append(booking)
        return filtered

    return list(pending)


def _create_earning_record(booking):
    """Creates a CoopEarning record when a booking is COMPLETED."""
    gross = booking.total_amount
    platform_fee = round(gross * 15 / 100, 2)
    coop_div = round(gross * 15 / 100, 2)
    worker_pay = round(gross * 70 / 100, 2)
    CoopEarning.objects.get_or_create(
        booking=booking,
        defaults=dict(
            worker=booking.worker,
            gross_amount=gross,
            commission_fee=platform_fee,
            coop_dividend_pool=coop_div,
            worker_payout=worker_pay,
        )
    )


# =============================================================================
# AUTH — Login / Logout / Register
# =============================================================================

def login_view(request):
    """Custom login view with role-based redirect."""
    if request.user.is_authenticated:
        return smart_redirect_by_role(request.user)

    form = AuthenticationForm(data=request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"Welcome back, {user.get_full_name() or user.username}!")
            return smart_redirect_by_role(user)
        else:
            messages.error(request, "Invalid username or password. Please try again.")

    return render(request, 'registration/login.html', {'form': form})


def logout_view(request):
    """Logout and redirect to home."""
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect('core:service_list')


def register_customer_view(request):
    """Customer registration — creates CustomUser with CUSTOMER role."""
    if request.user.is_authenticated:
        return smart_redirect_by_role(request.user)

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        phone = request.POST.get('phone_number', '').strip()
        city = request.POST.get('city', '').strip()
        pincode = request.POST.get('pincode', '').strip()
        lat = request.POST.get('latitude', '').strip() or None
        lon = request.POST.get('longitude', '').strip() or None
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')

        errors = []
        if not username:
            errors.append("Username is required.")
        if CustomUser.objects.filter(username=username).exists():
            errors.append("Username already taken.")
        if not email:
            errors.append("Email is required.")
        if CustomUser.objects.filter(email=email).exists():
            errors.append("Email already registered.")
        if password1 != password2:
            errors.append("Passwords do not match.")
        try:
            validate_password(password1)
        except ValidationError as e:
            errors.extend(e.messages)

        if errors:
            for err in errors:
                messages.error(request, err)
            return render(request, 'registration/register.html', {'post_data': request.POST})

        user = CustomUser.objects.create_user(
            username=username,
            email=email,
            password=password1,
            first_name=first_name,
            last_name=last_name,
            phone_number=phone or None,
            city=city,
            pincode=pincode,
            latitude=float(lat) if lat else None,
            longitude=float(lon) if lon else None,
            role=CustomUser.Role.CUSTOMER,
        )
        login(request, user)
        messages.success(request, f"Welcome to KaamConnect, {user.get_full_name() or user.username}!")
        return redirect('core:customer_dashboard')

    return render(request, 'registration/register.html', {})


def register_worker_view(request):
    """Worker registration — creates CustomUser + WorkerProfile (PENDING verification)."""
    if request.user.is_authenticated:
        return smart_redirect_by_role(request.user)

    categories = ServiceCategory.objects.all()

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        phone = request.POST.get('phone_number', '').strip()
        city = request.POST.get('city', '').strip()
        pincode = request.POST.get('pincode', '').strip()
        lat = request.POST.get('latitude', '').strip() or None
        lon = request.POST.get('longitude', '').strip() or None
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')
        skills = request.POST.getlist('skills')  # list of category slugs
        service_radius = request.POST.get('service_radius_km', '10').strip()
        hourly_rate = request.POST.get('hourly_rate', '').strip() or None
        coop_member_id = request.POST.get('coop_member_id', '').strip() or None

        errors = []
        if not username:
            errors.append("Username is required.")
        if CustomUser.objects.filter(username=username).exists():
            errors.append("Username already taken.")
        if not email:
            errors.append("Email is required.")
        if CustomUser.objects.filter(email=email).exists():
            errors.append("Email already registered.")
        if password1 != password2:
            errors.append("Passwords do not match.")
        if not skills:
            errors.append("Please select at least one skill/service category.")
        try:
            validate_password(password1)
        except ValidationError as e:
            errors.extend(e.messages)

        if errors:
            for err in errors:
                messages.error(request, err)
            return render(request, 'registration/worker_register.html', {
                'categories': categories,
                'post_data': request.POST,
            })

        with transaction.atomic():
            user = CustomUser.objects.create_user(
                username=username,
                email=email,
                password=password1,
                first_name=first_name,
                last_name=last_name,
                phone_number=phone or None,
                city=city,
                pincode=pincode,
                latitude=float(lat) if lat else None,
                longitude=float(lon) if lon else None,
                role=CustomUser.Role.PROVIDER,
            )
            WorkerProfile.objects.create(
                user=user,
                skills=skills,
                service_radius_km=int(service_radius) if service_radius.isdigit() else 10,
                hourly_rate=float(hourly_rate) if hourly_rate else None,
                coop_member_id=coop_member_id,
                verification_status=WorkerProfile.VerificationStatus.PENDING,
                availability_status=WorkerProfile.AvailabilityStatus.OFFLINE,
                latitude=float(lat) if lat else None,
                longitude=float(lon) if lon else None,
            )

        messages.success(request, "Registration submitted! Your account is pending admin verification.")
        return render(request, 'registration/worker_register_success.html', {'username': username})

    return render(request, 'registration/worker_register.html', {'categories': categories})


# =============================================================================
# PUBLIC — Service Listing
# =============================================================================

def service_list_view(request):
    """Renders all active services. Supports category filter & text search."""
    category_slug = request.GET.get('category')
    search_query = request.GET.get('q', '').strip()

    services = Service.objects.filter(is_active=True).select_related('category')
    categories = ServiceCategory.objects.all()

    if category_slug:
        services = services.filter(category__slug=category_slug)
    if search_query:
        services = services.filter(
            Q(title__icontains=search_query) | Q(description__icontains=search_query)
        )

    context = {
        'services': services,
        'categories': categories,
        'selected_category': category_slug,
        'search_query': search_query,
    }
    return render(request, 'core/service_list.html', context)


# =============================================================================
# CUSTOMER VIEWS
# =============================================================================

@login_required
@role_required(CustomUser.Role.CUSTOMER)
def customer_dashboard_view(request):
    """Customer's personal dashboard: booking history with step-tracker."""
    bookings = Booking.objects.filter(
        customer=request.user
    ).select_related('service__category', 'worker__user').prefetch_related('review').order_by('-created_at')

    active_bookings = bookings.filter(status__in=[
        Booking.BookingStatus.PENDING,
        Booking.BookingStatus.ACCEPTED,
        Booking.BookingStatus.IN_PROGRESS,
    ])
    completed_bookings = bookings.filter(status=Booking.BookingStatus.COMPLETED)
    cancelled_bookings = bookings.filter(status=Booking.BookingStatus.CANCELLED)

    total_spent = completed_bookings.filter(
        payment_status=Booking.PaymentStatus.PAID
    ).aggregate(total=Sum('total_amount'))['total'] or 0

    context = {
        'active_bookings': active_bookings,
        'completed_bookings': completed_bookings,
        'cancelled_bookings': cancelled_bookings,
        'total_spent': total_spent,
        'total_bookings': bookings.count(),
        'completed_count': completed_bookings.count(),
    }
    return render(request, 'core/customer_dashboard.html', context)


@login_required
@role_required(CustomUser.Role.CUSTOMER)
def booking_create_view(request, service_id):
    """
    Customer books a service. Worker field is left NULL (first-come, first-served).
    Captures customer GPS at booking time for geo-matching.
    """
    service = get_object_or_404(Service, id=service_id, is_active=True)

    if request.method == 'POST':
        scheduled_time_str = request.POST.get('scheduled_time')
        service_address = request.POST.get('service_address', '').strip()
        special_instructions = request.POST.get('special_instructions', '').strip()
        lat = request.POST.get('latitude', '').strip() or None
        lon = request.POST.get('longitude', '').strip() or None

        if not scheduled_time_str or not service_address:
            messages.error(request, "Please fill in all required fields (Scheduled Time & Address).")
            return render(request, 'core/booking_create.html', {'service': service})

        booking = Booking.objects.create(
            customer=request.user,
            service=service,
            scheduled_time=scheduled_time_str,
            total_amount=service.base_price,
            service_address=service_address,
            special_instructions=special_instructions,
            customer_latitude=float(lat) if lat else request.user.latitude,
            customer_longitude=float(lon) if lon else request.user.longitude,
            status=Booking.BookingStatus.PENDING,
            payment_status=Booking.PaymentStatus.UNPAID,
        )
        messages.success(request, f"Booking submitted! A worker will accept your job shortly.")
        return redirect('core:booking_detail', booking_id=booking.id)

    context = {'service': service}
    return render(request, 'core/booking_create.html', context)


@login_required
@role_required(CustomUser.Role.CUSTOMER)
def booking_detail_view(request, booking_id):
    """Customer views their booking status, step-tracker, payment, and review options."""
    booking = get_object_or_404(Booking, id=booking_id, customer=request.user)
    has_review = hasattr(booking, 'review')
    has_payment = hasattr(booking, 'payment') and booking.payment.status == Payment.Status.COMPLETED

    context = {
        'booking': booking,
        'has_review': has_review,
        'has_payment': has_payment,
    }
    return render(request, 'core/booking_detail.html', context)


@login_required
@role_required(CustomUser.Role.CUSTOMER)
@require_POST
def booking_cancel_view(request, booking_id):
    """Customer cancels a PENDING booking."""
    booking = get_object_or_404(Booking, id=booking_id, customer=request.user)
    if booking.status != Booking.BookingStatus.PENDING:
        messages.error(request, "Only PENDING bookings can be cancelled.")
        return redirect('core:booking_detail', booking_id=booking.id)

    booking.status = Booking.BookingStatus.CANCELLED
    booking.save(update_fields=['status', 'updated_at'])
    messages.success(request, "Your booking has been cancelled.")
    return redirect('core:customer_dashboard')


@login_required
@role_required(CustomUser.Role.CUSTOMER)
def payment_view(request, booking_id):
    """
    Simulated payment checkout and processing.
    GET: shows checkout page. POST: processes simulated payment.
    """
    booking = get_object_or_404(Booking, id=booking_id, customer=request.user)

    if booking.status != Booking.BookingStatus.ACCEPTED:
        messages.error(request, "Payment is only available for ACCEPTED bookings.")
        return redirect('core:booking_detail', booking_id=booking.id)

    if booking.payment_status == Booking.PaymentStatus.PAID:
        messages.info(request, "This booking has already been paid.")
        return redirect('core:payment_receipt', booking_id=booking.id)

    if request.method == 'POST':
        with transaction.atomic():
            payment = Payment.objects.create(
                booking=booking,
                amount=booking.total_amount,
                status=Payment.Status.COMPLETED,
                paid_at=timezone.now(),
            )
            booking.payment_status = Booking.PaymentStatus.PAID
            booking.save(update_fields=['payment_status', 'updated_at'])

        messages.success(request, "Payment successful! Thank you for using KaamConnect.")
        return redirect('core:payment_receipt', booking_id=booking.id)

    context = {'booking': booking}
    return render(request, 'core/payment_checkout.html', context)


@login_required
@role_required(CustomUser.Role.CUSTOMER)
def payment_receipt_view(request, booking_id):
    """Shows the payment receipt for a paid booking."""
    booking = get_object_or_404(Booking, id=booking_id, customer=request.user)
    payment = get_object_or_404(Payment, booking=booking, status=Payment.Status.COMPLETED)
    context = {'booking': booking, 'payment': payment}
    return render(request, 'core/payment_receipt.html', context)


@login_required
@role_required(CustomUser.Role.CUSTOMER)
def review_create_view(request, booking_id):
    """Customer leaves a star rating + comment for a COMPLETED booking."""
    booking = get_object_or_404(Booking, id=booking_id, customer=request.user)

    if booking.status != Booking.BookingStatus.COMPLETED:
        messages.error(request, "Reviews can only be left for completed bookings.")
        return redirect('core:booking_detail', booking_id=booking.id)

    if hasattr(booking, 'review'):
        messages.info(request, "You have already reviewed this booking.")
        return redirect('core:booking_detail', booking_id=booking.id)

    if not booking.worker:
        messages.error(request, "Cannot review a booking with no assigned worker.")
        return redirect('core:booking_detail', booking_id=booking.id)

    if request.method == 'POST':
        try:
            rating = int(request.POST.get('rating', 0))
        except (ValueError, TypeError):
            rating = 0

        comment = request.POST.get('comment', '').strip()

        if not (1 <= rating <= 5):
            messages.error(request, "Please select a rating between 1 and 5.")
            return render(request, 'core/review_create.html', {'booking': booking})

        with transaction.atomic():
            Review.objects.create(
                booking=booking,
                customer=request.user,
                worker=booking.worker,
                rating=rating,
                comment=comment,
            )
            # Recalculate worker's average rating
            worker_profile = booking.worker
            agg = Review.objects.filter(worker=worker_profile).aggregate(
                avg_rating=Avg('rating'), count=Count('id')
            )
            worker_profile.rating = round(agg['avg_rating'] or 0, 2)
            worker_profile.total_reviews_count = agg['count'] or 0
            worker_profile.save(update_fields=['rating', 'total_reviews_count', 'updated_at'])

        messages.success(request, "Thank you! Your review has been submitted.")
        return redirect('core:booking_detail', booking_id=booking.id)

    return render(request, 'core/review_create.html', {'booking': booking})


# =============================================================================
# WORKER VIEWS
# =============================================================================

@login_required
@role_required(CustomUser.Role.PROVIDER)
def worker_dashboard_view(request):
    """Worker's main dashboard: availability toggle + active/completed jobs."""
    try:
        worker_profile = request.user.worker_profile
    except WorkerProfile.DoesNotExist:
        messages.error(request, "Worker profile not found. Please contact support.")
        return redirect('core:service_list')

    # Handle availability toggle
    if request.method == 'POST' and 'toggle_status' in request.POST:
        new_status = request.POST.get('availability_status')
        if new_status in WorkerProfile.AvailabilityStatus.values:
            worker_profile.availability_status = new_status
            worker_profile.save(update_fields=['availability_status', 'updated_at'])
            messages.success(request, f"Status updated to '{worker_profile.get_availability_status_display()}'.")
        else:
            messages.error(request, "Invalid status.")
        return redirect('core:worker_dashboard')

    my_bookings = Booking.objects.filter(
        worker=worker_profile
    ).select_related('customer', 'service__category').order_by('-scheduled_time')

    active_jobs = my_bookings.filter(status__in=[
        Booking.BookingStatus.ACCEPTED,
        Booking.BookingStatus.IN_PROGRESS,
    ])
    completed_jobs = my_bookings.filter(status=Booking.BookingStatus.COMPLETED)

    earnings = CoopEarning.objects.filter(worker=worker_profile).aggregate(
        total_payout=Sum('worker_payout'),
        pending_payout=Sum('worker_payout', filter=Q(payout_status=CoopEarning.PayoutStatus.PENDING)),
    )

    # Available job pool (geo + skill matched)
    available_jobs = get_available_bookings_for_worker(worker_profile)

    context = {
        'worker_profile': worker_profile,
        'availability_choices': WorkerProfile.AvailabilityStatus.choices,
        'active_jobs': active_jobs,
        'completed_jobs': completed_jobs,
        'available_jobs': available_jobs,
        'total_payout': earnings['total_payout'] or 0,
        'pending_payout': earnings['pending_payout'] or 0,
        'total_jobs_done': completed_jobs.count(),
    }
    return render(request, 'core/worker_dashboard.html', context)


@login_required
@role_required(CustomUser.Role.PROVIDER)
@require_POST
def booking_action_view(request, booking_id):
    """
    Worker state-machine transitions:
      accept  → PENDING → ACCEPTED (first-come, first-served with DB lock)
      start   → ACCEPTED → IN_PROGRESS
      complete→ IN_PROGRESS → COMPLETED (creates CoopEarning)
    """
    try:
        worker_profile = request.user.worker_profile
    except WorkerProfile.DoesNotExist:
        messages.error(request, "Worker profile not found.")
        return redirect('core:worker_dashboard')

    action = request.POST.get('action')

    try:
        with transaction.atomic():
            # Lock the row to prevent race conditions on accept
            booking = Booking.objects.select_for_update().get(id=booking_id)

            if action == 'accept':
                if booking.status != Booking.BookingStatus.PENDING or booking.worker is not None:
                    messages.warning(request, "Sorry, this job has already been taken by another worker.")
                    return redirect('core:worker_dashboard')
                if worker_profile.verification_status != WorkerProfile.VerificationStatus.VERIFIED:
                    messages.error(request, "Only verified workers can accept jobs.")
                    return redirect('core:worker_dashboard')
                booking.worker = worker_profile
                booking.status = Booking.BookingStatus.ACCEPTED
                booking.job_accepted_at = timezone.now()
                booking.save(update_fields=['worker', 'status', 'job_accepted_at', 'updated_at'])
                # Mark worker as busy
                worker_profile.availability_status = WorkerProfile.AvailabilityStatus.BUSY
                worker_profile.save(update_fields=['availability_status', 'updated_at'])
                messages.success(request, f"Job accepted! Please proceed to the customer's location.")

            elif action == 'start':
                if booking.worker != worker_profile or booking.status != Booking.BookingStatus.ACCEPTED:
                    messages.error(request, "Invalid action: job must be Accepted and assigned to you.")
                    return redirect('core:worker_dashboard')
                booking.status = Booking.BookingStatus.IN_PROGRESS
                booking.save(update_fields=['status', 'updated_at'])
                messages.success(request, "Job started! Let the customer know you've arrived.")

            elif action == 'complete':
                if booking.worker != worker_profile or booking.status != Booking.BookingStatus.IN_PROGRESS:
                    messages.error(request, "Invalid action: job must be In Progress and assigned to you.")
                    return redirect('core:worker_dashboard')
                booking.status = Booking.BookingStatus.COMPLETED
                booking.completed_at = timezone.now()
                booking.save(update_fields=['status', 'completed_at', 'updated_at'])
                # Create earnings record
                _create_earning_record(booking)
                # Set worker back to available
                worker_profile.availability_status = WorkerProfile.AvailabilityStatus.AVAILABLE
                worker_profile.save(update_fields=['availability_status', 'updated_at'])
                messages.success(request, "Job marked as complete! Earnings have been recorded.")

            else:
                messages.error(request, "Unknown action.")

    except Booking.DoesNotExist:
        messages.error(request, "Booking not found.")

    return redirect('core:worker_dashboard')


# =============================================================================
# MARKETPLACE (JOB POSTINGS)
# =============================================================================

@login_required
def job_posting_list_view(request):
    """Lists open job postings. Workers see 'Express Interest' button."""
    postings = JobPosting.objects.filter(
        status=JobPosting.PostingStatus.OPEN
    ).select_related('customer', 'category').prefetch_related('interests').order_by('-created_at')

    # For workers: annotate whether they've already expressed interest
    worker_interests = {}
    if request.user.role == CustomUser.Role.PROVIDER:
        try:
            wp = request.user.worker_profile
            for interest in JobInterest.objects.filter(worker=wp, posting__in=postings):
                worker_interests[str(interest.posting_id)] = interest.status
        except WorkerProfile.DoesNotExist:
            pass

    # For customers: their own postings
    my_postings = []
    if request.user.role == CustomUser.Role.CUSTOMER:
        my_postings = JobPosting.objects.filter(customer=request.user).prefetch_related(
            'interests__worker__user'
        ).order_by('-created_at')

    context = {
        'postings': postings,
        'worker_interests': worker_interests,
        'my_postings': my_postings,
    }
    return render(request, 'core/job_posting_list.html', context)


@login_required
@role_required(CustomUser.Role.CUSTOMER)
def job_posting_create_view(request):
    """Customer creates a new custom job posting."""
    categories = ServiceCategory.objects.all()

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        category_id = request.POST.get('category_id')
        preferred_date = request.POST.get('preferred_date') or None
        budget = request.POST.get('budget_estimate', '').strip() or None
        address = request.POST.get('service_address', '').strip()
        lat = request.POST.get('latitude', '').strip() or None
        lon = request.POST.get('longitude', '').strip() or None

        if not title or not description or not category_id:
            messages.error(request, "Title, description, and category are required.")
            return render(request, 'core/job_posting_create.html', {'categories': categories})

        category = get_object_or_404(ServiceCategory, id=category_id)
        JobPosting.objects.create(
            customer=request.user,
            category=category,
            title=title,
            description=description,
            preferred_date=preferred_date,
            budget_estimate=float(budget) if budget else None,
            service_address=address,
            latitude=float(lat) if lat else request.user.latitude,
            longitude=float(lon) if lon else request.user.longitude,
        )
        messages.success(request, "Job posted! Workers in your area will be notified.")
        return redirect('core:job_posting_list')

    return render(request, 'core/job_posting_create.html', {'categories': categories})


@login_required
@role_required(CustomUser.Role.PROVIDER)
@require_POST
def express_interest_view(request, posting_id):
    """Worker expresses interest in a marketplace job posting."""
    posting = get_object_or_404(JobPosting, id=posting_id, status=JobPosting.PostingStatus.OPEN)
    try:
        worker_profile = request.user.worker_profile
    except WorkerProfile.DoesNotExist:
        messages.error(request, "Worker profile not found.")
        return redirect('core:job_posting_list')

    if worker_profile.verification_status != WorkerProfile.VerificationStatus.VERIFIED:
        messages.error(request, "Only verified workers can express interest.")
        return redirect('core:job_posting_list')

    message_text = request.POST.get('message', '').strip()
    _, created = JobInterest.objects.get_or_create(
        posting=posting,
        worker=worker_profile,
        defaults={'message': message_text},
    )
    if created:
        messages.success(request, "Interest expressed! The customer will review your profile.")
    else:
        messages.info(request, "You have already expressed interest in this posting.")
    return redirect('core:job_posting_list')


@login_required
@role_required(CustomUser.Role.CUSTOMER)
@require_POST
def select_worker_for_posting_view(request, posting_id):
    """Customer selects an interested worker, closing the posting."""
    posting = get_object_or_404(JobPosting, id=posting_id, customer=request.user)
    interest_id = request.POST.get('interest_id')
    interest = get_object_or_404(JobInterest, id=interest_id, posting=posting)

    with transaction.atomic():
        # Mark selected
        interest.status = JobInterest.InterestStatus.SELECTED
        interest.save(update_fields=['status'])
        # Reject others
        JobInterest.objects.filter(posting=posting).exclude(id=interest_id).update(
            status=JobInterest.InterestStatus.REJECTED
        )
        # Close posting
        posting.status = JobPosting.PostingStatus.ASSIGNED
        posting.assigned_worker = interest.worker
        posting.save(update_fields=['status', 'assigned_worker', 'updated_at'])

    messages.success(request, f"Worker selected! {interest.worker.user.get_full_name() or interest.worker.user.username} has been assigned.")
    return redirect('core:job_posting_list')


# =============================================================================
# COOPERATIVE ADMIN DASHBOARD
# =============================================================================

@login_required
@role_required(CustomUser.Role.COOP_ADMIN, CustomUser.Role.PLATFORM_ADMIN)
def coop_admin_dashboard_view(request):
    """Admin dashboard: worker verification, analytics, financial summaries."""
    # Handle verify / reject actions
    if request.method == 'POST' and 'worker_id' in request.POST:
        target_worker_id = request.POST.get('worker_id')
        action = request.POST.get('action')
        target_worker = get_object_or_404(WorkerProfile, id=target_worker_id)

        if action == 'verify':
            target_worker.verification_status = WorkerProfile.VerificationStatus.VERIFIED
            target_worker.availability_status = WorkerProfile.AvailabilityStatus.AVAILABLE
            target_worker.save(update_fields=['verification_status', 'availability_status', 'updated_at'])
            messages.success(request, f"Worker '{target_worker.user.get_full_name() or target_worker.user.username}' verified.")
        elif action == 'reject':
            target_worker.verification_status = WorkerProfile.VerificationStatus.REJECTED
            target_worker.save(update_fields=['verification_status', 'updated_at'])
            messages.warning(request, f"Worker '{target_worker.user.get_full_name() or target_worker.user.username}' rejected.")

        return redirect('core:coop_admin_dashboard')

    verified_workers = WorkerProfile.objects.filter(
        verification_status=WorkerProfile.VerificationStatus.VERIFIED
    ).select_related('user').order_by('-rating')

    pending_workers = WorkerProfile.objects.filter(
        verification_status=WorkerProfile.VerificationStatus.PENDING
    ).select_related('user').order_by('created_at')

    financial_summary = CoopEarning.objects.aggregate(
        total_gross=Sum('gross_amount'),
        total_commission=Sum('commission_fee'),
        total_dividend_pool=Sum('coop_dividend_pool'),
        total_worker_payouts=Sum('worker_payout'),
    )

    booking_stats = Booking.objects.aggregate(
        total=Count('id'),
        completed=Count('id', filter=Q(status=Booking.BookingStatus.COMPLETED)),
        pending=Count('id', filter=Q(status=Booking.BookingStatus.PENDING)),
        in_progress=Count('id', filter=Q(status=Booking.BookingStatus.IN_PROGRESS)),
    )

    top_workers = WorkerProfile.objects.filter(
        verification_status=WorkerProfile.VerificationStatus.VERIFIED
    ).annotate(
        jobs_done=Count('worker_bookings', filter=Q(worker_bookings__status=Booking.BookingStatus.COMPLETED))
    ).select_related('user').order_by('-jobs_done')[:5]

    context = {
        'verified_workers': verified_workers,
        'pending_workers': pending_workers,
        'financial_summary': financial_summary,
        'booking_stats': booking_stats,
        'top_workers': top_workers,
        'total_gross': financial_summary['total_gross'] or 0,
        'total_commission': financial_summary['total_commission'] or 0,
        'total_dividend_pool': financial_summary['total_dividend_pool'] or 0,
        'total_worker_payouts': financial_summary['total_worker_payouts'] or 0,
    }
    return render(request, 'core/coop_admin_dashboard.html', context)
