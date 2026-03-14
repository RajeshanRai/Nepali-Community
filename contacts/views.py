from django.views.generic import FormView
from .models import ContactMessage
from .forms import ContactForm
from django.urls import reverse_lazy


class ContactView(FormView):
    template_name = 'contacts/contact.html'
    form_class = ContactForm
    success_url = reverse_lazy('contact')

    def form_valid(self, form):
        form.save()
        return super().form_valid(form)
