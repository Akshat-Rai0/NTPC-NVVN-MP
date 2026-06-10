from django.urls import path

from predictions.api import views

urlpatterns = [
    path("states/", views.list_states, name="api-states"),
    path("states/<str:code>/today/", views.today_view, name="api-today"),
    path("states/<str:code>/tomorrow/", views.tomorrow_view, name="api-tomorrow"),
    path("states/<str:code>/forecast/", views.forecast_view, name="api-forecast"),
    path("states/<str:code>/history/", views.history_view, name="api-history"),
]
