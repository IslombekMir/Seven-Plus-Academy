# yourapp/middleware.py
from django.utils import translation

from django.utils import translation

from django.utils import translation

class UserLanguageMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if getattr(request, "user", None) and request.user.is_authenticated:
            settings_obj = getattr(request.user, "settings", None)
            if settings_obj:
                lang_code = "uz" if settings_obj.language == "UZBEK" else "en"
                translation.activate(lang_code)
                request.LANGUAGE_CODE = lang_code

        response = self.get_response(request)
        return response

