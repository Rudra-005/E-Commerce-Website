from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404
from django.views import View
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
import mimetypes
import os

from shop.models import Invoice

@method_decorator(login_required, name="dispatch")
class InvoiceDownloadView(View):
    def get(self, request, order_id):
        from shop.models import Order
        from shop.services.invoice_service import InvoiceService
        # Allow user to download their own invoice, or allow admin to download any invoice
        if request.user.is_staff or hasattr(request.user, 'userprofile') and request.user.userprofile.role in ['admin', 'support']:
            order = get_object_or_404(Order, id=order_id)
        else:
            order = get_object_or_404(Order, id=order_id, user=request.user)
            
        if hasattr(order, 'invoice'):
            invoice = order.invoice
        else:
            invoice = InvoiceService.generate_invoice(order)
            
        if not invoice or not invoice.invoice_pdf:
            raise Http404("Invoice PDF could not be generated.")
            
        file_path = invoice.invoice_pdf.path
        if not os.path.exists(file_path):
            raise Http404("Invoice PDF file not found on disk.")
            
        with open(file_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="Invoice_{invoice.invoice_number}.pdf"'
            return response


@method_decorator(login_required, name="dispatch")
class InvoiceView(View):
    def get(self, request, order_id):
        from shop.models import Order
        from shop.services.invoice_service import InvoiceService
        # Allow user to view their own invoice, or allow admin to view any invoice
        if request.user.is_staff or hasattr(request.user, 'userprofile') and request.user.userprofile.role in ['admin', 'support']:
            order = get_object_or_404(Order, id=order_id)
        else:
            order = get_object_or_404(Order, id=order_id, user=request.user)
            
        if hasattr(order, 'invoice'):
            invoice = order.invoice
        else:
            invoice = InvoiceService.generate_invoice(order)
            
        if not invoice or not invoice.invoice_pdf:
            raise Http404("Invoice PDF could not be generated.")
            
        file_path = invoice.invoice_pdf.path
        if not os.path.exists(file_path):
            raise Http404("Invoice PDF file not found on disk.")
            
        with open(file_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename="Invoice_{invoice.invoice_number}.pdf"'
            return response
