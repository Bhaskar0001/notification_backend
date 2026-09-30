from django.urls import path
from .views import UserProfileView, UserNotificationsView

urlpatterns = [
    path('me/', UserProfileView.as_view(), name='user-profile-me'),
    path('me/notifications/', UserNotificationsView.as_view(), name='user-notifications-me'),
]
