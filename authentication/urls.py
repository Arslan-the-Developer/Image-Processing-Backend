from django.urls import path
from . import views


urlpatterns = [
    path('user_register', views.UserRegistrationView.as_view())
]
