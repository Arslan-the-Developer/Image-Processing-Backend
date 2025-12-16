from django.urls import path
from . import views


urlpatterns = [
    path('upload_image', views.UploadOriginalImage.as_view()),
    path('apply_adjustments', views.ApplyImageAdjustments.as_view())
]
