from django.views.generic import ListView, DetailView
from django.db.models import F, Q
from django.utils import timezone
from .models import Announcement


class AnnouncementListView(ListView):
    model = Announcement
    template_name = 'announcements/list.html'
    context_object_name = 'announcements'
    paginate_by = 20
    
    def get_queryset(self):
        qs = Announcement.objects.filter(is_active=True)
        
        # Filter by published status
        now = timezone.now()
        qs = qs.filter(publish_date__lte=now)
        qs = qs.filter(Q(expire_date__isnull=True) | Q(expire_date__gte=now))
        
        # Filter by category
        category = self.request.GET.get('category')
        if category:
            qs = qs.filter(category=category)
        
        return qs.order_by('-is_pinned', '-priority', '-publish_date')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = Announcement.CATEGORY_CHOICES
        context['current_category'] = self.request.GET.get('category', '')
        return context


class AnnouncementDetailView(DetailView):
    model = Announcement
    template_name = 'announcements/detail.html'
    context_object_name = 'announcement'
    
    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        # Increment view count
        Announcement.objects.filter(pk=obj.pk).update(views_count=F('views_count') + 1)
        obj.refresh_from_db()
        return obj
