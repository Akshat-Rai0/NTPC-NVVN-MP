import openmeteo_requests

import pandas as pd
import requests_cache
from retry_requests import retry
import numpy as np

# Setup the Open-Meteo API client with cache and retry on error
cache_session = requests_cache.CachedSession('.cache', expire_after = 3600)
retry_session = retry(cache_session, retries = 5, backoff_factor = 0.2)
openmeteo = openmeteo_requests.Client(session = retry_session)

# Cities with coordinates and weights
cities = {
    "indore": {"lat": 22.7196, "lon": 75.8577, "weight": 0.292095},
    "bhopal": {"lat": 23.1815, "lon": 79.9864, "weight": 0.21238938},
    "jabalpur": {"lat": 23.1815, "lon": 79.9864, "weight": 0.15929204},
    "gwalior": {"lat": 26.2183, "lon": 78.1629, "weight": 0.12389381},
    "ujjain": {"lat": 23.1815, "lon": 75.7845, "weight": 0.09734513},
    "singrauli": {"lat": 24.1833, "lon": 82.6667, "weight": 0.11504425},
}

url = "https://api.open-meteo.com/v1/forecast"

# Fetch weather for all cities
all_temperatures = {}
for city_name, city_data in cities.items():
    params = {
        "latitude": city_data["lat"],
        "longitude": city_data["lon"],
        "minutely_15": "apparent_temperature",
        "forecast_minutely_15": 96,
    }
    
    responses = openmeteo.weather_api(url, params = params)
    response = responses[0]
    
    minutely_15 = response.Minutely15()
    temperatures = minutely_15.Variables(0).ValuesAsNumpy()
    
    all_temperatures[city_name] = {
        "temperatures": temperatures,
        "weight": city_data["weight"]
    }
    
    print(f"{city_name.upper()}: Coordinates {response.Latitude()}°N {response.Longitude()}°E")

# Calculate weighted temperature
time_index = all_temperatures["indore"]["temperatures"].shape[0]
weighted_temps = np.zeros(time_index)

for city_name, data in all_temperatures.items():
    weighted_temps += data["temperatures"] * data["weight"]

print(f"\nWeighted Temperature (List): {weighted_temps.tolist()}")

# Create DataFrame with weighted results
minutely_15 = responses[0].Minutely15()
df = pd.DataFrame({
    "datetime": pd.date_range(
        start = pd.to_datetime(minutely_15.Time(), unit = "s", utc = True),
        periods = len(weighted_temps),
        freq = pd.Timedelta(seconds = minutely_15.Interval()),
    ),
    "weighted_apparent_temperature": weighted_temps
})

print("\nWeighted Temperature Data\n", df)