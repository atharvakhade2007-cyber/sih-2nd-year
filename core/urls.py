from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    # ─── Public ───────────────────────────────────────────────────────────────
    path("", views.service_list_view, name="home"),
    path("services/", views.service_list_view, name="service_list"),

    # ─── Auth ─────────────────────────────────────────────────────────────────
    path("accounts/login/", views.login_view, name="login"),
    path("accounts/logout/", views.logout_view, name="logout"),
    path("accounts/register/", views.register_customer_view, name="register"),
    path("accounts/register/worker/", views.register_worker_view, name="worker_register"),

    # ─── Customer ─────────────────────────────────────────────────────────────
    path("dashboard/", views.customer_dashboard_view, name="customer_dashboard"),
    path("services/<uuid:service_id>/book/", views.booking_create_view, name="booking_create"),
    path("bookings/<uuid:booking_id>/", views.booking_detail_view, name="booking_detail"),
    path("bookings/<uuid:booking_id>/cancel/", views.booking_cancel_view, name="booking_cancel"),
    path("bookings/<uuid:booking_id>/pay/", views.payment_view, name="payment"),
    path("bookings/<uuid:booking_id>/receipt/", views.payment_receipt_view, name="payment_receipt"),
    path("bookings/<uuid:booking_id>/review/", views.review_create_view, name="review_create"),

    # ─── Worker ───────────────────────────────────────────────────────────────
    path("worker/dashboard/", views.worker_dashboard_view, name="worker_dashboard"),
    path("worker/bookings/<uuid:booking_id>/action/", views.booking_action_view, name="booking_action"),

    # ─── Marketplace ──────────────────────────────────────────────────────────
    path("marketplace/", views.job_posting_list_view, name="job_posting_list"),
    path("marketplace/post/", views.job_posting_create_view, name="job_posting_create"),
    path("marketplace/<uuid:posting_id>/interest/", views.express_interest_view, name="express_interest"),
    path("marketplace/<uuid:posting_id>/select/", views.select_worker_for_posting_view, name="select_worker"),

    # ─── Coop Admin ───────────────────────────────────────────────────────────
    path("coop-admin/dashboard/", views.coop_admin_dashboard_view, name="coop_admin_dashboard"),
]
