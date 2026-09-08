from django.urls import path
from . import views

app_name = "core"

urlpatterns = [
    # Root Landing & Customer Routes
    path("", views.service_list_view, name="home"),
    path("services/", views.service_list_view, name="service_list"),
    path("services/<uuid:service_id>/book/", views.booking_create_view, name="booking_create"),
    
    # Service Provider (Worker) Routes
    path("worker/dashboard/", views.worker_dashboard_view, name="worker_dashboard"),
    
    # Cooperative Admin Routes
    path("coop-admin/dashboard/", views.coop_admin_dashboard_view, name="coop_admin_dashboard"),
]
