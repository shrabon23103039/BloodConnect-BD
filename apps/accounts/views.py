"""Server-rendered account registration and session authentication views."""

from django.contrib.auth import views as auth_views
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_http_methods

from apps.accounts.forms import (
    AccountPasswordResetForm,
    IdentifierAuthenticationForm,
    RegistrationForm,
)
from apps.accounts.throttling import limited_by_ip


@limited_by_ip(scope="register", limit=5, window_seconds=3600)
@require_http_methods(["GET", "POST"])
def register(request):
    form = RegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        values = form.cleaned_data
        try:
            with transaction.atomic():
                get_user_model().objects.create_user(
                    email=values.get("email"),
                    phone_e164=values.get("phone_e164"),
                    display_name=values["display_name"],
                    password=values["password1"],
                )
        except (IntegrityError, ValidationError):
            # A generic response prevents account enumeration by email or phone.
            pass
        return redirect("accounts:registration_submitted")
    return render(request, "accounts/register.html", {"form": form})


def registration_submitted(request):
    return render(request, "accounts/registration_submitted.html")


class ThrottledLoginView(auth_views.LoginView):
    template_name = "accounts/login.html"
    authentication_form = IdentifierAuthenticationForm
    next_page = reverse_lazy("home")

    @limited_by_ip(scope="login", limit=10, window_seconds=60)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)


class ThrottledPasswordResetView(auth_views.PasswordResetView):
    template_name = "accounts/password_reset_form.html"
    form_class = AccountPasswordResetForm
    email_template_name = "accounts/password_reset_email.txt"
    subject_template_name = "accounts/password_reset_subject.txt"
    success_url = "/accounts/password-reset/done/"

    @limited_by_ip(scope="password-reset", limit=5, window_seconds=3600)
    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)
