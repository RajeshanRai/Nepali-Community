from django.urls import path
from . import views

urlpatterns = [
    path('', views.VolunteerListView.as_view(), name='volunteer_list'),
    path('request/', views.volunteer_request_submit, name='volunteer_request_submit'),
    path('<int:pk>/', views.VolunteerDetailView.as_view(), name='volunteer_detail'),
    path('<int:pk>/apply/', views.VolunteerApplyView.as_view(), name='volunteer_apply'),
]
