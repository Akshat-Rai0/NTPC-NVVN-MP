"""
MP Temperature Weighted Average Analysis
-----------------------------------------
Computes weighted avg of 5 district temperatures,
compares with Bhopal, gives deviation stats + plots.
"""

import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np

# ─────────────────────────────────────────────
# LOAD DATA
# ─────────────────────────────────────────────
df = pd.read_csv("combined_mp_power_weather.csv", parse_dates=["time"])
df = df.sort_values("time").reset_index(drop=True)

print(f"Loaded: {len(df)} rows | {df['time'].min()} → {df['time'].max()}")
print(f"Columns: {list(df.columns)}\n")

# ─────────────────────────────────────────────
# CITY WEIGHTS
# Based on population + industrial load
# ─────────────────────────────────────────────
WEIGHTS = {
    "apparent_temperature_bhopal":     0.21238938,
    "apparent_temperature_gwalior":    0.12389381,
    "apparent_temperature_indore":     0.292095,   # largest city, most load
    "apparent_temperature_jabalpur":   0.15929204,
    "apparent_temperature_singrauli":  0.11504425,   # industrial but smaller population
    "apparent_temperature_ujjain":     0.09734513,
}

# Auto-normalize so they always sum to 1
total = sum(WEIGHTS.values())
WEIGHTS = {k: v / total for k, v in WEIGHTS.items()}

# Verify
print("Weights sum:", sum(WEIGHTS.values()))  # should print 1.0

# ─────────────────────────────────────────────
# COMPUTE AVERAGES
# ─────────────────────────────────────────────
non_bhopal_cols = [c for c in WEIGHTS if c != "apparent_temperature_bhopal"]

df["simple_avg_5cities"] = df[non_bhopal_cols].mean(axis=1)
df["simple_avg_all6"]    = df[list(WEIGHTS.keys())].mean(axis=1)
df["weighted_avg"]       = sum(df[col] * w for col, w in WEIGHTS.items())

# ─────────────────────────────────────────────
# DEVIATION FROM BHOPAL
# ─────────────────────────────────────────────
df["dev_simple5"]     = df["simple_avg_5cities"] - df["apparent_temperature_bhopal"]
df["dev_simple_all6"] = df["simple_avg_all6"]    - df["apparent_temperature_bhopal"]
df["dev_weighted"]    = df["weighted_avg"]        - df["apparent_temperature_bhopal"]

# ─────────────────────────────────────────────
# STATS
# ─────────────────────────────────────────────
print("=" * 60)
print("  DEVIATION FROM BHOPAL — SUMMARY STATS")
print("=" * 60)

strategies = {
    "Simple avg (5 cities, excl. Bhopal)": "dev_simple5",
    "Simple avg (all 6 incl. Bhopal)":     "dev_simple_all6",
    "Weighted avg (all 6)":                "dev_weighted",
}

for label, col in strategies.items():
    mae  = df[col].abs().mean()
    mean = df[col].mean()
    std  = df[col].std()
    maxd = df[col].abs().max()
    p95  = df[col].abs().quantile(0.95)
    print(f"\n  {label}")
    print(f"    MAE (mean absolute error) : {mae:.3f} °C")
    print(f"    Mean bias (+ = warmer)    : {mean:+.3f} °C")
    print(f"    Std deviation             : {std:.3f} °C")
    print(f"    Max absolute deviation    : {maxd:.3f} °C")
    print(f"    95th percentile dev       : {p95:.3f} °C")

print("\n" + "=" * 60)
print("  DECISION GUIDE")
print("=" * 60)
mae_w = df["dev_weighted"].abs().mean()
if mae_w < 1.5:
    verdict = "✓ LOW  — Bhopal alone is representative. Single point is fine."
elif mae_w < 3.0:
    verdict = "~ MODERATE — Weighted avg adds meaningful accuracy. Use it."
else:
    verdict = "✗ HIGH — Consider zonal segmentation (North/Central/South MP)."
print(f"\n  Weighted avg MAE = {mae_w:.2f}°C")
print(f"  {verdict}\n")

print("  INDIVIDUAL CITY vs BHOPAL:")
for col in non_bhopal_cols:
    city = col.replace("apparent_temperature_", "").capitalize()
    diff = df[col] - df["apparent_temperature_bhopal"]
    print(f"    {city:<12} MAE: {diff.abs().mean():.2f}°C  |  Bias: {diff.mean():+.2f}°C")

print("=" * 60)

