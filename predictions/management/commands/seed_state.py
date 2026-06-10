from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from predictions.services.registry import StateRegistry


class Command(BaseCommand):
    help = "Register or update a state from a YAML config file"

    def add_arguments(self, parser):
        parser.add_argument("yaml_path", type=str, help="Path to state YAML config")

    def handle(self, *args, **options):
        path = Path(options["yaml_path"])
        if not path.exists():
            raise CommandError(f"Config not found: {path}")
        state = StateRegistry.upsert_from_yaml(path)
        self.stdout.write(self.style.SUCCESS(
            f"State '{state.name}' ({state.code}) registered/updated."
        ))
