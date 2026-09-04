from django.conf import settings


def site_menu(request):
    """Общие для всех шаблонов данные: параметры портала и признак админа."""
    return {
        "portal": settings.PORTAL,
        "is_content_manager": request.user.is_authenticated and request.user.is_staff,
        # Bootstrap и Leaflet берутся из static/vendor, если их туда положили
        # скриптом tools/vendor_assets.sh, иначе — из CDN.
        "vendor_local": settings.VENDOR_LOCAL,
    }
