from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.LoginView.as_view(), name='login'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('activate/<uidb64>/<token>', views.ActivationConfirmView.as_view(), name='activation_confirm'),
    path('password_reset/', views.PasswordResetView.as_view(), name='password_reset'),
    path('reset/<uidb64>/<token>/', views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('check-active-user/', views.CheckActiveUserView.as_view(), name='check_active_user'),
]
