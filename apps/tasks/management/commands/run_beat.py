from django.core.management.base import BaseCommand
import subprocess
import sys


class Command(BaseCommand):
    help = 'Run Celery beat scheduler for periodic tasks'

    def add_arguments(self, parser):
        parser.add_argument(
            '--loglevel',
            type=str,
            default='info',
            help='Logging level (debug, info, warning, error)'
        )
        parser.add_argument(
            '--scheduler',
            type=str,
            default='django_celery_beat.schedulers:DatabaseScheduler',
            help='Scheduler class to use'
        )

    def handle(self, *args, **options):
        loglevel = options['loglevel']
        scheduler = options['scheduler']
        
        self.stdout.write(self.style.SUCCESS('Starting Celery beat scheduler...'))
        self.stdout.write(f'Log level: {loglevel}')
        self.stdout.write(f'Scheduler: {scheduler}')
        
        cmd = [
            'celery',
            '-A', 'carbon_reform_scraper',
            'beat',
            '--loglevel', loglevel,
            '--scheduler', scheduler
        ]
        
        try:
            subprocess.call(cmd)
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\nShutting down beat scheduler...'))
            sys.exit(0)