import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponseForbidden, JsonResponse
from django.views.decorators.http import require_POST
from django.db.models import Sum, Count, Q, Avg
from django.utils import timezone

from .models import CustomUser, WorkerProfile, ServiceCategory, Service, Booking, CoopEarning

logger = logging.getLogger(__name__)


# -----------------------------------------------------------------------------
# Role-based Authorization Decorators & Helpers
# -----------------------------------------------------------------------------
def role_required(*allowed_roles):
    """
    Decorator enforcing that the logged-in user possesses one of the specified roles.
    """
    def decorator(view_func):
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            if request.user.role not in allowed_roles and not request.user.is_superuser:
                messages.error(request, "You are not authorized to access this page.")
                return HttpResponseForbidden("Access Denied: Insufficient Role Permissions")
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


# -----------------------------------------------------------------------------
# 1. Customer Views: Service Listing & Booking Creation
# -----------------------------------------------------------------------------
def service_list_view(request):
    """
    Renders all active household services available for customers.
    Supports filtering by category and search by title/description.
    """
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


@login_required
@role_required(CustomUser.Role.CUSTOMER)
def booking_create_view(request, service_id):
    """
    Allows authenticated customers to book a specific service.
    Handles GET (renders form & available verified workers) and POST (creates booking).
    """
    service = get_object_or_404(Service, id=service_id, is_active=True)
    available_workers = WorkerProfile.objects.filter(
        verification_status=WorkerProfile.VerificationStatus.VERIFIED,
        availability_status=WorkerProfile.AvailabilityStatus.AVAILABLE
    ).select_related('user')

    if request.method == 'POST':
        scheduled_time_str = request.POST.get('scheduled_time')
        service_address = request.POST.get('service_address', '').strip()
        special_instructions = request.POST.get('special_instructions', '').strip()
        worker_id = request.POST.get('worker_id')

        if not scheduled_time_str or not service_address:
            messages.error(request, "Please fill in all required fields (Scheduled Time & Address).")
            return render(request, 'core/booking_create.html', {
                'service': service,
                'available_workers': available_workers,
            })

        worker = None
        if worker_id:
            worker = get_object_or_404(WorkerProfile, id=worker_id, verification_status=WorkerProfile.VerificationStatus.VERIFIED)

        booking = Booking.objects.create(
            customer=request.user,
            worker=worker,
            service=service,
            scheduled_time=scheduled_time_str,
            total_amount=service.base_price,
            service_address=service_address,
            special_instructions=special_instructions,
            status=Booking.BookingStatus.PENDING,
        )

        messages.success(request, f"Booking #{str(booking.id)[:8]} for {service.title} submitted successfully!")
        return redirect('core:service_list')

    context = {
        'service': service,
        'available_workers': available_workers,
    }
    return render(request, 'core/booking_create.html', context)


