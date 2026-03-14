from django.db import models


class FAQCategory(models.Model):
    """Categories for organizing FAQs"""
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Font Awesome icon class (e.g., fa-question-circle)")
    order = models.PositiveIntegerField(default=0, help_text="Display order")
    
    class Meta:
        ordering = ['order', 'name']
        verbose_name_plural = 'FAQ Categories'
    
    def __str__(self):
        return self.name


class FAQ(models.Model):
    """Frequently Asked Questions"""
    category = models.ForeignKey(FAQCategory, on_delete=models.CASCADE, related_name='faqs')
    question = models.CharField(max_length=500)
    answer = models.TextField()
    
    # Optional fields
    helpful_count = models.PositiveIntegerField(default=0)
    not_helpful_count = models.PositiveIntegerField(default=0)
    
    # Display settings
    is_published = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False, help_text="Show in featured FAQs")
    order = models.PositiveIntegerField(default=0, help_text="Display order within category")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey('users.CustomUser', null=True, blank=True, on_delete=models.SET_NULL)
    
    # SEO
    meta_keywords = models.CharField(max_length=300, blank=True, help_text="For search")
    
    class Meta:
        ordering = ['order', '-created_at']
        verbose_name = 'FAQ'
        verbose_name_plural = 'FAQs'
    
    def __str__(self):
        return self.question[:100]
    
    @property
    def helpfulness_ratio(self):
        total = self.helpful_count + self.not_helpful_count
        if total == 0:
            return 0
        return (self.helpful_count / total) * 100
