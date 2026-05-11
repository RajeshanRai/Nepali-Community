"""
Dashboard template tags and filters.

This module provides template inclusion tags for repeated template context
like sidebar counts, status badges, and common UI elements.
"""

from django import template
from django.utils.html import format_html
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag
def sidebar_badge(count, badge_class='badge-warning'):
    """
    Render a badge for sidebar counts.
    
    Usage:
        {% sidebar_badge pending_projects_count %}
        {% sidebar_badge pending_projects_count "badge-info" %}
    """
    if count > 0:
        return format_html(
            '<span class="badge {}">{}</span>',
            badge_class,
            count
        )
    return ''


@register.simple_tag
def status_badge(status):
    """
    Render a status badge with appropriate styling.
    
    Usage:
        {% status_badge "pending" %}
        {% status_badge "approved" %}
    """
    status_classes = {
        'pending': 'badge-warning',
        'approved': 'badge-success',
        'rejected': 'badge-danger',
        'completed': 'badge-info',
        'open': 'badge-success',
        'filled': 'badge-secondary',
        'new': 'badge-primary',
        'contacted': 'badge-info',
        'closed': 'badge-secondary',
    }
    
    css_class = status_classes.get(status.lower(), 'badge-secondary')
    status_display = status.replace('_', ' ').title()
    
    return format_html(
        '<span class="badge {}">{}</span>',
        css_class,
        status_display
    )


@register.inclusion_tag('dashboard/includes/sidebar_counts.html')
def render_sidebar_counts():
    """
    Render sidebar counts in a consistent format.
    
    Usage:
        {% render_sidebar_counts %}
    
    This template tag uses the context processor values automatically.
    """
    return {}


@register.filter
def status_class(status):
    """
    Get CSS class for status.
    
    Usage:
        {{ status|status_class }}
    """
    status_classes = {
        'pending': 'warning',
        'approved': 'success',
        'rejected': 'danger',
        'completed': 'info',
        'open': 'success',
        'filled': 'secondary',
        'new': 'primary',
        'contacted': 'info',
        'closed': 'secondary',
    }
    return status_classes.get(status.lower(), 'secondary')


@register.filter
def status_icon(status):
    """
    Get icon name for status.
    
    Usage:
        {{ status|status_icon }}
    """
    status_icons = {
        'pending': 'clock',
        'approved': 'check-circle',
        'rejected': 'times-circle',
        'completed': 'check',
        'open': 'door-open',
        'filled': 'users',
        'new': 'plus-circle',
        'contacted': 'envelope',
        'closed': 'lock',
    }
    return status_icons.get(status.lower(), 'circle')


@register.simple_tag
def admin_nav_link(url, icon, label, badge_count=None):
    """
    Render an admin navigation link with icon and optional badge.
    
    Usage:
        {% admin_nav_link "dashboard:projects_pending" "fa-calendar" "Pending" pending_projects_count %}
    """
    html = f'<a href="{url}" class="nav-link">'
    html += f'<i class="{icon}"></i> '
    html += f'<span>{label}</span>'
    
    if badge_count and badge_count > 0:
        html += f'<span class="badge badge-warning">{badge_count}</span>'
    
    html += '</a>'
    return mark_safe(html)
