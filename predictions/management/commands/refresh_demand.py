from django.core.management.base import BaseCommand

from predictions.services.predictor import StatePredictor, refresh_all_states


class Command(BaseCommand):
    help = "Fetch live demand and run prediction for one or all states"

    def add_arguments(self, parser):
        parser.add_argument(
            "--state",
            type=str,
            help="State code (e.g. mp). If omitted, refreshes all active states.",
        )

    def handle(self, *args, **options):
        state_code = options.get("state")
        if state_code:
            result = StatePredictor(state_code).predict_now()
            self.stdout.write(self.style.SUCCESS(
                f"{state_code}: predicted={result['predicted_demand']:.1f} MW, "
                f"actual={result.get('actual_demand')}"
            ))
        else:
            results = refresh_all_states()
            for result in results:
                if "error" in result:
                    self.stdout.write(self.style.ERROR(str(result)))
                else:
                    self.stdout.write(self.style.SUCCESS(
                        f"predicted={result['predicted_demand']:.1f} MW, "
                        f"actual={result.get('actual_demand')}"
                    ))
