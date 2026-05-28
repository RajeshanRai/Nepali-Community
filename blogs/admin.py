from django.contrib import admin
from .models import BlogPost


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'author_name', 'published_at', 'slug')
    prepopulated_fields = {'slug': ('title',)}
    search_fields = ('title', 'author_name', 'content')
    list_filter = ('published_at',)
