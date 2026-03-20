from django.urls import path
from . import views
from . import api as dashboard_api

app_name = 'dashboard'


urlpatterns = [
    path('', views.dashboard_home, name='dashboard_home'),
    path('admin/users/profiles/', views.DashboardProfilesView.as_view(), name='profiles'),
    path('admin/users/profiles/<int:user_id>/', views.DashboardProfilesView.as_view(), name='profiles_detail'),
        # ====== SIDEBAR ADMIN INTERFACE ======
        # Main Dashboard
        path('admin/overview/', views.admin_overview, name='admin_overview'),
        path('admin/analytics/', views.admin_analytics, name='admin_analytics'),
        path('admin/activity/', views.admin_activity, name='admin_activity'),
    
        # Projects Management
        path('admin/projects/', views.projects_all, name='projects_all'),
        path('admin/projects/pending/', views.projects_pending, name='projects_pending'),
        path('admin/projects/approved/', views.projects_approved, name='projects_approved'),
        path('admin/projects/rejected/', views.projects_rejected, name='projects_rejected'),
    
        # Volunteers Management
        path('admin/volunteers/', views.volunteers_all, name='volunteers_all'),
        path('admin/volunteers/applications/', views.volunteers_applications, name='volunteers_applications'),
    
        # Users Management
        path('admin/users/', views.users_all, name='users_all'),
        path('admin/users/roles/', views.users_roles, name='users_roles'),
        path('admin/users/<int:user_id>/profile/', views.user_profile_api, name='user_profile_api'),
        path('admin/users/<int:user_id>/warn/', views.user_warn, name='user_warn'),
        path('admin/users/<int:user_id>/toggle-ban/', views.user_toggle_ban, name='user_toggle_ban'),
    
        # Categories Management
        path('admin/categories/', views.categories_list, name='categories_list'),
        path('admin/categories/create/', views.category_create, name='category_create'),
        path('admin/categories/<int:pk>/edit/', views.category_edit, name='category_edit'),
        path('admin/categories/<int:pk>/delete/', views.category_delete, name='category_delete'),
        path('admin/reports/monthly/', views.reports_monthly, name='reports_monthly'),

        # System Chain
        path('admin/reports/volunteers/', views.reports_volunteers, name='reports_volunteers'),
        path('admin/reports/projects/', views.reports_projects, name='reports_projects'),
    
        # Notifications & Settings
        path('admin/notifications/', views.notifications, name='notifications'),
        path('admin/notifications/mark-all-read/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
        path('admin/settings/', views.settings_view, name='settings'),
        # System Design (3D graph view)
        path('admin/system-design/', views.system_chain_view, name='system_design'),
    
    
    # Event Management
    path('events/', views.event_list, name='event_list'),
    path('events/create/', views.event_create, name='event_create'),
    path('events/<int:pk>/edit/', views.event_edit, name='event_edit'),
    path('events/<int:pk>/delete/', views.event_delete, name='event_delete'),
    
    # Volunteer Management
    path('volunteers/opportunities/', views.volunteer_opportunities_list, name='volunteer_opportunities_list'),
    path('volunteers/opportunities/create/', views.volunteer_opportunity_create, name='volunteer_opportunity_create'),
    path('volunteers/opportunities/<int:pk>/edit/', views.volunteer_opportunity_edit, name='volunteer_opportunity_edit'),
    path('volunteers/opportunities/<int:pk>/delete/', views.volunteer_opportunity_delete, name='volunteer_opportunity_delete'),
    path('volunteers/applications/', views.volunteer_applications_list, name='volunteer_applications_list'),
    path('volunteers/applications/<int:pk>/approve/', views.volunteer_application_approve, name='volunteer_application_approve'),
    path('volunteers/applications/<int:pk>/reject/', views.volunteer_application_reject, name='volunteer_application_reject'),
    path('volunteers/applications/<int:pk>/delete/', views.volunteer_application_delete, name='volunteer_application_delete'),
    path('volunteers/applications/<int:pk>/assign/', views.volunteer_application_assign, name='volunteer_application_assign'),
    path('volunteers/requests/<int:pk>/approve/', views.volunteer_request_approve, name='volunteer_request_approve'),
    path('volunteers/requests/<int:pk>/reject/', views.volunteer_request_reject, name='volunteer_request_reject'),
    path('volunteers/requests/<int:pk>/delete/', views.volunteer_request_delete, name='volunteer_request_delete'),
    path('volunteers/requests/<int:pk>/assign/', views.volunteer_request_assign, name='volunteer_request_assign'),
    
    # Event Requests
    path('requests/', views.event_requests_list, name='event_requests_list'),
    path('requests/<int:pk>/approve/', views.event_request_approve, name='event_request_approve'),
    path('requests/<int:pk>/reject/', views.event_request_reject, name='event_request_reject'),
    path('requests/<int:pk>/delete/', views.event_request_delete, name='event_request_delete'),
    
    # Announcements
    path('announcements/', views.announcements_list, name='announcements_list'),
    path('announcements/create/', views.announcement_create, name='announcement_create'),
    path('announcements/<int:pk>/edit/', views.announcement_edit, name='announcement_edit'),
    path('announcements/<int:pk>/delete/', views.announcement_delete, name='announcement_delete'),
    
    # FAQs
    path('faqs/', views.faqs_list, name='faqs_list'),
    path('faqs/create/', views.faq_create, name='faq_create'),
    path('faqs/<int:pk>/edit/', views.faq_edit, name='faq_edit'),
    path('faqs/<int:pk>/delete/', views.faq_delete, name='faq_delete'),

    # Donations
    path('donations/', views.donations_list, name='donations_list'),
    path('donations/create/', views.donation_create, name='donation_create'),
    path('donations/<int:pk>/edit/', views.donation_edit, name='donation_edit'),
    path('donations/<int:pk>/delete/', views.donation_delete, name='donation_delete'),

    # Contact Messages
    path('contact-messages/', views.contact_messages_list, name='contact_messages_list'),
    path('contact-messages/create/', views.contact_message_create, name='contact_message_create'),
    path('contact-messages/<int:pk>/edit/', views.contact_message_edit, name='contact_message_edit'),
    path('contact-messages/<int:pk>/delete/', views.contact_message_delete, name='contact_message_delete'),

    # Partners
    path('partners/', views.partners_list, name='partners_list'),
    path('partners/create/', views.partner_create, name='partner_create'),
    path('partners/<int:pk>/edit/', views.partner_edit, name='partner_edit'),
    path('partners/<int:pk>/delete/', views.partner_delete, name='partner_delete'),

    # Team Members
    path('team-members/', views.team_members_list, name='team_members_list'),
    path('team-members/create/', views.team_member_create, name='team_member_create'),
    path('team-members/<int:pk>/edit/', views.team_member_edit, name='team_member_edit'),
    path('team-members/<int:pk>/delete/', views.team_member_delete, name='team_member_delete'),
    
    # API Endpoints
    path('api/available-opportunities/', dashboard_api.get_available_opportunities, name='api_available_opportunities'),
]
