from django.urls import path
from . import views

urlpatterns = [
    path('', views.FAQListView.as_view(), name='faq_list'),
]
