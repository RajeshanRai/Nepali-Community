from django.views.generic import ListView
from .models import FAQ


class FAQListView(ListView):
    model = FAQ
    template_name = 'faqs/list.html'
    context_object_name = 'faqs'
    
    def get_queryset(self):
        # Return only 20 published FAQs, ordered by display order
        return FAQ.objects.filter(is_published=True).order_by('order', '-created_at')[:20]
