from django.urls import path
from . import views

urlpatterns = [
    path('', views.PartnerListView.as_view(), name='partner_list'),
]
