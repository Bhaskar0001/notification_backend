from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    TriggerViewSet,
    NotificationTemplateViewSet,
    TemplateToggleView,
    TemplateTestSendView,
    NotificationViewSet,
    AdminStatsView,
    PushSubscriptionView,
)

router = DefaultRouter()
router.register(r'triggers', TriggerViewSet, basename='admin-triggers')
router.register(r'templates', NotificationTemplateViewSet, basename='admin-templates')
router.register(r'notifications', NotificationViewSet, basename='admin-notifications')

urlpatterns = [
    path('admin/stats/', AdminStatsView.as_view(), name='admin-stats'),
    path('admin/templates/<uuid:pk>/toggle/', TemplateToggleView.as_view(), name='admin-template-toggle'),
    path('admin/templates/<uuid:pk>/test/', TemplateTestSendView.as_view(), name='admin-template-test'),
    path('admin/', include(router.urls)),
    path('push/subscribe/', PushSubscriptionView.as_view(), name='push-subscription'),
]
