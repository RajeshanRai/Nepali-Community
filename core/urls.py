from django.urls import path
from . import views

urlpatterns = [
    path('', views.HomeView.as_view(), name='home'),
    path('about/', views.AboutView.as_view(), name='about'),
    path('privacy/', views.PrivacyPolicyView.as_view(), name='privacy_policy'),
    path('terms/', views.TermsOfUseView.as_view(), name='terms_of_use'),
    path('accessibility/', views.AccessibilityView.as_view(), name='accessibility'),
    path('search/', views.SearchView.as_view(), name='search'),
    path('sitemap.xml', views.SitemapView.as_view(), name='sitemap'),
    path('rss/', views.RSSFeedView.as_view(), name='rss_feed'),
    path('admin/dashboard/', views.AdminDashboardView.as_view(), name='admin_dashboard'),
    path('admin/dashboard/stats/', views.dashboard_stats_api, name='admin_dashboard_stats'),
]
