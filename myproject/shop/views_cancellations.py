import json
from django.http import JsonResponse
from django.views import View
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from .models import Order, OrderItem, OrderItemCancellation

@method_decorator(csrf_exempt, name='dispatch')
class CancelOrderItemAPIView(LoginRequiredMixin, View):
    def post(self, request, order_id, item_id):
        try:
            data = json.loads(request.body)
            reason = data.get('reason', '')
            other_reason = data.get('other_reason', '')

            if not reason:
                return JsonResponse({'success': False, 'error': 'Cancellation reason is required'}, status=400)

            # Get order and item
            order = get_object_or_404(Order, id=order_id, user=request.user)
            item = get_object_or_404(OrderItem, id=item_id, order=order)

            # Check eligibility
            if item.status in ['Cancelled', 'Cancellation Requested', 'Shipped', 'Delivered']:
                return JsonResponse({'success': False, 'error': f'Item cannot be cancelled because it is {item.status}'}, status=400)
            
            if order.status in ['Cancelled', 'Shipped', 'Delivered']:
                return JsonResponse({'success': False, 'error': f'Order cannot be cancelled because it is {order.status}'}, status=400)

            # Check if already requested
            if OrderItemCancellation.objects.filter(order_item=item).exists():
                return JsonResponse({'success': False, 'error': 'Cancellation already requested for this item'}, status=400)

            # Calculate refund (assuming full amount for the item)
            refund_amount = item.subtotal

            # Create cancellation record
            cancellation = OrderItemCancellation.objects.create(
                order_item=item,
                order=order,
                customer=request.user,
                product=item.product,
                quantity_cancelled=item.quantity,
                reason=reason,
                other_reason=other_reason,
                status='Pending',
                refund_amount=refund_amount,
                refund_status='Pending',
                is_partial_cancel=True
            )

            # Update item status
            item.status = 'Cancellation Requested'
            item.save()

            return JsonResponse({'success': True, 'message': 'Cancellation requested successfully.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)


class AdminCancellationsView(UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_superuser or self.request.user.is_staff

    def get(self, request):
        cancellations = OrderItemCancellation.objects.all().order_by('-created_at')
        return render(request, 'admin/cancellations.html', {
            'cancellations': cancellations
        })


@method_decorator(csrf_exempt, name='dispatch')
class AdminProcessCancellationAPIView(UserPassesTestMixin, View):
    def test_func(self):
        return self.request.user.is_superuser or self.request.user.is_staff

    def post(self, request, cancel_id):
        try:
            data = json.loads(request.body)
            action = data.get('action') # 'approve', 'reject', 'refund'
            notes = data.get('notes', '')
            
            cancellation = get_object_or_404(OrderItemCancellation, id=cancel_id)
            
            if action == 'approve':
                cancellation.status = 'Approved'
                cancellation.approved_at = timezone.now()
                cancellation.approved_by = request.user
                cancellation.admin_notes = notes
                cancellation.order_item.status = 'Cancelled'
                cancellation.order_item.save()
            elif action == 'reject':
                cancellation.status = 'Rejected'
                cancellation.admin_notes = notes
                cancellation.order_item.status = 'Pending' # Revert to normal
                cancellation.order_item.save()
            elif action == 'refund':
                cancellation.refund_status = 'Completed'
                cancellation.refund_completed_at = timezone.now()
                cancellation.admin_notes = notes
            else:
                return JsonResponse({'success': False, 'error': 'Invalid action'}, status=400)
                
            cancellation.save()
            
            # Check if all items in order are cancelled
            order = cancellation.order
            all_items_cancelled = all(i.status == 'Cancelled' for i in order.items.all())
            if all_items_cancelled:
                order.status = 'Cancelled'
                order.save()

            return JsonResponse({'success': True, 'message': f'Cancellation {action} processed.'})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)
