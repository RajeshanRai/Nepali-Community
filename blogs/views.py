from django.views.generic import ListView, DetailView
from .models import BlogPost


class BlogListView(ListView):
    model = BlogPost
    template_name = 'blogs/list.html'
    context_object_name = 'posts'
    paginate_by = 10


class BlogDetailView(DetailView):
    model = BlogPost
    template_name = 'blogs/detail.html'
    context_object_name = 'post'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['recommended_posts'] = BlogPost.objects.exclude(pk=self.object.pk)[:3]
        return context
