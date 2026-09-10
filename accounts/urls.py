from django.urls import path
from accounts.views import LoginView, LogoutView, ProfileView, PasswordView, AvailableRolesView

urlpatterns = [
    path('auth/login', LoginView.as_view()),
    path('auth/logout', LogoutView.as_view()),
    path('auth/profile', ProfileView.as_view()),
    path('auth/change-password', PasswordView.as_view()),
    path('available-roles', AvailableRolesView.as_view()),
]
