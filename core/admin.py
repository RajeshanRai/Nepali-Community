from django.contrib import admin
from .models import ChatbotConversation, ChatbotFaq, ChatbotMessage, TeamMember


@admin.register(TeamMember)
class TeamMemberAdmin(admin.ModelAdmin):
    list_display = ('name', 'role', 'badge', 'order', 'is_active')
    list_editable = ('order', 'is_active')
    list_filter = ('is_active',)
    search_fields = ('name', 'role')


@admin.register(ChatbotFaq)
class ChatbotFaqAdmin(admin.ModelAdmin):
    list_display = ('question', 'is_active', 'updated_at')
    list_editable = ('is_active',)
    search_fields = ('question', 'answer', 'keywords')
    list_filter = ('is_active',)


@admin.register(ChatbotConversation)
class ChatbotConversationAdmin(admin.ModelAdmin):
    list_display = ('session_key', 'user', 'message_count', 'updated_at')
    readonly_fields = ('created_at', 'updated_at', 'message_count', 'last_message')
    search_fields = ('session_key', 'user__username', 'user__email')
    list_filter = ('user',)


@admin.register(ChatbotMessage)
class ChatbotMessageAdmin(admin.ModelAdmin):
    list_display = ('conversation', 'role', 'source', 'created_at')
    readonly_fields = ('conversation', 'role', 'content', 'source', 'created_at')
    list_filter = ('role', 'source')
    search_fields = ('content',)
