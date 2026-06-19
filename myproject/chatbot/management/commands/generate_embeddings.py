"""
Management command to generate product embeddings.

Usage:
    python manage.py generate_embeddings           # Only new products
    python manage.py generate_embeddings --all      # Regenerate all
"""

from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Generate vector embeddings for products using BAAI/bge-small-en-v1.5'

    def add_arguments(self, parser):
        parser.add_argument(
            '--all',
            action='store_true',
            help='Regenerate embeddings for ALL products (including existing ones)'
        )
        parser.add_argument(
            '--batch-size',
            type=int,
            default=50,
            help='Batch size for embedding generation (default: 50)'
        )

    def handle(self, *args, **options):
        from chatbot.services.embedding_service import (
            generate_all_embeddings,
            regenerate_all_embeddings
        )

        batch_size = options['batch_size']

        if options['all']:
            self.stdout.write(self.style.WARNING(
                'Regenerating ALL product embeddings...'
            ))
            count = regenerate_all_embeddings(batch_size=batch_size)
            self.stdout.write(self.style.SUCCESS(
                f'Successfully regenerated {count} embeddings.'
            ))
        else:
            self.stdout.write(self.style.WARNING(
                'Generating embeddings for new products...'
            ))
            created, skipped = generate_all_embeddings(batch_size=batch_size)
            self.stdout.write(self.style.SUCCESS(
                f'Created: {created}, Skipped (already exist): {skipped}'
            ))
