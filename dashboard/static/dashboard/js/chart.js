(() => {
  const REFRESH_MS = 5 * 60 * 1000;
  const SLOTS_PER_DAY = 96;
  const MINUTES_PER_SLOT = 15;

  const COLORS = {
    actual: {
      line: "#16a34a",
      fill: "rgba(22, 163, 74, 0.18)",
    },
    predicted: {
      line: "#2563eb",
      fill: "rgba(37, 99, 235, 0.10)",
    },
    forecast: {
      line: "#ea580c",
      fill: "rgba(234, 88, 12, 0.08)",
    },
  };

  let currentView = "today";
  let currentState = null;
  let chart = null;
  let lastData = null;
  let refreshTimer = null;
  let countdownTimer = null;
  let nextRefreshAt = Date.now() + REFRESH_MS;
  let slotLabels = [];
  let useMw = true;

  const stateSelect = document.getElementById("state-select");
  const datePicker = document.getElementById("date-picker");
  const chartTitle = document.getElementById("chart-title");
  const chartSubtitle = document.getElementById("chart-subtitle");
  const lastUpdated = document.getElementById("last-updated");
  const refreshCountdown = document.getElementById("refresh-countdown");
  const peakLabel = document.getElementById("peak-label");
  const infoTooltip = document.getElementById("info-tooltip");
  const chartPanel = document.getElementById("chart-panel");
  const metricsPanel = document.getElementById("metrics-panel");

  function toDisplayValue(mw) {
    return useMw ? mw : mw / 1000;
  }

  function unitLabel() {
    return useMw ? "MW" : "GW";
  }

  function formatMw(mw) {
    if (mw === null || mw === undefined) return "—";
    return `${Number(mw).toFixed(2)} MW`;
  }

  function pad2(n) {
    return String(n).padStart(2, "0");
  }

  function slotIndex(isoString) {
    const d = new Date(isoString);
    return d.getHours() * 4 + Math.floor(d.getMinutes() / MINUTES_PER_SLOT);
  }

  function formatAxisLabel(hour, minute) {
    const suffix = hour >= 12 ? "p" : "a";
    const hour12 = hour % 12 || 12;
    if (minute === 0) return `${hour12}${suffix}`;
    return `${hour12}:${pad2(minute)}${suffix}`;
  }

  function formatSlotTime(hour, minute) {
    return `${pad2(hour)}:${pad2(minute)}`;
  }

  function buildDayLabels() {
    const labels = [];
    const tooltips = [];
    for (let i = 0; i < SLOTS_PER_DAY; i++) {
      const hour = Math.floor(i / 4);
      const minute = (i % 4) * MINUTES_PER_SLOT;
      labels.push(formatAxisLabel(hour, minute));
      tooltips.push(formatSlotTime(hour, minute));
    }
    slotLabels = tooltips;
    return labels;
  }

  function seriesFromPoints(points, length = SLOTS_PER_DAY) {
    const values = Array(length).fill(null);
    (points || []).forEach((p) => {
      const idx = slotIndex(p.t);
      if (idx >= 0 && idx < length) {
        values[idx] = toDisplayValue(p.mw);
      }
    });
    return values;
  }

  function computeYBounds(seriesList) {
    const values = seriesList.flat().filter((v) => v !== null && !Number.isNaN(v));
    if (!values.length) return {};
    const min = Math.min(...values);
    const max = Math.max(...values);
    const span = max - min || max * 0.1 || 100;
    const pad = span * 0.12;
    return { min: Math.max(0, min - pad), max: max + pad };
  }

  function destroyChart() {
    if (chart) {
      chart.destroy();
      chart = null;
    }
  }

  function baseLineOptions(label, color, fillColor, dashed = false) {
    return {
      label,
      borderColor: color,
      backgroundColor: fillColor,
      fill: !!fillColor,
      tension: 0.35,
      pointRadius: 0,
      pointHoverRadius: 4,
      borderWidth: 2.5,
      borderDash: dashed ? [6, 4] : [],
      spanGaps: false,
    };
  }

  function updateMetrics(data) {
    if (currentView !== "today" || !data.metrics) {
      metricsPanel.classList.add("hidden");
      return;
    }

    metricsPanel.classList.remove("hidden");
    const m = data.metrics;

    document.getElementById("metric-live-load").textContent =
      m.live_load_mw != null ? formatMw(m.live_load_mw) : "—";
    document.getElementById("metric-live-window").textContent =
      m.live_window || "No live data yet";

    document.getElementById("metric-current-pred").textContent =
      m.current_predicted_mw != null ? formatMw(m.current_predicted_mw) : "—";
    document.getElementById("metric-current-temp").textContent =
      m.current_temp_c != null ? `${m.current_temp_c}°C` : "—";

    document.getElementById("metric-peak-pred").textContent =
      m.predicted_peak_mw != null ? formatMw(m.predicted_peak_mw) : "—";
    const peakParts = [];
    if (m.predicted_peak_time) peakParts.push(`Peak at ${m.predicted_peak_time}`);
    if (m.predicted_peak_temp_c != null) peakParts.push(`${m.predicted_peak_temp_c}°C`);
    document.getElementById("metric-peak-detail").textContent =
      peakParts.length ? peakParts.join(" · ") : "—";

    document.getElementById("metric-avg-mape").textContent =
      m.avg_mape_pct != null ? `${m.avg_mape_pct.toFixed(2)} %` : "—";

    document.getElementById("metric-active-mape").textContent =
      m.active_mape_pct != null ? `${m.active_mape_pct.toFixed(2)} %` : "—";
    document.getElementById("metric-active-window").textContent =
      m.active_window || "—";
  }

  function renderChart(data) {
    destroyChart();
    lastData = data;
    useMw = data.unit !== "GW";
    const ctx = document.getElementById("demand-chart").getContext("2d");
    const labels = buildDayLabels();
    const datasets = [];
    let ySeries = [];

    if (currentView === "today") {
      const predicted = seriesFromPoints(data.predicted || data.forecast);
      const actual = data.has_actual_data
        ? seriesFromPoints(data.actual)
        : Array(SLOTS_PER_DAY).fill(null);

      ySeries.push(predicted);
      if (data.has_actual_data) ySeries.push(actual);

      datasets.push({
        ...baseLineOptions(
          "Predicted Load (MW)",
          COLORS.predicted.line,
          COLORS.predicted.fill,
          false,
        ),
        data: predicted,
        order: 2,
      });

      if (data.has_actual_data) {
        datasets.push({
          ...baseLineOptions(
            "Actual Load (MW)",
            COLORS.actual.line,
            COLORS.actual.fill,
            false,
          ),
          data: actual,
          order: 1,
        });
      }

      (data.prior_7_days || []).forEach((day, idx) => {
        const prior = seriesFromPoints(day.points);
        datasets.push({
          label: day.label,
          data: prior,
          borderColor: `rgba(120, 120, 120, ${0.3 - idx * 0.025})`,
          borderWidth: 1,
          pointRadius: 0,
          pointHoverRadius: 3,
          fill: false,
          tension: 0.35,
          order: 3,
        });
      });

      if (data.peak && data.has_actual_data) {
        const peakIdx = slotIndex(data.peak.timestamp);
        peakLabel.classList.remove("hidden");
        peakLabel.textContent = `peak ${Math.round(data.peak.value_mw).toLocaleString()}`;
        peakLabel.style.left = `${Math.min(85, 8 + (peakIdx / SLOTS_PER_DAY) * 84)}%`;
      } else {
        peakLabel.classList.add("hidden");
      }
    } else if (currentView === "tomorrow" || currentView === "future") {
      const predicted = seriesFromPoints(data.predicted);
      ySeries.push(predicted);
      datasets.push({
        ...baseLineOptions(
          "Predicted Load",
          COLORS.forecast.line,
          COLORS.forecast.fill,
          true,
        ),
        data: predicted,
      });
      peakLabel.classList.add("hidden");
    } else if (currentView === "history") {
      const actual = seriesFromPoints(data.actual);
      const predicted = seriesFromPoints(data.predicted);
      ySeries.push(actual, predicted);
      if (actual.some((v) => v !== null)) {
        datasets.push({
          ...baseLineOptions("Actual Load", COLORS.actual.line, COLORS.actual.fill),
          data: actual,
        });
      }
      datasets.push({
        ...baseLineOptions("Predicted Load", COLORS.predicted.line, null, true),
        data: predicted,
      });
      peakLabel.classList.add("hidden");
    }

    const yBounds = computeYBounds(ySeries);

    const annotations = {};
    if (currentView === "today" && data.now && data.has_actual_data) {
      const nowIdx = slotIndex(data.now);
      annotations.nowLine = {
        type: "line",
        xMin: nowIdx,
        xMax: nowIdx,
        borderColor: "#999",
        borderWidth: 1,
        borderDash: [4, 4],
        label: {
          display: true,
          content: "now",
          position: "start",
          backgroundColor: "transparent",
          color: "#666",
          font: { size: 11 },
        },
      };
    }

    chart = new Chart(ctx, {
      type: "line",
      data: { labels, datasets },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "index", intersect: false },
        plugins: {
          legend: {
            display: true,
            position: "bottom",
            labels: { boxWidth: 12, font: { size: 11 } },
          },
          annotation: { annotations },
          tooltip: {
            callbacks: {
              title(items) {
                const idx = items[0]?.dataIndex ?? 0;
                return slotLabels[idx] || labels[idx];
              },
              label(ctx) {
                if (ctx.parsed.y === null) return null;
                const mw = useMw ? ctx.parsed.y : ctx.parsed.y * 1000;
                return `${ctx.dataset.label}: ${Math.round(mw).toLocaleString()} MW`;
              },
            },
          },
        },
        scales: {
          x: {
            grid: {
              display: true,
              color: (ctx) => (ctx.index % 4 === 0 ? "rgba(0,0,0,0.06)" : "rgba(0,0,0,0.02)"),
            },
            ticks: {
              maxRotation: 0,
              autoSkip: false,
              maxTicksLimit: SLOTS_PER_DAY,
              callback(val, index) {
                if (index % 16 === 0) return labels[index];
                if (index % 4 === 0) return "·";
                return "";
              },
              font: { size: 11 },
              color: "#666",
            },
          },
          y: {
            title: { display: true, text: unitLabel(), color: "#666", font: { size: 11 } },
            grid: { color: "#ddd", borderDash: [2, 4] },
            ticks: {
              font: { size: 11 },
              color: "#666",
              callback: (v) => (useMw ? Math.round(v) : v.toFixed(1)),
            },
            ...yBounds,
          },
        },
      },
    });
  }

  async function fetchStates() {
    const res = await fetch("/api/states/");
    const data = await res.json();
    stateSelect.innerHTML = "";
    data.states.forEach((s) => {
      const opt = document.createElement("option");
      opt.value = s.code;
      opt.textContent = s.name;
      stateSelect.appendChild(opt);
    });
    currentState = data.states[0]?.code;
  }

  function apiUrl() {
    if (currentView === "today") {
      return `/api/states/${currentState}/today/`;
    }
    if (currentView === "tomorrow") {
      return `/api/states/${currentState}/tomorrow/`;
    }
    if (currentView === "future") {
      return `/api/states/${currentState}/forecast/?date=${datePicker.value}`;
    }
    return `/api/states/${currentState}/history/?date=${datePicker.value}`;
  }

  async function loadData() {
    if (!currentState) return;
    if ((currentView === "future" || currentView === "history") && !datePicker.value) {
      return;
    }

    try {
      const res = await fetch(apiUrl());
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.error || "Failed to load data");
      }
      const data = await res.json();
      chartTitle.textContent = data.title || "Power demand";
      if (chartSubtitle) {
        chartSubtitle.textContent = data.subtitle || "";
      }
      updateMetrics(data);
      renderChart(data);
      lastUpdated.textContent = `Last updated: ${new Date().toLocaleTimeString()}`;
      nextRefreshAt = Date.now() + REFRESH_MS;
    } catch (err) {
      console.error(err);
      lastUpdated.textContent = `Error: ${err.message}`;
    }
  }

  function setupDatePicker() {
    const today = new Date();
    const tomorrow = new Date(today);
    tomorrow.setDate(today.getDate() + 1);
    const yesterday = new Date(today);
    yesterday.setDate(today.getDate() - 1);

    if (currentView === "future") {
      datePicker.classList.remove("hidden");
      datePicker.min = tomorrow.toISOString().slice(0, 10);
      const max = new Date(today);
      max.setDate(today.getDate() + 16);
      datePicker.max = max.toISOString().slice(0, 10);
      datePicker.value = tomorrow.toISOString().slice(0, 10);
    } else if (currentView === "history") {
      datePicker.classList.remove("hidden");
      datePicker.max = yesterday.toISOString().slice(0, 10);
      datePicker.min = "2024-01-01";
      datePicker.value = yesterday.toISOString().slice(0, 10);
    } else {
      datePicker.classList.add("hidden");
    }

    if (currentView !== "today") {
      metricsPanel.classList.add("hidden");
    }
  }

  function setupRefreshTimer() {
    if (refreshTimer) clearInterval(refreshTimer);
    if (currentView === "today") {
      refreshTimer = setInterval(loadData, REFRESH_MS);
    }
  }

  function setupCountdown() {
    if (countdownTimer) clearInterval(countdownTimer);
    countdownTimer = setInterval(() => {
      if (currentView !== "today") {
        refreshCountdown.textContent = "";
        return;
      }
      const remaining = Math.max(0, nextRefreshAt - Date.now());
      const mins = Math.floor(remaining / 60000);
      const secs = Math.floor((remaining % 60000) / 1000);
      refreshCountdown.textContent = `Next refresh in ${mins}:${String(secs).padStart(2, "0")}`;
    }, 1000);
  }

  function downloadCsv() {
    if (!lastData) return;
    const rows = [["timestamp", "mw", "type"]];
    const append = (points, type) => {
      (points || []).forEach((p) => rows.push([p.t, p.mw, type]));
    };
    if (currentView === "today") {
      append(lastData.actual, "actual");
      append(lastData.predicted, "predicted");
    } else if (currentView === "history") {
      append(lastData.actual, "actual");
      append(lastData.predicted, "predicted");
    } else {
      append(lastData.predicted, "predicted");
    }
    const csv = rows.map((r) => r.join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `demand_${currentState}_${currentView}.csv`;
    a.click();
  }

  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((t) => t.classList.remove("active"));
      tab.classList.add("active");
      currentView = tab.dataset.view;
      setupDatePicker();
      setupRefreshTimer();
      loadData();
    });
  });

  stateSelect.addEventListener("change", () => {
    currentState = stateSelect.value;
    loadData();
  });

  datePicker.addEventListener("change", loadData);

  document.getElementById("btn-info").addEventListener("click", () => {
    infoTooltip.classList.toggle("hidden");
  });

  document.getElementById("btn-download").addEventListener("click", downloadCsv);

  document.getElementById("btn-fullscreen").addEventListener("click", () => {
    chartPanel.classList.toggle("fullscreen");
    if (chart) chart.resize();
  });

  async function init() {
    await fetchStates();
    setupDatePicker();
    setupRefreshTimer();
    setupCountdown();
    await loadData();
  }

  init();
})();
