from django.contrib import admin
from .models import FAQCategory, FAQ


@admin.register(FAQCategory)
class FAQCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'order', 'faq_count')
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ('order',)
    
    def faq_count(self, obj):
        return obj.faqs.count()
    faq_count.short_description = 'Number of FAQs'


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('question_preview', 'category', 'is_published', 'is_featured', 'order', 'helpful_count', 'not_helpful_count', 'updated_at')
    list_filter = ('category', 'is_published', 'is_featured', 'created_at')
    search_fields = ('question', 'answer', 'meta_keywords')
    # Optimized: select_related to prevent N+1 when displaying category and created_by
    list_select_related = ('category', 'created_by')
    list_editable = ('is_published', 'is_featured', 'order')
    readonly_fields = ('created_at', 'updated_at', 'helpful_count', 'not_helpful_count', 'helpfulness_ratio')
    
    fieldsets = (
        ('Question & Answer', {
            'fields': ('category', 'question', 'answer')
        }),
        ('Display Settings', {
            'fields': ('is_published', 'is_featured', 'order')
        }),
        ('Feedback Stats', {
            'fields': ('helpful_count', 'not_helpful_count', 'helpfulness_ratio'),
            'classes': ('collapse',)
        }),
        ('SEO & Metadata', {
            'fields': ('meta_keywords', 'created_by', 'created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def question_preview(self, obj):
        return obj.question[:80] + '...' if len(obj.question) > 80 else obj.question
    question_preview.short_description = 'Question'
    
    def save_model(self, request, obj, form, change):
        if not change:  # New object
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
