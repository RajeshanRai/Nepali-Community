from django.views.generic import FormView
from django.contrib import messages
from .models import ContactMessage
from .forms import ContactForm
from django.urls import reverse_lazy


class ContactView(FormView):
    template_name = 'contacts/contact.html'
    form_class = ContactForm
    success_url = reverse_lazy('contact')

    def form_valid(self, form):
        form.save()
        messages.success(self.request, 'Your message was sent successfully. We will get back to you soon.')
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, 'Please fix the highlighted errors and submit the form again.')
        return super().form_invalid(form)