# -----------------------------------------------------------------------------
# 2. Worker / Provider Dashboard View
# -----------------------------------------------------------------------------
@login_required
@role_required(CustomUser.Role.PROVIDER)
def worker_dashboard_view(request):
    """
    Allows service providers (workers) to view assigned jobs, update job status,
    and toggle their availability status (Available, Busy, Offline).
    """
    try:
        worker_profile = request.user.worker_profile
    except WorkerProfile.DoesNotExist:
        messages.error(request, "Worker profile not found. Please contact support.")
        return redirect('core:service_list')

    # Handle Availability Status Toggle via POST
    if request.method == 'POST' and 'toggle_status' in request.POST:
        new_status = request.POST.get('availability_status')
        if new_status in WorkerProfile.AvailabilityStatus.values:
            worker_profile.availability_status = new_status
            worker_profile.save(update_fields=['availability_status', 'updated_at'])
            messages.success(request, f"Your status has been updated to '{worker_profile.get_availability_status_display()}'.")
            return redirect('core:worker_dashboard')
        else:
            messages.error(request, "Invalid availability status specified.")

    # Fetch assigned bookings
    assigned_bookings = Booking.objects.filter(
        worker=worker_profile
    ).select_related('customer', 'service').order_selection if hasattr(Booking.objects, 'order_selection') else Booking.objects.filter(
        worker=worker_profile
    ).select_related('customer', 'service').order_by('-scheduled_time')

    pending_jobs = assigned_bookings.filter(status=Booking.BookingStatus.PENDING)
    active_jobs = assigned_bookings.filter(status__in=[Booking.BookingStatus.ACCEPTED, Booking.BookingStatus.IN_PROGRESS])
    completed_jobs = assigned_bookings.filter(status=Booking.BookingStatus.COMPLETED)

    # Calculate earnings summary
    earnings_summary = CoopEarning.objects.filter(worker=worker_profile).aggregate(
        total_payout=Sum('worker_payout'),
        pending_payout=Sum('worker_payout', filter=Q(payout_status=CoopEarning.PayoutStatus.PENDING))
    )

    context = {
        'worker_profile': worker_profile,
        'availability_choices': WorkerProfile.AvailabilityStatus.choices,
        'pending_jobs': pending_jobs,
        'active_jobs': active_jobs,
        'completed_jobs': completed_jobs,
        'total_payout': earnings_summary['total_payout'] or 0.00,
        'pending_payout': earnings_summary['pending_payout'] or 0.00,
    }
    return render(request, 'core/worker_dashboard.html', context)


# -----------------------------------------------------------------------------
# 3. Cooperative Admin Dashboard View
# -----------------------------------------------------------------------------
@login_required
@role_required(CustomUser.Role.COOP_ADMIN, CustomUser.Role.PLATFORM_ADMIN)
def coop_admin_dashboard_view(request):
    """
    Shows verified local workers, pending worker verification applications,
    community earnings summaries, platform commission analytics, and dividend pool metrics.
    """
    verified_workers = WorkerProfile.objects.filter(
        verification_status=WorkerProfile.VerificationStatus.VERIFIED
    ).select_related('user')

    pending_workers = WorkerProfile.objects.filter(
        verification_status=WorkerProfile.VerificationStatus.PENDING
    ).select_related('user')

    # Handle Worker Verification Actions (Verify / Reject)
    if request.method == 'POST' and 'worker_id' in request.POST:
        target_worker_id = request.POST.get('worker_id')
        action = request.POST.get('action')
        target_worker = get_object_or_404(WorkerProfile, id=target_worker_id)

        if action == 'verify':
            target_worker.verification_status = WorkerProfile.VerificationStatus.VERIFIED
            target_worker.save(update_fields=['verification_status', 'updated_at'])
            messages.success(request, f"Worker '{target_worker.user.get_full_name() or target_worker.user.username}' has been verified.")
        elif action == 'reject':
            target_worker.verification_status = WorkerProfile.VerificationStatus.REJECTED
            target_worker.save(update_fields=['verification_status', 'updated_at'])
            messages.warning(request, f"Worker '{target_worker.user.get_full_name() or target_worker.user.username}' has been rejected.")
        
        return redirect('core:coop_admin_dashboard')

    # Community financial metrics aggregation
    financial_summary = CoopEarning.objects.aggregate(
        total_gross=Sum('gross_amount'),
        total_commission=Sum('commission_fee'),
        total_dividend_pool=Sum('coop_dividend_pool'),
        total_worker_payouts=Sum('worker_payout')
    )

    booking_stats = Booking.objects.aggregate(
        total_bookings=Count('id'),
        completed_bookings=Count('id', filter=Q(status=Booking.BookingStatus.COMPLETED)),
        pending_bookings=Count('id', filter=Q(status=Booking.BookingStatus.PENDING))
    )

    context = {
        'verified_workers': verified_workers,
        'pending_workers': pending_workers,
        'total_gross': financial_summary['total_gross'] or 0.00,
        'total_commission': financial_summary['total_commission'] or 0.00,
        'total_dividend_pool': financial_summary['total_dividend_pool'] or 0.00,
        'total_worker_payouts': financial_summary['total_worker_payouts'] or 0.00,
        'booking_stats': booking_stats,
    }
    return render(request, 'core/coop_admin_dashboard.html', context)
