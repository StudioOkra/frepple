from django.core.management.base import BaseCommand
from freppledb.scheduler.scheduler import SchedulerEngine

class Command(BaseCommand):
    help = "Run the scheduler"

    def add_arguments(self, parser):
        parser.add_argument(
            "--forward",
            action="store_true",
            help="Use forward scheduling (default is backward)",
        )
        parser.add_argument(
            "--start",
            help="Scheduling horizon start date",
        )
        parser.add_argument(
            "--end",
            help="Scheduling horizon end date",
        )

    def handle(self, *args, **options):
        scheduler = SchedulerEngine(
            horizon_start=options["start"],
            horizon_end=options["end"],
            forward=options["forward"]
        )
        scheduler.solve()
