"""
URL configuration for nepali_community project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('favicon.ico', RedirectView.as_view(url=f'{settings.STATIC_URL}favicon.svg', permanent=False)),
    path('accounts/login/', RedirectView.as_view(url='/users/login/', query_string=True, permanent=False)),
    path('', include('core.urls')),
    path('users/', include('users.urls')),
    path('communities/', include('communities.urls')),
    path('programs/', include('programs.urls')),
    path('partners/', include('partners.urls')),
    path('donate/', include('donations.urls')),
    path('contact/', include('contacts.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('volunteers/', include('volunteers.urls')),
    path('announcements/', include('announcements.urls')),
    path('faq/', include('faqs.urls')),
]

# Serve static and media files in development
if settings.DEBUG:
    # Serve from the source static directory, not STATIC_ROOT (which is for production)
    urlpatterns += static(settings.STATIC_URL, document_root=str(settings.BASE_DIR / 'static'))
    urlpatterns += static(settings.MEDIA_URL, document_root=str(settings.MEDIA_ROOT))
