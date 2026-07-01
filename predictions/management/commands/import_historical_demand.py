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

        df = pd.read_csv(csv_path, on_bad_lines='skip')
        if options["limit"]:
            df = df.tail(options["limit"])

        time_col = "datetime" if "datetime" in df.columns else "timestamp"
        
        if "hourly_demand_met_mw" in df.columns:
            demand_col = "hourly_demand_met_mw"
        elif "load_mw" in df.columns:
            demand_col = "load_mw"
        elif "actual_demand" in df.columns:
            demand_col = "actual_demand"
        else:
            demand_col = "demand_mw"

        created = 0
        for _, row in df.iterrows():
            ts_val = pd.Timestamp(row[time_col]).floor("15min")
            if ts_val.tzinfo is not None:
                ts_val = ts_val.tz_convert(django_tz.get_current_timezone()).tz_localize(None)
            ts_naive = ts_val.to_pydatetime()
            ts = django_tz.make_aware(ts_naive, django_tz.get_current_timezone())
            demand = float(row[demand_col])
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
