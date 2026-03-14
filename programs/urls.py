from django.urls import path
from . import views

urlpatterns = [
    path('', views.ProgramListView.as_view(), name='program_list'),
    path('calendar/', views.CalendarView.as_view(), name='calendar'),
    path('<int:pk>/', views.ProgramDetailView.as_view(), name='program_detail'),
    path('<int:program_id>/register/', views.RegisterForEventView.as_view(), name='register_event'),    path('<int:program_id>/unregister/', views.UnregisterForEventView.as_view(), name='program_unregister'),    path('my-registrations/', views.UserRegistrationsView.as_view(), name='my_registrations'),
    path('request/', views.RequestEventCreateView.as_view(), name='request_event'),
    path('api/recent-requests/', views.programs_recent_requests, name='programs_recent_requests_api'),
]
