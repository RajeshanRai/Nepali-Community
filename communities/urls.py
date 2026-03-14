from django.urls import path
from . import views

urlpatterns = [
    path('', views.CommunityListView.as_view(), name='community_list'),
    path('<int:pk>/', views.CommunityDetailView.as_view(), name='community_detail'),
]
