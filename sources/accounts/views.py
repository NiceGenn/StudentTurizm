from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.utils.translation import gettext_lazy as _

from catalog.models import Favorite, Review

from .forms import ProfileForm, RegisterForm


def register(request):
    if request.user.is_authenticated:
        return redirect("catalog:home")

    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, _("Регистрация завершена. Добро пожаловать!"))
            return redirect("catalog:home")
    else:
        form = RegisterForm()

    return render(request, "accounts/register.html", {"form": form})


@login_required
def profile(request):
    if request.method == "POST":
        form = ProfileForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, _("Профиль сохранён."))
            return redirect("accounts:profile")
    else:
        form = ProfileForm(instance=request.user)

    reviews = Review.objects.filter(user=request.user).select_related("attraction")
    context = {
        "form": form,
        "reviews": reviews,
        "favorites_count": Favorite.objects.filter(user=request.user).count(),
    }
    return render(request, "accounts/profile.html", context)


@login_required
def favorites(request):
    items = (
        Favorite.objects.filter(user=request.user)
        .select_related("attraction__category", "attraction__village")
        .prefetch_related("attraction__photos")
    )
    context = {
        "items": items,
        # Все объекты в этом списке уже в избранном — сердечки активны.
        "favorite_slugs": {favorite.attraction.slug for favorite in items},
    }
    return render(request, "accounts/favorites.html", context)
