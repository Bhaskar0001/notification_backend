from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse


def root_health_view(request):
    return JsonResponse({
        "status": "online",
        "service": "Notification Management System API",
        "version": "1.0.0",
        "endpoints": {
            "auth": "/api/auth/",
            "users": "/api/users/",
            "notifications": "/api/",
        }
    })


urlpatterns = [
    path('', root_health_view, name='root_health'),
    path('admin/', admin.site.urls),
    path('api/auth/', include('apps.accounts.urls')),
    path('api/users/', include('apps.accounts.user_urls')),
    path('api/', include('apps.notifications.urls')),
]
