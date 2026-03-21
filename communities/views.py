from django.views.generic import ListView, DetailView
from django.db.models import Count
from .models import Community
from users.tracking import track_recent_view


def _attach_display_stats(community):
    """Attach live stats used by templates, falling back to stored values."""
    linked_members = (
        getattr(community, 'primary_members_count', 0)
        + getattr(community, 'secondary_members_count', 0)
    )
    linked_programs = getattr(community, 'programs_count', 0)

    community.display_member_count = linked_members if linked_members > 0 else community.member_count
    community.display_events_per_year = linked_programs if linked_programs > 0 else community.events_per_year
    return community


class CommunityListView(ListView):
    model = Community
    template_name = 'communities/list.html'
    context_object_name = 'communities'

    def get_queryset(self):
        qs = (
            Community.objects
            .annotate(
                primary_members_count=Count('primary_members', distinct=True),
                secondary_members_count=Count('secondary_members', distinct=True),
                programs_count=Count('programs', distinct=True),
            )
            .order_by('name')
        )
        return [_attach_display_stats(community) for community in qs]


class CommunityDetailView(DetailView):
    model = Community
    template_name = 'communities/detail.html'

    def get_queryset(self):
        return Community.objects.annotate(
            primary_members_count=Count('primary_members', distinct=True),
            secondary_members_count=Count('secondary_members', distinct=True),
            programs_count=Count('programs', distinct=True),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        community = _attach_display_stats(self.object)
        track_recent_view(
            self.request,
            content_type='community',
            object_id=community.pk,
            title=community.name,
            url=self.request.path,
        )
        return context
