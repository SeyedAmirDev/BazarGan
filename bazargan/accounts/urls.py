from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.LoginView.as_view(), name='login'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('activate/<uidb64>/<token>', views.ActivationLinkConfirmView.as_view(), name='activation_confirm'),
    path('reset/<uidb64>/<token>/', views.PasswordResetLinkConfirmView.as_view(), name='password_reset_confirm'),
    path('check-active-user/', views.CheckActiveUserView.as_view(), name='check_active_user'),
    path('reset_password/otp/', views.PasswordResetOtpView.as_view(), name='password_reset_otp'),
    path('reset_password/otp/verify/', views.ReceiveOTPForPasswordReset.as_view(), name='password_reset_otp_verify'),
    path('reset_password/otp/complete/', views.PasswordResetOtpCompleteView.as_view(), name='password_reset_otp_complete'),
    path('activation/otp/', views.ActivationOtpView.as_view(), name='activation_otp'),
    path('activation/otp/verify/', views.ReceiveOTPForActivationView.as_view(), name='activation_otp_verify'),
    path('activation/otp/complete/', views.ActivationCompleteView.as_view(), name='activation_otp_complete'),
]
