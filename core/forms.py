from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError

from .models import (
    CustomUser,
    WorkerProfile,
    ServiceCategory,
    Booking,
    Review,
    JobPosting,
)


# ---------------------------------------------------------------------------
# Authentication Forms
# ---------------------------------------------------------------------------
class LoginForm(AuthenticationForm):
    """Enhanced login form with Bootstrap-compatible widgets."""

    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(
            attrs={
                "class": "w-full px-4 py-3 rounded-xl border border-slate-200 bg-slate-50 focus:outline-none focus:ring-2 focus:ring-brand-400 text-sm placeholder-slate-400",
                "placeholder": "Enter your username",
                "autocomplete": "username",
            }
        ),
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "class": "w-full px-4 py-3 rounded-xl border border-slate-200 bg-slate-50 focus:outline-none focus:ring-2 focus:ring-brand-400 text-sm placeholder-slate-400",
                "placeholder": "Enter your password",
                "autocomplete": "current-password",
            }
        ),
    )


# ---------------------------------------------------------------------------
# Registration Forms
# ---------------------------------------------------------------------------
class CustomerRegistrationForm(forms.Form):
    """Form for customer self-registration."""

    username = forms.CharField(max_length=150)
    email = forms.EmailField()
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)
    phone_number = forms.CharField(max_length=20, required=False)
    city = forms.CharField(max_length=100, required=False)
    pincode = forms.CharField(max_length=10, required=False)
    latitude = forms.FloatField(required=False)
    longitude = forms.FloatField(required=False)
    password1 = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password1") != cleaned.get("password2"):
            raise forms.ValidationError("Passwords do not match.")
        try:
            validate_password(cleaned.get("password1"))
        except ValidationError as e:
            raise forms.ValidationError(e.messages)
        if CustomUser.objects.filter(username=cleaned.get("username")).exists():
            raise forms.ValidationError({"username": "Username already taken."})
        if CustomUser.objects.filter(email=cleaned.get("email")).exists():
            raise forms.ValidationError({"email": "Email already registered."})
        return cleaned


class WorkerRegistrationForm(forms.Form):
    """Form for worker self-registration (creates CustomUser + WorkerProfile)."""

    username = forms.CharField(max_length=150)
    email = forms.EmailField()
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)
    phone_number = forms.CharField(max_length=20, required=False)
    city = forms.CharField(max_length=100, required=False)
    pincode = forms.CharField(max_length=10, required=False)
    latitude = forms.FloatField(required=False)
    longitude = forms.FloatField(required=False)
    password1 = forms.CharField(widget=forms.PasswordInput)
    password2 = forms.CharField(widget=forms.PasswordInput)
    skills = forms.MultipleChoiceField(choices=[])
    hourly_rate = forms.DecimalField(max_digits=10, decimal_places=2, required=False, min_value=0)
    service_radius_km = forms.IntegerField(initial=10, min_value=1, max_value=200)
    coop_member_id = forms.CharField(max_length=50, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["skills"].choices = [
            (cat.slug, cat.name) for cat in ServiceCategory.objects.all()
        ]

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("password1") != cleaned.get("password2"):
            raise forms.ValidationError("Passwords do not match.")
        try:
            validate_password(cleaned.get("password1"))
        except ValidationError as e:
            raise forms.ValidationError(e.messages)
        if not cleaned.get("skills"):
            raise forms.ValidationError({"skills": "Please select at least one skill."})
        if CustomUser.objects.filter(username=cleaned.get("username")).exists():
            raise forms.ValidationError({"username": "Username already taken."})
        if CustomUser.objects.filter(email=cleaned.get("email")).exists():
            raise forms.ValidationError({"email": "Email already registered."})
        return cleaned


# ---------------------------------------------------------------------------
# Booking Forms
# ---------------------------------------------------------------------------
class BookingCreateForm(forms.ModelForm):
    """Form for creating a new booking."""

    class Meta:
        model = Booking
        fields = ["scheduled_time", "service_address", "special_instructions"]
        widgets = {
            "scheduled_time": forms.DateTimeInput(
                attrs={"type": "datetime-local", "class": "w-full px-4 py-3 bg-slate-50 border border-slate-300 rounded-xl text-sm font-medium text-slate-900 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:bg-white transition-all"}
            ),
            "service_address": forms.Textarea(
                attrs={"rows": 3, "class": "w-full px-4 py-3 bg-slate-50 border border-slate-300 rounded-xl text-sm font-medium text-slate-900 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:bg-white transition-all", "placeholder": "Enter full service location address..."}
            ),
            "special_instructions": forms.Textarea(
                attrs={"rows": 2, "class": "w-full px-4 py-3 bg-slate-50 border border-slate-300 rounded-xl text-sm font-medium text-slate-900 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:bg-white transition-all", "placeholder": "Any specific requirements..."}
            ),
        }


# ---------------------------------------------------------------------------
# Review Forms
# ---------------------------------------------------------------------------
class ReviewForm(forms.ModelForm):
    """Form for leaving a review on a completed booking."""

    class Meta:
        model = Review
        fields = ["rating", "comment"]
        widgets = {
            "rating": forms.NumberInput(
                attrs={"min": 1, "max": 5, "class": "hidden"}
            ),
            "comment": forms.Textarea(
                attrs={
                    "rows": 4,
                    "class": "w-full px-4 py-3 bg-slate-50 border border-slate-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:bg-white transition-all",
                    "placeholder": "Share your experience (optional)...",
                }
            ),
        }


# ---------------------------------------------------------------------------
# Marketplace Forms
# ---------------------------------------------------------------------------
class JobPostingForm(forms.ModelForm):
    """Form for creating a custom job posting."""

    class Meta:
        model = JobPosting
        fields = [
            "title",
            "description",
            "category",
            "preferred_date",
            "budget_estimate",
            "service_address",
        ]
        widgets = {
            "title": forms.TextInput(
                attrs={"class": "w-full px-4 py-3 bg-slate-50 border border-slate-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-brand-500", "placeholder": "e.g. Need an electrician for ceiling fan installation"}
            ),
            "description": forms.Textarea(
                attrs={"rows": 4, "class": "w-full px-4 py-3 bg-slate-50 border border-slate-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-brand-500", "placeholder": "Describe your requirements in detail..."}
            ),
            "category": forms.Select(
                attrs={"class": "w-full px-4 py-3 bg-slate-50 border border-slate-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 cursor-pointer"}
            ),
            "preferred_date": forms.DateInput(
                attrs={"type": "date", "class": "w-full px-4 py-3 bg-slate-50 border border-slate-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"}
            ),
            "budget_estimate": forms.NumberInput(
                attrs={"min": 0, "step": 10, "class": "w-full px-4 py-3 bg-slate-50 border border-slate-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-brand-500", "placeholder": "Estimated budget in INR"}
            ),
            "service_address": forms.Textarea(
                attrs={"rows": 2, "class": "w-full px-4 py-3 bg-slate-50 border border-slate-300 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-brand-500", "placeholder": "Location where service is needed..."}
            ),
        }


# ---------------------------------------------------------------------------
# Worker Profile Forms
# ---------------------------------------------------------------------------
class WorkerAvailabilityForm(forms.Form):
    """Form for toggling worker availability status."""

    availability_status = forms.ChoiceField(
        choices=WorkerProfile.AvailabilityStatus.choices,
        widget=forms.Select(
            attrs={"class": "w-full md:w-auto px-4 py-2 bg-white border border-slate-300 rounded-xl text-sm font-bold text-slate-800 focus:outline-none focus:ring-2 focus:ring-brand-500 shadow-sm cursor-pointer"}
        ),
    )