# ─────────────────────────────────────────────
# SAVE OUTPUT CSV
# ─────────────────────────────────────────────
output_cols = [
    "time", "State", "hourly_demand_met_mw",
    "apparent_temperature_bhopal",
    "apparent_temperature_gwalior",
    "apparent_temperature_indore",
    "apparent_temperature_jabalpur",
    "apparent_temperature_singrauli",
    "apparent_temperature_ujjain",
    "simple_avg_5cities",
    "simple_avg_all6",
    "weighted_avg",
    "dev_simple5",
    "dev_simple_all6",
    "dev_weighted",
]
df[output_cols].to_csv("mp_temp_with_avg.csv", index=False)
print("\n  Saved: mp_temp_with_avg.csv")

# ─────────────────────────────────────────────
# PLOTS
# ─────────────────────────────────────────────
daily = df.set_index("time").resample("D").mean(numeric_only=True)

fig, axes = plt.subplots(3, 1, figsize=(15, 14))
fig.suptitle("MP Temperature Strategy Comparison vs Bhopal", fontsize=14, fontweight="bold")

# Plot 1: Temperature lines
ax1 = axes[0]
ax1.plot(daily.index, daily["apparent_temperature_bhopal"], label="Bhopal (baseline)",    color="#e74c3c", linewidth=1.5)
ax1.plot(daily.index, daily["simple_avg_all6"],             label="Simple avg (all 6)",   color="#3498db", linewidth=1.2, linestyle="--")
ax1.plot(daily.index, daily["weighted_avg"],                label="Weighted avg (all 6)", color="#2ecc71", linewidth=1.2, linestyle=":")
ax1.set_ylabel("Apparent Temperature (°C)")
ax1.set_title("Daily Average — Bhopal vs Computed Averages")
ax1.legend()
ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
ax1.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
plt.setp(ax1.xaxis.get_majorticklabels(), rotation=30)
ax1.grid(True, alpha=0.3)

# Plot 2: Deviation over time
ax2 = axes[1]
ax2.plot(daily.index, daily["dev_simple_all6"], label="Simple avg deviation", color="#3498db", linewidth=1)
ax2.plot(daily.index, daily["dev_weighted"],    label="Weighted avg deviation",color="#2ecc71", linewidth=1)
ax2.axhline(0,    color="gray",   linestyle="-",  linewidth=0.8)
ax2.axhline(1.5,  color="orange", linestyle="--", linewidth=1, label="±1.5°C")
ax2.axhline(-1.5, color="orange", linestyle="--", linewidth=1)
ax2.axhline(3.0,  color="red",    linestyle="--", linewidth=1, label="±3.0°C")
ax2.axhline(-3.0, color="red",    linestyle="--", linewidth=1)
ax2.fill_between(daily.index, daily["dev_weighted"], 0, alpha=0.1, color="#2ecc71")
ax2.set_ylabel("Deviation from Bhopal (°C)")
ax2.set_title("Daily Deviation from Bhopal")
ax2.legend()
ax2.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
ax2.xaxis.set_major_locator(mdates.MonthLocator(interval=2))
plt.setp(ax2.xaxis.get_majorticklabels(), rotation=30)
ax2.grid(True, alpha=0.3)

# Plot 3: Monthly MAE bars
ax3 = axes[2]
monthly = df.set_index("time").resample("ME").mean(numeric_only=True)
month_labels = monthly.index.strftime("%b %Y")
x = np.arange(len(monthly))
w = 0.35
ax3.bar(x - w/2, monthly["dev_simple_all6"].abs(), width=w, label="Simple avg vs Bhopal",   color="#3498db", alpha=0.8)
ax3.bar(x + w/2, monthly["dev_weighted"].abs(),    width=w, label="Weighted avg vs Bhopal", color="#2ecc71", alpha=0.8)
ax3.axhline(1.5, color="orange", linestyle="--", linewidth=1, label="1.5°C")
ax3.axhline(3.0, color="red",    linestyle="--", linewidth=1, label="3.0°C")
ax3.set_xticks(x)
ax3.set_xticklabels(month_labels, rotation=45, ha="right", fontsize=8)
ax3.set_ylabel("Mean Absolute Deviation (°C)")
ax3.set_title("Monthly Average Deviation from Bhopal")
ax3.legend()
ax3.grid(True, alpha=0.3, axis="y")

plt.tight_layout()
plt.savefig("mp_temp_comparison.png", dpi=150, bbox_inches="tight")
print("  Saved: mp_temp_comparison.png")
plt.show()