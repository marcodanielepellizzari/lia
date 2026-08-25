from django.contrib.auth.forms import AuthenticationForm
from django.shortcuts import render


def home(request):
    """Landing page: login form for anonymous visitors, quick links for
    logged-in users (including the entry point into the upload wizard)."""
    context = {}
    if not request.user.is_authenticated:
        context["form"] = AuthenticationForm(request)
    return render(request, "home.html", context)
