from django.views.generic import ListView, DetailView
from .models import Community


class CommunityListView(ListView):
    model = Community
    template_name = 'communities/list.html'
    context_object_name = 'communities'


class CommunityDetailView(DetailView):
    model = Community
    template_name = 'communities/detail.html'
