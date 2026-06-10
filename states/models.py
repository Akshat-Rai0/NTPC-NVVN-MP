from django.db import models


class State(models.Model):
    code = models.SlugField(max_length=10, unique=True)
    name = models.CharField(max_length=100)
    merit_state_code = models.CharField(max_length=10)
    merit_url = models.URLField(max_length=500)
    model_path = models.CharField(max_length=500)
    fallback_demand_mw = models.FloatField(default=14500.0)
    timezone = models.CharField(max_length=50, default="Asia/Kolkata")
    cities = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.code})"


class DemandReading(models.Model):
    SOURCE_CHOICES = [
        ("api", "MERIT API"),
        ("predicted", "Predicted"),
        ("import", "Imported"),
    ]

    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name="demand_readings")
    timestamp = models.DateTimeField(db_index=True)
    demand_mw = models.FloatField()
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default="api")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["timestamp"]
        unique_together = [("state", "timestamp")]
        indexes = [
            models.Index(fields=["state", "timestamp"]),
        ]

    def __str__(self):
        return f"{self.state.code} @ {self.timestamp}: {self.demand_mw:.0f} MW"


class PredictionRecord(models.Model):
    state = models.ForeignKey(State, on_delete=models.CASCADE, related_name="predictions")
    timestamp = models.DateTimeField(db_index=True)
    actual_demand = models.FloatField(null=True, blank=True)
    predicted_demand = models.FloatField()
    temp_weighted = models.FloatField()
    month = models.IntegerField()
    holiday = models.IntegerField()
    is_weekend = models.IntegerField()
    hour = models.IntegerField()
    minute = models.IntegerField()
    y_lag_1 = models.FloatField()
    y_lag_24h = models.FloatField()
    y_lag_7d = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["state", "timestamp"]),
        ]

    def __str__(self):
        return f"{self.state.code} @ {self.timestamp}: {self.predicted_demand:.0f} MW"
