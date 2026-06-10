from pathlib import Path

import pandas as pd
from django.core.management.base import BaseCommand
from django.utils import timezone as django_tz

from predictions.services.registry import StateRegistry
from states.models import DemandReading


class Command(BaseCommand):
    help = "Import historical demand from Final dataset.csv for lag features"

    def add_arguments(self, parser):
        parser.add_argument("--state", type=str, default="mp")
        parser.add_argument(
            "--csv",
            type=str,
            default="data/Final dataset.csv",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Max rows to import (0 = all)",
        )

    def handle(self, *args, **options):
        state = StateRegistry.upsert_from_yaml(
            Path("config/states") / f"{options['state']}.yaml"
        )
        csv_path = Path(options["csv"])
        if not csv_path.exists():
            self.stdout.write(self.style.WARNING(f"CSV not found: {csv_path}"))
            return

        df = pd.read_csv(csv_path, parse_dates=["datetime"])
        if options["limit"]:
            df = df.tail(options["limit"])

        created = 0
        for _, row in df.iterrows():
            ts_naive = pd.Timestamp(row["datetime"]).floor("15min").to_pydatetime()
            ts = django_tz.make_aware(ts_naive, django_tz.get_current_timezone())
            demand = float(row["hourly_demand_met_mw"])
            _, was_created = DemandReading.objects.update_or_create(
                state=state,
                timestamp=ts,
                defaults={"demand_mw": demand, "source": "import"},
            )
            if was_created:
                created += 1

        self.stdout.write(self.style.SUCCESS(
            f"Imported demand readings for {state.code}: {created} new rows "
            f"({len(df)} total processed)"
        ))
