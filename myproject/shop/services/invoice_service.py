import os
from io import BytesIO
from django.conf import settings
from django.core.files.base import ContentFile
from django.template.loader import get_template
from shop.models import Invoice, Order, OrderItem
from xhtml2pdf import pisa
import logging

logger = logging.getLogger(__name__)

class InvoiceService:
    @staticmethod
    def generate_invoice_number(order_id):
        # Generates a unique invoice number like INV-2026-000001
        from django.utils import timezone
        year = timezone.now().year
        return f"INV-{year}-{order_id:06d}"

    @staticmethod
    def generate_invoice(order):
        """
        Generates an Invoice record and PDF for a given Order.
        """
        if hasattr(order, 'invoice'):
            logger.info(f"Invoice already exists for order {order.id}")
            return order.invoice

        try:
            # 1. Prepare Financial Breakdown
            order_items = OrderItem.objects.filter(order=order).select_related('product')
            subtotal = sum(item.price * item.quantity for item in order_items)
            
            # Simple tax calculation (e.g. 18% GST overall logic if you want to be precise,
            # but usually subtotal includes tax or we calculate it).
            # For simplicity matching Flipkart:
            # Let's say shipping is 50 if subtotal < 500, else 0
            shipping_charge = 50.00 if subtotal < 500 else 0.00
            discount = 0.00
            
            # Grand total should match order.total_price ideally, 
            # but since order.total_price is what the user paid:
            grand_total = order.total_price
            
            # Let's compute tax as 18% of the subtotal just for display
            tax = round(float(subtotal) * 0.18, 2)
            
            # 2. Extract Addresses
            shipping_addr_text = ""
            if order.shipping_address:
                addr = order.shipping_address
                shipping_addr_text = f"{addr.full_name}\n{addr.address_line_1}\n{addr.address_line_2}\n{addr.city}, {addr.state} - {addr.pincode}\nPhone: {addr.phone}"
            else:
                shipping_addr_text = "N/A"

            # 3. Create Invoice Record in DB
            invoice = Invoice.objects.create(
                invoice_number=InvoiceService.generate_invoice_number(order.id),
                order=order,
                user=order.user,
                subtotal=subtotal,
                discount=discount,
                shipping_charge=shipping_charge,
                tax=tax,
                grand_total=grand_total,
                payment_method=order.payment_method,
                payment_status=order.payment_status,
                gst_number="29ABCDE1234F1Z5", # Mock Company GST
                shipping_address=shipping_addr_text,
                billing_address=shipping_addr_text, # Assuming same for now
            )

            # 4. Generate PDF
            template = get_template('shop/invoice_pdf.html')
            context = {
                'invoice': invoice,
                'order': order,
                'items': order_items,
                'company': {
                    'name': 'Velora E-Commerce Pvt. Ltd.',
                    'address': '123 Tech Park, 4th Floor, Sector 5\nBengaluru, Karnataka 560001',
                    'gst': '29ABCDE1234F1Z5',
                    'email': 'support@velora.com',
                    'phone': '+91 800 123 4567',
                    'website': 'www.velora.com'
                }
            }
            html_string = template.render(context)
            
            pdf_file = BytesIO()
            pisa_status = pisa.CreatePDF(
                BytesIO(html_string.encode("UTF-8")),
                dest=pdf_file,
                encoding='utf-8'
            )
            
            if not pisa_status.err:
                pdf_filename = f"Invoice_{invoice.invoice_number}.pdf"
                invoice.invoice_pdf.save(pdf_filename, ContentFile(pdf_file.getvalue()))
                logger.info(f"Successfully generated PDF for {invoice.invoice_number}")
            else:
                logger.error(f"Error generating PDF for {invoice.invoice_number}: {pisa_status.err}")
                
            return invoice
            
        except Exception as e:
            logger.error(f"Failed to generate invoice for order {order.id}: {str(e)}", exc_info=True)
            return None
