from django.views.generic import ListView
from .models import Partner


class PartnerListView(ListView):
    model = Partner
    template_name = 'partners/list.html'
    context_object_name = 'partners'
