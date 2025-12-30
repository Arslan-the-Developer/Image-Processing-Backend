from django.urls import path
from . import views


urlpatterns = [
    path('user_register', views.UserRegistrationView.as_view()),
    path('user_otp_verify', views.VerifyUserOTP.as_view()),
    path('user_login', views.UserLoginView.as_view()),
    path('check_user_authentication', views.CheckUserAuthentication.as_view()),
    path('get_user_details', views.GetUserDetails.as_view()),
]
