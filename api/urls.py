from django.urls import path
from . import views


urlpatterns = [
    path('upload_image', views.UploadOriginalImage.as_view()),
    path('apply_adjustments', views.ApplyImageAdjustments.as_view()),
    path('resize_image', views.ResizeImage.as_view()),
    path('modify_geometry', views.ModifyGeometry.as_view()),
    path('edge_detection', views.EdgeDetectionView.as_view()),
    path('channel_analysis', views.ChannelAnalysisView.as_view()),
]
