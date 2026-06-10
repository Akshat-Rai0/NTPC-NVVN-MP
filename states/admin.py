import csv
from io import StringIO

from django.contrib import admin, messages
from django.http import HttpResponse

from states.models import DemandReading, PredictionRecord, State


@admin.register(State)
class StateAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "merit_state_code", "is_active", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("code", "name", "merit_state_code")
    readonly_fields = ("created_at", "updated_at")


@admin.register(DemandReading)
class DemandReadingAdmin(admin.ModelAdmin):
    list_display = ("state", "timestamp", "demand_mw", "source", "created_at")
    list_filter = ("state", "source")
    search_fields = ("state__code", "state__name")
    date_hierarchy = "timestamp"
    actions = ["export_to_csv"]

    @admin.action(description="Export selected to CSV")
    def export_to_csv(self, request, queryset):
        buffer = StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["timestamp", "demand_mw", "source", "state"])
        for row in queryset.order_by("timestamp"):
            writer.writerow([
                row.timestamp.isoformat(),
                row.demand_mw,
                row.source,
                row.state.code,
            ])
        response = HttpResponse(buffer.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="demand_readings.csv"'
        return response


@admin.register(PredictionRecord)
class PredictionRecordAdmin(admin.ModelAdmin):
    list_display = (
        "state",
        "timestamp",
        "actual_demand",
        "predicted_demand",
        "temp_weighted",
        "month",
        "holiday",
        "is_weekend",
        "hour",
        "minute",
        "y_lag_1",
        "y_lag_24h",
        "y_lag_7d",
    )
    list_filter = ("state", "month", "holiday", "is_weekend")
    search_fields = ("state__code", "state__name")
    date_hierarchy = "timestamp"
    actions = ["export_to_csv"]

    @admin.action(description="Export selected to CSV")
    def export_to_csv(self, request, queryset):
        buffer = StringIO()
        writer = csv.writer(buffer)
        writer.writerow([
            "timestamp",
            "actual_demand",
            "predicted_demand",
            "temp_weighted",
            "month",
            "holiday",
            "is_weekend",
            "hour",
            "minute",
            "y_lag_1",
            "y_lag_24h",
            "y_lag_7d",
            "state",
        ])
        for row in queryset.order_by("timestamp"):
            writer.writerow([
                row.timestamp.isoformat(),
                row.actual_demand,
                row.predicted_demand,
                row.temp_weighted,
                row.month,
                row.holiday,
                row.is_weekend,
                row.hour,
                row.minute,
                row.y_lag_1,
                row.y_lag_24h,
                row.y_lag_7d,
                row.state.code,
            ])
        response = HttpResponse(buffer.getvalue(), content_type="text/csv")
        response["Content-Disposition"] = 'attachment; filename="prediction_records.csv"'
        return response
