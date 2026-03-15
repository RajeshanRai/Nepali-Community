from django.utils import timezone

from .models import RecentlyViewedContent


def track_recent_view(request, *, content_type, object_id, title, url, max_items=40):
    """Store recent page views for authenticated users in an isolated users model."""
    user = getattr(request, 'user', None)
    if not user or not user.is_authenticated:
        return

    normalized_title = (title or '').strip()[:255]
    normalized_url = (url or '').strip()[:255]
    normalized_object_id = int(object_id) if object_id is not None else None
    if not normalized_title or not normalized_url or normalized_object_id is None:
        return

    RecentlyViewedContent.objects.update_or_create(
        user=user,
        content_type=content_type,
        object_id=normalized_object_id,
        defaults={
            'title': normalized_title,
            'url': normalized_url,
            'viewed_at': timezone.now(),
        },
    )

    stale_ids = list(
        RecentlyViewedContent.objects.filter(user=user)
        .order_by('-viewed_at')
        .values_list('id', flat=True)[max_items:]
    )
    if stale_ids:
        RecentlyViewedContent.objects.filter(id__in=stale_ids).delete()
