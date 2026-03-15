from django.views.generic import ListView, DetailView
from .models import Community
from users.tracking import track_recent_view


class CommunityListView(ListView):
    model = Community
    template_name = 'communities/list.html'
    context_object_name = 'communities'


class CommunityDetailView(DetailView):
    model = Community
    template_name = 'communities/detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        community = self.object
        track_recent_view(
            self.request,
            content_type='community',
            object_id=community.pk,
            title=community.name,
            url=self.request.path,
        )
        return context
