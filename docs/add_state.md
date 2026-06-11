# How to Add a New State

The system is designed to dynamically load states from the database and configuration files. Because of this, **you do not need to modify any existing Python code** to add a new state. 

Instead, you just need to provide the model, a YAML configuration, and run a command. Here are the exact steps and paths:

### Step 1: Add the Trained Model File
1. Train a LightGBM model expecting the 9 required features in order (`temp_weighted`, `month`, `holiday`, `is_weekend`, `hour`, `minute`, `y_lag_24h`, `y_lag_7d`, `y_lag_1`).
2. Create a new directory for your state inside the `models/` folder.
3. Save the trained model text file in that directory.
   - **Exact File Path:** `models/[state_code]/lgbm_final.txt` 
   - **Example for Gujarat (gj):** `models/gj/lgbm_final.txt`

### Step 2: Create the State Configuration YAML
1. You must define the state's settings (like MERIT URL, cities for weather weights, etc.) in a new YAML file.
2. **Exact File Path:** `config/states/[state_code].yaml` 
   - **Example for Gujarat:** `config/states/gj.yaml`
3. Create the file and add your state's configuration. Here is an example content for Gujarat:
```yaml
code: gj
name: Gujarat
merit_state_code: GJD
merit_url: https://meritindia.in/StateWiseDetails/BindCurrentStateStatus?StateCode=GJD
model_path: models/gj/lgbm_final.txt
fallback_demand_mw: 18000
timezone: Asia/Kolkata
is_active: true
cities:
  ahmedabad:
    lat: 23.0225
    lon: 72.5714
    weight: 0.35
  surat:
    lat: 21.1702
    lon: 72.8311
    weight: 0.25
  vadodara:
    lat: 22.3072
    lon: 73.1812
    weight: 0.20
  rajkot:
    lat: 22.3039
    lon: 70.8022
    weight: 0.20
```

### Step 3: Register the State in the Database
Now, you need to tell Django to parse the YAML file and save it to the database.
1. Open your terminal and ensure you are in the project root: `/Users/bipinkumarrai/Desktop/NTPC-NVVN-MP`.
2. Run the `seed_state` management command:
```bash
python manage.py seed_state config/states/gj.yaml
```
*Behind the scenes: This command triggers `StateRegistry.upsert_from_yaml` (located at `predictions/services/registry.py:74`) which safely inserts or updates the database `State` model.*

### Step 4: Import Historical Demand (Optional but Recommended)
For lag features to work accurately right away, import past demand if you have it.
1. Run the following command from the project root:
```bash
python manage.py import_historical_demand --state gj --csv path/to/gujarat_demand.csv --limit 0
```
*Note: Your CSV must contain `datetime` and `hourly_demand_met_mw` columns.*

### Step 5: Refresh Live Demand
Finally, to trigger the first live prediction for your new state, run:
```bash
python manage.py refresh_demand --state gj
```

### Summary
Because the architecture relies on the `StateRegistry` mapping (`predictions/services/registry.py`), there are **no exact lines in Python files to change**. The predictor (`predictions/services/predictor.py`) dynamically reads the `model_path` and `cities` from the registered `StateConfig`.

Once Step 3 is complete, your state will automatically appear in the dashboard dropdown, the admin panel, and the API endpoints!
