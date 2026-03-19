"""
Dashboard Views Package
Modular structure for better maintainability.

Modules:
- admin_panel.py: DashboardView class and admin panel functionality
- views_module.py: Legacy CRUD operations (to be refactored into crud.py)
"""

# Import admin panel and analytics
from dashboard.views.admin_panel import (
    DashboardView,
    advanced_admin_panel,
    system_chain_view,
    staff_required,
    admin_required,
)

from dashboard.views.member_profile import (
    DashboardProfilesView,
    dashboard_home,
)

# Import all CRUD operations from views_module temporarily
# TODO: Extract these to crud.py
from dashboard.views_module import (
    # Event Management
    event_list,
    event_create, 
    event_edit,
    event_delete,
    event_requests_list,
    event_request_approve,
    event_request_reject,
    event_request_delete,
    
    # Volunteer Management
    volunteer_opportunities_list,
    volunteer_opportunity_create,
    volunteer_opportunity_edit, 
    volunteer_opportunity_delete,
    volunteer_applications_list,
    volunteer_application_approve,
    volunteer_application_reject,
    volunteer_application_delete,
    volunteer_application_assign,
    volunteer_request_approve,
    volunteer_request_reject,
    volunteer_request_delete,
    volunteer_request_assign,
    
    # Announcement Management
    announcements_list,
    announcement_create,
    announcement_edit,
    announcement_delete,
    
    # FAQ Management
    faqs_list,
    faq_create,
    faq_edit,
    faq_delete,
    categories_list,
    category_create,
    category_edit,
    category_delete,
    
    # Donation Management
    donations_list,
    donation_create,
    donation_edit,
    donation_delete,

    # Partner Management
    partners_list,
    partner_create,
    partner_edit,
    partner_delete,
    
    # Contact Management
    contact_messages_list,
    contact_message_create,
    contact_message_edit,
    contact_message_delete,
    
    # Admin Overview & Analytics
    admin_overview,
    admin_analytics,
    admin_activity,
    
    # Projects/Programs Management
    projects_all,
    projects_pending,
    projects_approved,
    projects_rejected,
    
    # Volunteers Management
    volunteers_all,
    volunteers_applications,
    
    # Users Management
    users_all,
    users_roles,
    user_profile_api,
    user_warn,
    user_toggle_ban,
    
    # Reports
    reports_monthly,
    reports_volunteers,
    reports_projects,
    
    # Other
    notifications,
    mark_all_notifications_read,
    settings_view,
)

# Define public API
__all__ = [
    'DashboardProfilesView',
    'dashboard_home',

    # Main Dashboard & Admin Panel
    'DashboardView',
    'advanced_admin_panel',
    'system_chain_view',
    'staff_required',
    'admin_required',
    
    # Event Management
    'event_list',
    'event_create', 
    'event_edit',
    'event_delete',
    'event_requests_list',
    'event_request_approve',
    'event_request_reject',
    'event_request_delete',
    
    # Volunteer Management
    'volunteer_opportunities_list',
    'volunteer_opportunity_create',
    'volunteer_opportunity_edit', 
    'volunteer_opportunity_delete',
    'volunteer_applications_list',
    'volunteer_application_approve',
    'volunteer_application_reject',
    'volunteer_application_delete',
    'volunteer_request_approve',
    'volunteer_request_reject',
    'volunteer_request_delete',
    'volunteer_request_assign',
    
    # Announcement Management
    'announcements_list',
    'announcement_create',
    'announcement_edit',
    'announcement_delete',
    
    # FAQ Management
    'faqs_list',
    'faq_create',
    'faq_edit',
    'faq_delete',
    'categories_list',
    'category_create',
    'category_edit',
    'category_delete',
    
    # Donation Management
    'donations_list',
    'donation_create',
    'donation_edit',
    'donation_delete',

    # Partner Management
    'partners_list',
    'partner_create',
    'partner_edit',
    'partner_delete',
    
    # Contact Management
    'contact_messages_list',
    'contact_message_create',
    'contact_message_edit',
    'contact_message_delete',
    
    # Admin Overview & Analytics
    'admin_overview',
    'admin_analytics',
    'admin_activity',
    
    # Projects/Programs Management
    'projects_all',
    'projects_pending',
    'projects_approved',
    'projects_rejected',
    
    # Volunteers Management
    'volunteers_all',
    'volunteers_applications',
    
    # Users Management
    'users_all',
    'users_roles',
    'user_profile_api',
    'user_warn',
    'user_toggle_ban',
    
    # Reports
    'reports_monthly',
    'reports_volunteers',
    'reports_projects',
    
    # Other
    'notifications',
    'mark_all_notifications_read',
    'settings_view',
]
