from django.core.management.base import BaseCommand
import subprocess
import sys


class Command(BaseCommand):
    help = 'Run Celery worker for background task processing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--loglevel',
            type=str,
            default='info',
            help='Logging level (debug, info, warning, error)'
        )
        parser.add_argument(
            '--concurrency',
            type=int,
            default=4,
            help='Number of concurrent worker processes'
        )
        parser.add_argument(
            '--queues',
            type=str,
            default='celery',
            help='Comma-separated list of queues to process'
        )

    def handle(self, *args, **options):
        loglevel = options['loglevel']
        concurrency = options['concurrency']
        queues = options['queues']
        
        self.stdout.write(self.style.SUCCESS('Starting Celery worker...'))
        self.stdout.write(f'Log level: {loglevel}')
        self.stdout.write(f'Concurrency: {concurrency}')
        self.stdout.write(f'Queues: {queues}')
        
        cmd = [
            'celery',
            '-A', 'carbon_reform_scraper',
            'worker',
            '--loglevel', loglevel,
            '--concurrency', str(concurrency),
            '--queues', queues
        ]
        
        try:
            subprocess.call(cmd)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\nShutting down worker...'))
            sys.exit(0)