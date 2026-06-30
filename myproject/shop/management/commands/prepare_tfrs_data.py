import os
from django.core.management.base import BaseCommand
from django.conf import settings
from shop.ml.data_pipeline import TFRSDataPipeline

class Command(BaseCommand):
    help = 'Extracts interaction data and prepares TensorFlow Recommenders datasets'

    def add_arguments(self, parser):
        parser.add_argument(
            '--out',
            type=str,
            default=os.path.join(settings.BASE_DIR, 'ml_data', 'datasets'),
            help='Output directory for the saved tf.data.Datasets'
        )

    def handle(self, *args, **kwargs):
        out_dir = kwargs['out']
        self.stdout.write(self.style.SUCCESS(f'Starting TFRS dataset pipeline. Output directory: {out_dir}'))
        
        try:
            pipeline = TFRSDataPipeline()
            pipeline.process_and_save(save_dir=out_dir)
            self.stdout.write(self.style.SUCCESS('Successfully completed TFRS dataset preparation.'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Pipeline failed: {str(e)}'))
