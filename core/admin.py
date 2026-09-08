from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    CustomUser, WorkerProfile, ServiceCategory, Service,
    Booking, CoopEarning, Review, Payment, JobPosting, JobInterest,
)


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ["username", "email", "role", "is_active", "city", "created_at"]
    list_filter = ["role", "is_active"]
    fieldsets = UserAdmin.fieldsets + (
        ("KaamConnect Profile", {
            "fields": ("role", "phone_number", "profile_picture", "bio", "city", "pincode", "latitude", "longitude"),
        }),
    )
    add_fieldsets = UserAdmin.add_fieldsets + (
        ("KaamConnect Profile", {
            "fields": ("role", "email", "phone_number", "city", "pincode"),
        }),
    )


@admin.register(WorkerProfile)
class WorkerProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "verification_status", "availability_status", "rating", "service_radius_km"]
    list_filter = ["verification_status", "availability_status"]
    search_fields = ["user__username", "user__email"]
    readonly_fields = ["rating", "total_reviews_count"]


@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ["name", "slug"]
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ["title", "category", "base_price", "is_active"]
    list_filter = ["category", "is_active"]
    search_fields = ["title"]
    prepopulated_fields = {"slug": ("title",)}


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ["id", "customer", "worker", "service", "status", "payment_status", "scheduled_time"]
    list_filter = ["status", "payment_status"]
    search_fields = ["customer__username", "service__title"]
    readonly_fields = ["id", "created_at", "updated_at", "job_accepted_at", "completed_at"]


@admin.register(CoopEarning)
class CoopEarningAdmin(admin.ModelAdmin):
    list_display = ["booking", "worker", "gross_amount", "worker_payout", "payout_status"]
    list_filter = ["payout_status"]
    readonly_fields = ["created_at", "updated_at"]


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ["booking", "customer", "worker", "rating", "created_at"]
    list_filter = ["rating"]
    readonly_fields = ["created_at"]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ["booking", "amount", "status", "transaction_ref", "paid_at"]
    list_filter = ["status"]
    readonly_fields = ["transaction_ref", "created_at"]


@admin.register(JobPosting)
class JobPostingAdmin(admin.ModelAdmin):
    list_display = ["title", "customer", "category", "status", "budget_estimate", "created_at"]
    list_filter = ["status", "category"]
    search_fields = ["title", "customer__username"]


@admin.register(JobInterest)
class JobInterestAdmin(admin.ModelAdmin):
    list_display = ["posting", "worker", "status", "expressed_at"]
    list_filter = ["status"]
