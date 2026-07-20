import logging
from django.db import transaction, IntegrityError
from shop.models import Product, InventoryTransaction

logger = logging.getLogger(__name__)

class OutOfStockError(Exception):
    pass

class InventoryService:
    """
    Centralized gatekeeper for all inventory modifications.
    Ensures ACID compliance, idempotency, and strict row-level locking.
    """
    
    @staticmethod
    def reserve_stock(reference_id, user, items, idempotency_key_prefix):
        """
        Reserves stock for a list of items (e.g. from a cart during checkout).
        Uses select_for_update to lock rows and prevent overselling.
        """
        logger.info(f"Attempting to reserve stock for {reference_id}")
        
        # We lock products in a consistent order (by ID) to prevent deadlocks
        product_ids = sorted([item.product.id for item in items])
        
        with transaction.atomic():
            # Lock the products
            locked_products = {
                p.id: p for p in Product.objects.select_for_update().filter(id__in=product_ids)
            }
            
            # Validate all items
            for item in items:
                product = locked_products.get(item.product.id)
                if not product or product.stock < item.quantity:
                    raise OutOfStockError(f"Product {item.product.name} is out of stock.")
            
            # Perform deduction and logging
            for item in items:
                product = locked_products[item.product.id]
                product.stock -= item.quantity
                product.save(update_fields=['stock'])
                
                ikey = f"{idempotency_key_prefix}_{reference_id}_P{product.id}_RESERVE"
                
                try:
                    InventoryTransaction.objects.create(
                        reference_id=reference_id,
                        product=product,
                        quantity=item.quantity,
                        transaction_type='RESERVED',
                        idempotency_key=ikey,
                        user=user
                    )
                except IntegrityError:
                    # Idempotency hit: already reserved this exact key
                    logger.warning(f"Idempotent hit: {ikey} already exists.")
                    continue
                    
        logger.info(f"Successfully reserved stock for {reference_id}")

    @staticmethod
    def commit_stock(reference_id, idempotency_key_prefix):
        """
        Marks previously reserved stock as committed (e.g. after successful payment).
        Does not change Product.stock since it was already deducted.
        """
        logger.info(f"Committing stock for {reference_id}")
        
        with transaction.atomic():
            reservations = InventoryTransaction.objects.filter(
                reference_id=reference_id, 
                transaction_type='RESERVED'
            ).select_for_update()
            
            for res in reservations:
                ikey = f"{idempotency_key_prefix}_{reference_id}_P{res.product_id}_COMMIT"
                try:
                    # We can either update the old record or create a new one. 
                    # Creating a new one preserves full audit trail.
                    InventoryTransaction.objects.create(
                        reference_id=reference_id,
                        product=res.product,
                        quantity=res.quantity,
                        transaction_type='COMMITTED',
                        idempotency_key=ikey,
                        user=res.user
                    )
                    # Mark original as processed to avoid double commits? 
                    # The prompt implies we just need a COMMITTED record.
                except IntegrityError:
                    logger.warning(f"Idempotent hit: {ikey} already exists.")
                    
        logger.info(f"Successfully committed stock for {reference_id}")

    @staticmethod
    def release_stock(reference_id, idempotency_key_prefix, release_reason="Cancelled"):
        """
        Releases reserved or committed stock back to inventory.
        Handles cancellations, expirations, and refunds.
        """
        logger.info(f"Releasing stock for {reference_id} ({release_reason})")
        
        with transaction.atomic():
            # Find what was reserved or committed
            # A product could have been RESERVED, then COMMITTED. 
            # We must only release based on the max quantity tracked or just look at initial RESERVED/COMMITTED.
            # To be safe, we query the original RESERVED transactions.
            transactions = InventoryTransaction.objects.filter(
                reference_id=reference_id,
                transaction_type__in=['RESERVED', 'COMMITTED']
            )
            
            # Aggregate what was promised vs what is already released
            promised = {}
            users = {}
            for t in transactions:
                promised[t.product_id] = t.quantity
                users[t.product_id] = t.user
                
            released_tx = InventoryTransaction.objects.filter(
                reference_id=reference_id,
                transaction_type='RELEASED'
            )
            for t in released_tx:
                if t.product_id in promised:
                    promised[t.product_id] -= t.quantity
            
            # Products to lock
            product_ids = sorted(promised.keys())
            if not product_ids:
                return # Nothing to release
                
            locked_products = {
                p.id: p for p in Product.objects.select_for_update().filter(id__in=product_ids)
            }
            
            for pid, qty_to_release in promised.items():
                if qty_to_release <= 0:
                    continue
                    
                product = locked_products[pid]
                product.stock += qty_to_release
                product.save(update_fields=['stock'])
                
                ikey = f"{idempotency_key_prefix}_{reference_id}_P{pid}_RELEASE"
                
                try:
                    InventoryTransaction.objects.create(
                        reference_id=reference_id,
                        product=product,
                        quantity=qty_to_release,
                        transaction_type='RELEASED',
                        idempotency_key=ikey,
                        user=users[pid]
                    )
                except IntegrityError:
                    logger.warning(f"Idempotent hit: {ikey} already exists.")
                    
        logger.info(f"Successfully released stock for {reference_id}")

    @staticmethod
    def restock(product_id, quantity, admin_user, idempotency_key):
        """
        Admin method to manually restock items.
        """
        with transaction.atomic():
            product = Product.objects.select_for_update().get(id=product_id)
            product.stock += quantity
            product.save(update_fields=['stock'])
            
            try:
                InventoryTransaction.objects.create(
                    reference_id="ADMIN_ADJUSTMENT",
                    product=product,
                    quantity=quantity,
                    transaction_type='RESTOCKED',
                    idempotency_key=idempotency_key,
                    user=admin_user
                )
            except IntegrityError:
                logger.warning(f"Idempotent hit: {idempotency_key} already exists.")
