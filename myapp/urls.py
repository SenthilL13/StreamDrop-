from django.urls import path
from . import views

urlpatterns = [
    path('', views.index_view, name='index'),
    path('upload/', views.FileUploadView.as_view(), name='file-upload'),
    path('stream/<uuid:file_id>/', views.FileStreamView.as_view(), name='file-stream'),
    path('stream/<uuid:file_id>/info/', views.FileInfoView.as_view(), name='file-info'),
    path('qr/<uuid:file_id>/', views.qr_code_view, name='qr-code'),
    path('room/create/', views.CreateRoomView.as_view(), name='room-create'),
    path('room/join/', views.JoinRoomView.as_view(), name='room-join'),
    path('room/<str:pin>/status/', views.RoomStatusView.as_view(), name='room-status'),
]
