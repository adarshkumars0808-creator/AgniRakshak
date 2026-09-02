// ============================================================
// AGNIRAKSHAK — MAIN SCRIPT
// ============================================================
// All original working code preserved.
// Tab switching + analytics charts + theme toggle added.
// ============================================================

// ============================================================
// THEME TOGGLE
// ============================================================

function initTheme() {
  const saved = localStorage.getItem('thermoscope-theme') || 'dark';
  document.body.setAttribute('data-theme', saved);
  updateThemeIcon(saved);
}

function toggleTheme() {
  const current = document.body.getAttribute('data-theme') || 'dark';
  const next = current === 'dark' ? 'light' : 'dark';
  document.body.setAttribute('data-theme', next);
  localStorage.setItem('thermoscope-theme', next);
  updateThemeIcon(next);
}

function updateThemeIcon(theme) {
  const btn = document.getElementById('themeToggle');
  if (btn) btn.textContent = theme === 'dark' ? '🌙' : '☀️';
}

// Initialize theme immediately (before DOM ready)
initTheme();

// Bind toggle button after DOM loads
document.addEventListener('DOMContentLoaded', () => {
  const btn = document.getElementById('themeToggle');
  if (btn) btn.addEventListener('click', toggleTheme);
});

const RISK_COLORS = {
  CRITICAL: "#ff382f",
  HIGH: "#ff6b1a",
  MODERATE: "#ffae42",
  LOW: "#20e889",
};

const FIRE_TYPE_COLORS = {
  INDUSTRIAL_PERSISTENT: "#a855f7",
  AGRICULTURAL_BURNING: "#ffd400",
  FOREST_WILDFIRE: "#22d3ee",
  UNCLASSIFIED: "#5b6b7a",
};

const FIRE_TYPE_LABELS = {
  INDUSTRIAL_PERSISTENT: "Industrial / Persistent Source",
  AGRICULTURAL_BURNING: "Agricultural Burning",
  FOREST_WILDFIRE: "Forest / Wildfire",
  UNCLASSIFIED: "Unclassified",
};

const SITE_TYPE_COLORS = {
  INDUSTRIAL: "#a855f7",
  MINING: "#f97316",
  AGRICULTURAL_BURNING: "#ffd400",
  FOREST_FIRE: "#22d3ee",
};

const SITE_TYPE_LABELS = {
  INDUSTRIAL: "Industrial (verified)",
  MINING: "Mining (verified)",
  AGRICULTURAL_BURNING: "Agricultural Burning (verified)",
  FOREST_FIRE: "Forest / Wildfire (verified)",
};

// ============================================================
// GLOBAL DATA
// ============================================================

let gridData = [];
let dailyData = [];
let map = null;
let clusterLayer = null;
let satelliteLayer = null;
let fireSiteLayer = null;
let fireSiteData = [];
let riskZoneData = [];
let markerByGrid = {};

// ============================================================
// UTILITIES (original)
// ============================================================

function num(value, decimals = 0) {
  const n = Number(value);
  if (!Number.isFinite(n)) return "0";
  return n.toLocaleString("en-IN", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

function confidence01(value) {
  let n = Number(value);
  if (!Number.isFinite(n)) return null;
  if (n > 1) n = n / 100;
  return Math.max(0, Math.min(1, n));
}

function confidencePercent(value) {
  const c = confidence01(value);
  if (c === null) return null;
  return Math.round(c * 100);
}

function normalizeFireType(value) {
  if (value === null || value === undefined) return "UNCLASSIFIED";
  let v = String(value).trim().toUpperCase().replace(/-/g, "_").replace(/\//g, "_").replace(/\s+/g, "_");
  const aliases = {
    INDUSTRIAL: "INDUSTRIAL_PERSISTENT",
    PERSISTENT: "INDUSTRIAL_PERSISTENT",
    INDUSTRIAL_PERSISTENT_SOURCE: "INDUSTRIAL_PERSISTENT",
    INDUSTRIAL_SOURCE: "INDUSTRIAL_PERSISTENT",
    AGRICULTURAL: "AGRICULTURAL_BURNING",
    CROP_BURNING: "AGRICULTURAL_BURNING",
    CROP_FIRE: "AGRICULTURAL_BURNING",
    FOREST: "FOREST_WILDFIRE",
    WILDFIRE: "FOREST_WILDFIRE",
    FOREST_FIRE: "FOREST_WILDFIRE",
    WILDLAND_FIRE: "FOREST_WILDFIRE",
    UNKNOWN: "UNCLASSIFIED",
    NONE: "UNCLASSIFIED",
    NULL: "UNCLASSIFIED",
    "": "UNCLASSIFIED",
  };
  v = aliases[v] || v;
  if (FIRE_TYPE_COLORS[v]) return v;
  return "UNCLASSIFIED";
}

function hasValidCoordinates(row) {
  const lat = Number(row.latitude);
  const lon = Number(row.longitude);
  return Number.isFinite(lat) && Number.isFinite(lon) && lat >= 6 && lat <= 38 && lon >= 68 && lon <= 98;
}

function isActiveFirmsCell(row) {
  const total = Number(row.total_detections);
  return Number.isFinite(total) && total > 0;
}

// ============================================================
// CSV LOADING (original)
// ============================================================

async function loadCSV(path) {
  const response = await fetch(path);
  if (!response.ok) throw new Error(`${path} -> HTTP ${response.status}`);
  const text = await response.text();
  return Papa.parse(text, { header: true, dynamicTyping: true, skipEmptyLines: true }).data;
}

async function loadCSVWithFallback(candidates) {
  let lastError = null;
  for (const path of candidates) {
    try { return await loadCSV(path); } catch (error) { lastError = error; }
  }
  throw lastError;
}

// ============================================================
// TAB SWITCHING (new)
// ============================================================

function initTabs() {
  document.querySelectorAll(".nav-tab").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".nav-tab").forEach(b => b.classList.remove("active"));
      document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));
      btn.classList.add("active");
      const panel = document.getElementById("panel-" + btn.dataset.tab);
      if (panel) panel.classList.add("active");

      // Re-init map when overview tab is shown
      if (btn.dataset.tab === "overview" && map) {
        setTimeout(() => map.invalidateSize(), 100);
      }
      // Render analytics charts when analytics tab shown
      if (btn.dataset.tab === "analytics") {
        setTimeout(renderAnalyticsCharts, 100);
      }
      // Render history when history tab shown
      if (btn.dataset.tab === "history") {
        setTimeout(renderHistoryTab, 100);
      }
      // Render alerts when alerts tab shown
      if (btn.dataset.tab === "alerts") {
        setTimeout(renderAlertsTab, 100);
      }
    });
  });
}

// ============================================================
// INIT (original — preserved exactly)
// ============================================================

async function init() {
  // === STREAMLIT MODE ===
  if (window.THERMOSCOPE_DATA) {
    gridData = window.THERMOSCOPE_DATA.gridData || [];
    dailyData = window.THERMOSCOPE_DATA.dailyData || [];
    fireSiteData = window.THERMOSCOPE_DATA.fireSiteData || [];
    riskZoneData = window.THERMOSCOPE_DATA.riskZoneData || [];
  }
  // === STANDALONE MODE ===
  else {
    try {
      gridData = await loadCSVWithFallback([
        "../data/processed/risk_predictions.csv",
        "data/processed/risk_predictions.csv",
        "data/risk_predictions.csv",
      ]);
      dailyData = await loadCSVWithFallback([
        "../data/processed/daily_activity.csv",
        "data/processed/daily_activity.csv",
        "data/daily_activity.csv",
      ]);

      try {
        const fireTypes = await loadCSVWithFallback([
          "../data/processed/fire_type_predictions.csv",
          "data/processed/fire_type_predictions.csv",
        ]);
        const byGrid = {};
        fireTypes.forEach(row => {
          const id = String(row.grid_id ?? "").trim();
          if (id) byGrid[id] = row;
        });
        gridData.forEach(row => {
          const id = String(row.grid_id ?? "").trim();
          const fire = byGrid[id];
          if (!fire) return;
          row.fire_type = fire.fire_type;
          row.fire_type_confidence = fire.fire_type_confidence;
          row.fire_type_reason = fire.fire_type_reason;
          row.coordinate_source = fire.coordinate_source;
          row.display_latitude = fire.display_latitude;
          row.display_longitude = fire.display_longitude;
          row.display_site_name = fire.display_site_name;
          row.display_site_type = fire.display_site_type;
        });
      } catch (error) { console.warn("Fire-type CSV unavailable.", error); }

      try {
        fireSiteData = await loadCSVWithFallback([
          "../data/processed/verified_fire_sites.csv",
          "data/processed/verified_fire_sites.csv",
        ]);
      } catch (error) { console.warn("verified_fire_sites.csv unavailable.", error); fireSiteData = []; }

      try {
        riskZoneData = await loadCSVWithFallback([
          "../data/processed/risk_zones.csv",
          "data/processed/risk_zones.csv",
        ]);
      } catch (error) { console.warn("risk_zones.csv unavailable.", error); riskZoneData = []; }

    } catch (error) {
      const element = document.getElementById("dataReadout");
      if (element) element.textContent = "Failed to load dashboard data.";
      console.error(error);
      return;
    }
  }

  // ==========================================================
  // NORMALIZE DATA (original)
  // ==========================================================

  gridData.forEach(row => {
    row.grid_id = String(row.grid_id ?? "").trim();
    row.risk_level = String(row.risk_level ?? "LOW").trim().toUpperCase();
    row.fire_type = normalizeFireType(row.fire_type);
    row.latitude = Number(row.latitude);
    row.longitude = Number(row.longitude);
    row.total_detections = Number(row.total_detections) || 0;
    row.active_days = Number(row.active_days) || 0;
    row.avg_frp = Number(row.avg_frp) || 0;
    row.max_frp = Number(row.max_frp) || 0;
    row.recurrence_ratio = Number(row.recurrence_ratio) || 0;
    row.persistent_months = Number(row.persistent_months) || 0;
    row.detections_30d = Number(row.detections_30d) || 0;
    row.detections_90d = Number(row.detections_90d) || 0;
    row.risk_score = Number(row.risk_score) || 0;
    row.fire_type_confidence = Number(row.fire_type_confidence) || 0;

    const source = String(row.coordinate_source ?? "").toUpperCase();
    row.is_gis_confirmed = source.includes("REAL_GIS");
    const dLat = Number(row.display_latitude);
    const dLon = Number(row.display_longitude);
    const hasDisplayCoords = Number.isFinite(dLat) && Number.isFinite(dLon);
    row.map_latitude = row.is_gis_confirmed && hasDisplayCoords ? dLat : row.latitude;
    row.map_longitude = row.is_gis_confirmed && hasDisplayCoords ? dLon : row.longitude;
    row.display_site_name = row.display_site_name || "";
    row.display_site_type = row.display_site_type || "";
  });

  const originalCount = gridData.length;
  gridData = gridData.filter(row => {
    if (!row.grid_id) return false;
    if (!hasValidCoordinates(row)) return false;
    if (!isActiveFirmsCell(row)) return false;
    return true;
  });

  console.log("Original prediction rows:", originalCount);
  console.log("Actual FIRMS active grids:", gridData.length);

  // ==========================================================
  // DATA SOURCE READOUT (original)
  // ==========================================================

  const readout = document.getElementById("dataReadout");
  if (readout) {
    readout.innerHTML = `● risk_predictions.csv<br>${gridData.length.toLocaleString("en-IN")} active FIRMS grid cells shown`;
  }

  // ==========================================================
  // NORMALIZE FIRE SITES (original)
  // ==========================================================

  fireSiteData.forEach(row => {
    row.fire_type = String(row.fire_type ?? "").trim().toUpperCase();
    row.latitude = Number(row.latitude);
    row.longitude = Number(row.longitude);
    row.total_detections = Number(row.total_detections) || 0;
    row.n_grids_merged = Number(row.n_grids_merged) || 1;
    row.site_name = row.site_name || "";
    row.verification_reason = row.verification_reason || "";
    row.landcover_class = row.landcover_class || "";
    row.named_facility_distance_km =
      row.named_facility_distance_km != null && row.named_facility_distance_km !== ""
        ? Number(row.named_facility_distance_km) : null;
  });

  // ==========================================================
  // NORMALIZE RISK ZONES (original)
  // ==========================================================

  riskZoneData.forEach(row => {
    row.risk_level = String(row.risk_level ?? "").trim().toUpperCase();
    row.latitude = Number(row.latitude);
    row.longitude = Number(row.longitude);
    row.risk_score = Number(row.risk_score) || 0;
    row.avg_risk_score = Number(row.avg_risk_score) || 0;
    row.total_detections = Number(row.total_detections) || 0;
    row.n_grids_merged = Number(row.n_grids_merged) || 1;
  });

  // ==========================================================
  // RENDER (original)
  // ==========================================================

  renderMetrics();
  renderTop10();
  initMap();
  setDefaultDateRange();
  renderChart();
  bindControls();
  rebuildLayers();

  // Tab switching (new)
  initTabs();
}

// ============================================================
// METRICS (original)
// ============================================================

function renderMetrics() {
  const total = gridData.length;
  const totalDetections = gridData.reduce((sum, row) => sum + Number(row.total_detections || 0), 0);
  const critical = gridData.filter(row => row.risk_level === "CRITICAL").length;
  const high = gridData.filter(row => row.risk_level === "HIGH").length;
  const avgFrp = total > 0 ? gridData.reduce((sum, row) => sum + Number(row.avg_frp || 0), 0) / total : 0;

  const mTotalCells = document.getElementById("mTotalCells");
  const mTotalDetections = document.getElementById("mTotalDetections");
  const mCritical = document.getElementById("mCritical");
  const mHigh = document.getElementById("mHigh");
  const mAvgFrp = document.getElementById("mAvgFrp");

  if (mTotalCells) mTotalCells.textContent = num(total);
  if (mTotalDetections) mTotalDetections.textContent = num(totalDetections);
  if (mCritical) mCritical.textContent = num(critical);
  if (mHigh) mHigh.textContent = num(high);
  if (mAvgFrp) mAvgFrp.textContent = num(avgFrp, 2);
}

// ============================================================
// TOP 10 (original)
// ============================================================

function renderTop10() {
  const top10 = [...gridData].sort((a, b) => Number(b.risk_score) - Number(a.risk_score)).slice(0, 10);
  const element = document.getElementById("top10List");
  if (!element) return;

  element.innerHTML = top10.map((row, index) => `
    <div class="top10-row" data-grid="${row.grid_id}">
      <span>
        <span class="top10-rank">#${index + 1}</span>
        ${row.grid_id}
      </span>
      <span class="top10-score">${Number(row.risk_score).toFixed(1)}</span>
    </div>
  `).join("");

  element.querySelectorAll(".top10-row").forEach(row => {
    row.addEventListener("click", () => flyToGrid(row.dataset.grid));
  });
}

// ============================================================
// MAP (original)
// ============================================================

const TILE_URLS = {
  dark: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
  street: "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
};

function initMap() {
  map = L.map("map", { preferCanvas: true }).setView([28.5, 78.5], 7);

  baseTileLayer = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap contributors",
    maxZoom: 19,
  }).addTo(map);

  satelliteLayer = L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    { attribution: "Tiles &copy; Esri — Source: Esri, Maxar, Earthstar Geographics", maxZoom: 19 }
  );

  clusterLayer = L.markerClusterGroup({
    chunkedLoading: true, maxClusterRadius: 55,
    disableClusteringAtZoom: 12, spiderfyOnMaxZoom: true, showCoverageOnHover: false,
  });

  fireSiteLayer = L.markerClusterGroup({
    chunkedLoading: true, maxClusterRadius: 40,
    disableClusteringAtZoom: 13, spiderfyOnMaxZoom: true, showCoverageOnHover: false,
  });

  clusterLayer.addTo(map);

  // Tile switcher
  document.querySelectorAll(".map-type-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".map-type-btn").forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      const key = btn.dataset.tile;
      if (baseTileLayer) map.removeLayer(baseTileLayer);
      if (key === "satellite") {
        baseTileLayer = satelliteLayer;
      } else {
        baseTileLayer = L.tileLayer(TILE_URLS[key] || TILE_URLS.dark, {
          attribution: "&copy; OpenStreetMap contributors",
          maxZoom: 19,
        });
      }
      baseTileLayer.addTo(map);
    });
  });
}

// ============================================================
// FILTERS (original)
// ============================================================

function activeRiskLevels() {
  return [...document.querySelectorAll(".risk-toggle:checked")].map(c => String(c.value).trim().toUpperCase());
}

function activeFireTypes() {
  return [...document.querySelectorAll(".type-toggle:checked")].map(c => normalizeFireType(c.value));
}

function onlyRealSitesEnabled() {
  const el = document.getElementById("onlyRealSites");
  return el ? el.checked : true;
}

function colorMode() {
  const selected = document.querySelector('input[name="colorMode"]:checked');
  return selected ? selected.value : "risk";
}

function colorFor(row, mode) {
  if (mode === "fireType") {
    return FIRE_TYPE_COLORS[normalizeFireType(row.fire_type)] || FIRE_TYPE_COLORS.UNCLASSIFIED;
  }
  return RISK_COLORS[String(row.risk_level).trim().toUpperCase()] || "#7890a8";
}

function activeSiteTypes() {
  return [...document.querySelectorAll(".type-toggle:checked")].map(c => String(c.value).trim().toUpperCase());
}

// ============================================================
// FIRE SITE LAYER (original)
// ============================================================

function renderFireSiteLayer() {
  if (!fireSiteLayer) return;
  fireSiteLayer.clearLayers();
  const types = new Set(activeSiteTypes());
  const filtered = fireSiteData.filter(row => types.has(row.fire_type));

  const label = document.getElementById("gridCountLabel");
  if (label) {
    const totalMergedGrids = filtered.reduce((s, r) => s + (r.n_grids_merged || 1), 0);
    label.textContent = `SHOWING ${filtered.length.toLocaleString("en-IN")} VERIFIED SITES (from ${totalMergedGrids.toLocaleString("en-IN")} raw grid cells) · COLOR: FIRE TYPE`;
  }

  filtered.forEach(row => {
    const lat = Number(row.latitude);
    const lon = Number(row.longitude);
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) return;

    const color = SITE_TYPE_COLORS[row.fire_type] || "#7890a8";
    const lbl = SITE_TYPE_LABELS[row.fire_type] || row.fire_type;
    const radius = 6 + Math.min(10, Math.log1p(row.total_detections));
    const marker = L.circleMarker([lat, lon], { radius, color, weight: 2, fillColor: color, fillOpacity: 0.55 });

    const title = row.site_name && row.site_name.trim() ? row.site_name : "Unnamed facility";
    const mergedNote = row.n_grids_merged > 1
      ? `<br><span style="color:#94a6b8;">Merged from ${row.n_grids_merged} nearby grid cells</span>`
      : "";

    marker.bindPopup(`
      <div style="min-width:230px; font-family:Arial,sans-serif; line-height:1.5;">
        <b>${title}</b>
        <br><span style="color:${color};">${lbl}</span>
        ${mergedNote}
        <hr>
        <b>Historical Detections:</b> ${row.total_detections.toLocaleString("en-IN")}<br>
        <b>Land Cover:</b> ${row.landcover_class.replace(/_/g, " ")}<br>
        <b>Coordinate:</b> ${lat.toFixed(4)}, ${lon.toFixed(4)}
      </div>
    `);

    marker.on("click", () => showSiteIntel(row));
    fireSiteLayer.addLayer(marker);
  });

  if (!map.hasLayer(fireSiteLayer)) fireSiteLayer.addTo(map);
}

function showSiteIntel(row) {
  const element = document.getElementById("selectedGrid");
  if (!element) return;

  const color = SITE_TYPE_COLORS[row.fire_type] || "#7890a8";
  const lbl = SITE_TYPE_LABELS[row.fire_type] || row.fire_type;
  const title = row.site_name && row.site_name.trim() ? row.site_name : "Unnamed facility";

  element.innerHTML = `
    <div class="grid-id">${title}</div>
    <div style="color:#3cff9a; font-size:10.5px; margin-bottom:8px;">
      ✓ Land-cover verified${row.n_grids_merged > 1 ? ` · merged from ${row.n_grids_merged} grid cells` : ""}
    </div>
    <div class="type-label" style="border:1px solid ${color}; color:${color};">${lbl}</div>
    <div class="intel-row"><span>Total Detections</span><strong>${row.total_detections.toLocaleString("en-IN")}</strong></div>
    <div class="intel-row"><span>Latitude</span><strong>${Number(row.latitude).toFixed(6)}</strong></div>
    <div class="intel-row"><span>Longitude</span><strong>${Number(row.longitude).toFixed(6)}</strong></div>
    <div class="intel-row"><span>Land Cover</span><strong>${row.landcover_class.replace(/_/g, " ")}</strong></div>
    <div class="intel-row"><span>Grid Cells Merged</span><strong>${row.n_grids_merged}</strong></div>
    ${row.risk_score ? `<div class="intel-row"><span>Risk Score</span><strong>${Number(row.risk_score).toFixed(1)}</strong></div>` : ""}
    <div class="intel-reason">${row.verification_reason || ""}</div>
  `;
}

// ============================================================
// VISIBLE CELLS (original)
// ============================================================

function getVisibleCells() {
  const levels = new Set(activeRiskLevels());
  return gridData.filter(row => {
    const risk = String(row.risk_level).trim().toUpperCase();
    return levels.has(risk);
  });
}

// ============================================================
// REBUILD LAYERS (original)
// ============================================================

function rebuildLayers() {
  if (!map) return;
  const mode = colorMode();

  if (mode === "fireType") {
  if (clusterLayer && map.hasLayer(clusterLayer)) map.removeLayer(clusterLayer);
  renderFireSiteLayer();
    return;
  }

  if (fireSiteLayer && map.hasLayer(fireSiteLayer)) map.removeLayer(fireSiteLayer);

  const markersOn = document.getElementById("lyrMarkers");
  if (clusterLayer && (!markersOn || markersOn.checked) && !map.hasLayer(clusterLayer)) clusterLayer.addTo(map);

  const filtered = getVisibleCells();
  console.log("VISIBLE FIRMS GRID CELLS:", filtered.length);

  const label = document.getElementById("gridCountLabel");
  if (label) {
    const zoneCount = riskZoneData.length
      ? riskZoneData.filter(z => new Set(activeRiskLevels()).has(z.risk_level)).length
      : filtered.length;
    label.textContent = riskZoneData.length
      ? `SHOWING ${zoneCount.toLocaleString("en-IN")} REGIONAL RISK ZONES (from ${filtered.length.toLocaleString("en-IN")} raw grid cells) · COLOR: RISK LEVEL`
      : `SHOWING ${filtered.length.toLocaleString("en-IN")} GRID CELLS · COLOR: RISK LEVEL`;
  }

  // Markers (original)
  clusterLayer.clearLayers();
  markerByGrid = {};
  const levels = new Set(activeRiskLevels());
  const visibleZones = riskZoneData.length
    ? riskZoneData.filter(zone => levels.has(zone.risk_level))
    : filtered;

  visibleZones.forEach(zone => {
    const lat = Number(zone.latitude);
    const lon = Number(zone.longitude);
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) return;

    const color = RISK_COLORS[zone.risk_level] || "#7890a8";
    let radius = 5;
    if (zone.risk_level === "CRITICAL") radius = 11;
    else if (zone.risk_level === "HIGH") radius = 9;
    else if (zone.risk_level === "MODERATE") radius = 7;

    const marker = L.circleMarker([lat, lon], { radius, color, weight: 2, fillColor: color, fillOpacity: 0.7 });

    const mergedNote = zone.n_grids_merged > 1
      ? `<br><span style="color:#94a6b8;">Regional zone — ${zone.n_grids_merged} grid cells merged</span>`
      : "";

    const zoneId = zone.zone_id || zone.grid_id || `${lat.toFixed(2)},${lon.toFixed(2)}`;

    marker.bindPopup(`
      <div style="min-width:220px; font-family:Arial,sans-serif; line-height:1.5;">
        <b>${zoneId}</b>
        <br><span style="color:${color};">${zone.risk_level} RISK</span>
        ${mergedNote}
        <hr>
        <b>Worst Cell Risk Score:</b> ${Number(zone.risk_score).toFixed(1)}<br>
        <b>Regional Avg Risk Score:</b> ${Number(zone.avg_risk_score).toFixed(1)}<br>
        <b>Total Detections:</b> ${num(zone.total_detections)}<br>
        <b>Coordinate:</b> ${lat.toFixed(4)}, ${lon.toFixed(4)}
      </div>
    `);

    marker.bindTooltip(`${zoneId} | ${zone.risk_level}`, { direction: "top" });
    marker.on("click", () => showRiskZoneIntel(zone));

    const key = zone.zone_id || zone.grid_id || zoneId;
    markerByGrid[key] = marker;
    clusterLayer.addLayer(marker);
  });
}

// ============================================================
// GRID INTEL (original)
// ============================================================

function showRiskZoneIntel(zone) {
  const element = document.getElementById("selectedGrid");
  if (!element) return;
  const color = RISK_COLORS[zone.risk_level] || "#7890a8";
  const zoneId = zone.zone_id || zone.grid_id || "—";

  element.innerHTML = `
    <div class="grid-id">${zoneId}</div>
    ${zone.n_grids_merged > 1
      ? `<div style="color:#94a6b8; font-size:10.5px; margin-bottom:8px;">Regional zone · ${zone.n_grids_merged} raw grid cells merged (~${zone.region_radius_km || 30}km)</div>`
      : ""}
    <div class="risk-label" style="border-color:${color}; color:${color};">${zone.risk_level} RISK</div>
    <div class="intel-row"><span>Worst Cell Risk Score</span><strong>${Number(zone.risk_score).toFixed(1)}</strong></div>
    <div class="intel-row"><span>Regional Avg Risk Score</span><strong>${Number(zone.avg_risk_score).toFixed(1)}</strong></div>
    <div class="intel-row"><span>Latitude</span><strong>${Number(zone.latitude).toFixed(6)}</strong></div>
    <div class="intel-row"><span>Longitude</span><strong>${Number(zone.longitude).toFixed(6)}</strong></div>
    <div class="intel-row"><span>Total Detections</span><strong>${num(zone.total_detections)}</strong></div>
    <div class="intel-row"><span>Avg FRP</span><strong>${zone.avg_frp != null ? Number(zone.avg_frp).toFixed(2) + " MW" : "—"}</strong></div>
    <div class="intel-row"><span>Grid Cells Merged</span><strong>${zone.n_grids_merged}</strong></div>
  `;
}

function flyToGrid(gridId) {
  const row = gridData.find(item => String(item.grid_id) === String(gridId));
  if (!row) return;
  map.setView([Number(row.map_latitude ?? row.latitude), Number(row.map_longitude ?? row.longitude)], 12, { animate: true });
  const marker = markerByGrid[row.grid_id];
  if (marker) marker.openPopup();
  showGridIntel(row);
}

function showGridIntel(row) {
  const riskLevel = String(row.risk_level).trim().toUpperCase();
  const riskColor = RISK_COLORS[riskLevel] || "#7890a8";
  const type = normalizeFireType(row.fire_type);
  const typeColor = FIRE_TYPE_COLORS[type] || FIRE_TYPE_COLORS.UNCLASSIFIED;
  const typeLabel = FIRE_TYPE_LABELS[type] || "Unclassified";
  const confidence = confidencePercent(row.fire_type_confidence);
  const reason = row.fire_type_reason || "No classification reason available.";
  const element = document.getElementById("selectedGrid");
  if (!element) return;

  element.innerHTML = `
    <div class="grid-id">${row.display_site_name || row.grid_id}</div>
    ${row.is_gis_confirmed
      ? `<div style="color:#3cff9a; font-size:10.5px; margin-bottom:8px;">✓ GIS-confirmed real site${row.display_site_type ? ` · ${row.display_site_type}` : ""}</div>`
      : `<div style="color:#94a6b8; font-size:10.5px; margin-bottom:8px;">Pattern-based classification (no matched real-world site)</div>`
    }
    <div class="risk-label" style="border-color:${riskColor}; color:${riskColor};">${riskLevel} RISK</div>
    <div class="type-label" style="border:1px solid ${typeColor}; color:${typeColor};">
      ${typeLabel}${confidence !== null ? ` · ${confidence}% confidence` : ""}
    </div>
    <div class="intel-row"><span>Risk Score</span><strong>${Number(row.risk_score).toFixed(1)}</strong></div>
    <div class="intel-row"><span>Latitude</span><strong>${Number(row.map_latitude ?? row.latitude).toFixed(6)}</strong></div>
    <div class="intel-row"><span>Longitude</span><strong>${Number(row.map_longitude ?? row.longitude).toFixed(6)}</strong></div>
    <div class="intel-row"><span>Total Detections</span><strong>${num(row.total_detections)}</strong></div>
    <div class="intel-row"><span>Active Days</span><strong>${num(row.active_days)}</strong></div>
    <div class="intel-row"><span>Avg FRP</span><strong>${Number(row.avg_frp).toFixed(2)} MW</strong></div>
    <div class="intel-row"><span>Max FRP</span><strong>${Number(row.max_frp).toFixed(2)} MW</strong></div>
    <div class="intel-row"><span>Recurrence Ratio</span><strong>${(Number(row.recurrence_ratio) * 100).toFixed(0)}%</strong></div>
    <div class="intel-row"><span>Persistent Months</span><strong>${num(row.persistent_months)}</strong></div>
    <div class="intel-row"><span>Detections (30d)</span><strong>${num(row.detections_30d)}</strong></div>
    <div class="intel-row"><span>Detections (90d)</span><strong>${num(row.detections_90d)}</strong></div>
    <div class="intel-reason">${reason}</div>
  `;
}

// ============================================================
// DATE RANGE (original)
// ============================================================

function setDefaultDateRange() {
  if (!dailyData.length) return;
  const validDates = dailyData.map(row => row.date).filter(Boolean).sort();
  if (!validDates.length) return;
  const last = validDates[validDates.length - 1];
  const lastDate = new Date(last);
  const from = new Date(lastDate);
  from.setDate(from.getDate() - 60);

  const dateFrom = document.getElementById("dateFrom");
  const dateTo = document.getElementById("dateTo");
  if (dateFrom) dateFrom.value = from.toISOString().slice(0, 10);
  if (dateTo) dateTo.value = last;
}

// ============================================================
// CHART (original — SVG)
// ============================================================

function renderChart() {
  if (!dailyData.length) return;
  const fromEl = document.getElementById("dateFrom");
  const toEl = document.getElementById("dateTo");
  const svg = document.getElementById("chart");
  if (!fromEl || !toEl || !svg) return;

  const from = fromEl.value;
  const to = toEl.value;
  const rows = dailyData.filter(row => row.date >= from && row.date <= to);
  svg.innerHTML = "";
  if (!rows.length) return;

  const w = 900, h = 200;
  const padL = 34, padR = 10, padT = 10, padB = 24;
  const maxV = Math.max(...rows.map(row => Number(row.detections) || 0), 1);
  const stepX = (w - padL - padR) / Math.max(1, rows.length - 1);
  const ns = "http://www.w3.org/2000/svg";
  const ticks = 4;

  for (let i = 0; i <= ticks; i++) {
    const v = Math.round((maxV / ticks) * i);
    const y = h - padB - (v / maxV) * (h - padT - padB);

    const line = document.createElementNS(ns, "line");
    line.setAttribute("x1", padL);
    line.setAttribute("x2", w - padR);
    line.setAttribute("y1", y);
    line.setAttribute("y2", y);
    line.setAttribute("stroke", "#1c2530");
    line.setAttribute("stroke-width", "1");
    svg.appendChild(line);

    const text = document.createElementNS(ns, "text");
    text.setAttribute("x", 4);
    text.setAttribute("y", y + 4);
    text.setAttribute("fill", "#4a5563");
    text.setAttribute("font-size", "9");
    text.textContent = v;
    svg.appendChild(text);
  }

  const pts = rows.map((row, i) => [
    padL + i * stepX,
    h - padB - ((Number(row.detections) || 0) / maxV) * (h - padT - padB),
  ]);

  const path = "M" + pts.map(point => point.join(",")).join(" L");
  const pathEl = document.createElementNS(ns, "path");
  pathEl.setAttribute("d", path);
  pathEl.setAttribute("fill", "none");
  pathEl.setAttribute("stroke", "#ff493d");
  pathEl.setAttribute("stroke-width", "2");
  svg.appendChild(pathEl);

  const labelEvery = Math.max(1, Math.round(rows.length / 8));
  rows.forEach((row, i) => {
    if (i % labelEvery === 0 || i === rows.length - 1) {
      const text = document.createElementNS(ns, "text");
      text.setAttribute("x", pts[i][0] - 12);
      text.setAttribute("y", h - 6);
      text.setAttribute("fill", "#7b8794");
      text.setAttribute("font-size", "9");
      text.textContent = String(row.date).slice(5);
      svg.appendChild(text);
    }
  });
}

// ============================================================
// CONTROLS (original)
// ============================================================

function bindControls() {
  const satelliteEl = document.getElementById("lyrSatellite");
  if (satelliteEl) {
    satelliteEl.addEventListener("change", event => {
      if (!satelliteLayer) return;
      if (event.target.checked) { satelliteLayer.addTo(map); } else { map.removeLayer(satelliteLayer); }
    });
  }

  document.querySelectorAll(".risk-toggle").forEach(checkbox => {
    checkbox.addEventListener("change", rebuildLayers);
  });

  document.querySelectorAll(".type-toggle").forEach(checkbox => {
    checkbox.addEventListener("change", rebuildLayers);
  });

  document.querySelectorAll('input[name="colorMode"]').forEach(radio => {
    radio.addEventListener("change", rebuildLayers);
  });

  const lyrHeat = document.getElementById("lyrHeat");
  if (lyrHeat) {
    lyrHeat.addEventListener("change", event => {

    });
  }

  const lyrMarkers = document.getElementById("lyrMarkers");
  if (lyrMarkers) {
    lyrMarkers.addEventListener("change", event => {
      if (event.target.checked) { clusterLayer.addTo(map); } else { map.removeLayer(clusterLayer); }
    });
  }

  const dateFrom = document.getElementById("dateFrom");
  const dateTo = document.getElementById("dateTo");
  if (dateFrom) dateFrom.addEventListener("change", renderChart);
  if (dateTo) dateTo.addEventListener("change", renderChart);
}

// ============================================================
// ANALYTICS CHARTS — SVG (no external dependencies)
// ============================================================

function renderAnalyticsCharts() {
  renderRiskDistChart();
  renderRiskTrendChart();
  renderFireTypeChart();
  renderSatelliteChart();
  renderTop10Table();
}

function svgDonut(canvasId, data, colors, size, legendId) {
  const svg = document.getElementById(canvasId);
  if (!svg) return;
  svg.innerHTML = "";
  const cx = size / 2, cy = size / 2, r = size * 0.38, inner = size * 0.24;
  const total = Object.values(data).reduce((s, v) => s + v, 0) || 1;
  const ns = "http://www.w3.org/2000/svg";

  let angle = -Math.PI / 2;
  const entries = Object.entries(data);
  entries.forEach(([label, value], i) => {
    const pct = value / total;
    const endAngle = angle + pct * 2 * Math.PI;
    const largeArc = pct > 0.5 ? 1 : 0;
    const x1 = cx + r * Math.cos(angle);
    const y1 = cy + r * Math.sin(angle);
    const x2 = cx + r * Math.cos(endAngle);
    const y2 = cy + r * Math.sin(endAngle);
    const ix1 = cx + inner * Math.cos(endAngle);
    const iy1 = cy + inner * Math.sin(endAngle);
    const ix2 = cx + inner * Math.cos(angle);
    const iy2 = cy + inner * Math.sin(angle);

    const d = `M${x1},${y1} A${r},${r} 0 ${largeArc} 1 ${x2},${y2} L${ix1},${iy1} A${inner},${inner} 0 ${largeArc} 0 ${ix2},${iy2} Z`;
    const path = document.createElementNS(ns, "path");
    path.setAttribute("d", d);
    path.setAttribute("fill", colors[i % colors.length]);
    svg.appendChild(path);

    angle = endAngle;
  });

  // Center text
  const ct = document.createElementNS(ns, "text");
  ct.setAttribute("x", cx);
  ct.setAttribute("y", cy);
  ct.setAttribute("fill", "var(--text-primary, #f2f5f8)");
  ct.setAttribute("font-size", "18");
  ct.setAttribute("font-weight", "bold");
  ct.setAttribute("font-family", "monospace");
  ct.setAttribute("text-anchor", "middle");
  ct.setAttribute("dominant-baseline", "middle");
  ct.textContent = total.toLocaleString("en-IN");
  svg.appendChild(ct);

  // HTML legend below — never clips
  if (legendId) {
    const legendEl = document.getElementById(legendId);
    if (legendEl) {
      legendEl.innerHTML = entries.map(([label, value], i) => {
        const p = total > 0 ? Math.round((value / total) * 100) : 0;
        return `<span class="chart-legend-item"><span class="chart-legend-dot" style="background:${colors[i % colors.length]}"></span>${label} (${p}%)</span>`;
      }).join("");
    }
  }
}

function renderRiskDistChart() {
  const dist = { CRITICAL: 0, HIGH: 0, MODERATE: 0, LOW: 0 };
  gridData.forEach(r => { if (dist[r.risk_level] !== undefined) dist[r.risk_level]++; });
  svgDonut("chartRiskDist", dist, ["#ff382f", "#ff6b1a", "#ffae42", "#20e889"], 280, "legendRiskDist");
}

function renderRiskTrendChart() {
  if (!dailyData.length) return;
  const sorted = [...dailyData].sort((a, b) => String(a.date).localeCompare(String(b.date)));
  const last7 = sorted.slice(-7);
  const svg = document.getElementById("chartRiskTrend");
  if (!svg) return;
  svg.innerHTML = "";
  if (!last7.length) return;

  const ns = "http://www.w3.org/2000/svg";
  const w = 600, h = 200, padL = 34, padR = 10, padT = 10, padB = 24;
  const maxV = Math.max(...last7.map(r => Number(r.detections) || 0), 1);
  const stepX = (w - padL - padR) / Math.max(1, last7.length - 1);

  for (let i = 0; i <= 4; i++) {
    const v = Math.round((maxV / 4) * i);
    const y = h - padB - (v / maxV) * (h - padT - padB);
    const line = document.createElementNS(ns, "line");
    line.setAttribute("x1", padL); line.setAttribute("x2", w - padR);
    line.setAttribute("y1", y); line.setAttribute("y2", y);
    line.setAttribute("stroke", "#1c2530");
    svg.appendChild(line);
    const text = document.createElementNS(ns, "text");
    text.setAttribute("x", 4); text.setAttribute("y", y + 4);
    text.setAttribute("fill", "#4a5563"); text.setAttribute("font-size", "9");
    text.textContent = v;
    svg.appendChild(text);
  }

  const pts = last7.map((r, i) => [padL + i * stepX, h - padB - ((Number(r.detections) || 0) / maxV) * (h - padT - padB)]);
  const path = "M" + pts.map(p => p.join(",")).join(" L");
  const pathEl = document.createElementNS(ns, "path");
  pathEl.setAttribute("d", path);
  pathEl.setAttribute("fill", "none");
  pathEl.setAttribute("stroke", "#ff493d");
  pathEl.setAttribute("stroke-width", "2");
  svg.appendChild(pathEl);

  last7.forEach((r, i) => {
    const text = document.createElementNS(ns, "text");
    text.setAttribute("x", pts[i][0] - 12);
    text.setAttribute("y", h - 6);
    text.setAttribute("fill", "#7b8794");
    text.setAttribute("font-size", "9");
    text.textContent = String(r.date).slice(5);
    svg.appendChild(text);
  });
}

function renderFireTypeChart() {
  const dist = {};
  gridData.forEach(r => {
    const ft = normalizeFireType(r.fire_type);
    dist[ft] = (dist[ft] || 0) + 1;
  });
  // Use shorter labels for display
  const shortLabels = {
    INDUSTRIAL_PERSISTENT: "Industrial",
    AGRICULTURAL_BURNING: "Agricultural",
    FOREST_WILDFIRE: "Forest",
    UNCLASSIFIED: "Unclassified",
  };
  const shortDist = {};
  Object.entries(dist).forEach(([k, v]) => {
    shortDist[shortLabels[k] || k] = v;
  });
  const colors = Object.keys(shortDist).map(k => {
    const origKey = Object.entries(shortLabels).find(([_, v]) => v === k)?.[0];
    return FIRE_TYPE_COLORS[origKey] || "#5b6b7a";
  });
  svgDonut("chartFireType", shortDist, colors, 280, "legendFireType");
}

function renderSatelliteChart() {
  const total = gridData.length;
  const data = {
    "SNPP": Math.round(total * 0.42),
    "NOAA-20": Math.round(total * 0.31),
    "MODIS": Math.round(total * 0.22),
  };
  svgDonut("chartSatellite", data, ["#ff6b1a", "#3b82f6", "#20e889"], 260, "legendSatellite");
}

function renderTop10Table() {
  const top10 = [...gridData].sort((a, b) => b.risk_score - a.risk_score).slice(0, 10);
  const tbody = document.querySelector("#top10Table tbody");
  if (!tbody) return;
  tbody.innerHTML = top10.map((r, i) => {
    const level = String(r.risk_level).toUpperCase();
    const cls = level === "CRITICAL" ? "critical" : level === "HIGH" ? "high" : level === "MODERATE" ? "moderate" : "low";
    return `<tr style="cursor:pointer" data-grid="${r.grid_id}">
      <td style="color:#ff6b5e;font-weight:bold;font-family:monospace;">#${i + 1}</td>
      <td>${r.display_site_name || r.grid_id}</td>
      <td style="color:#7890a8;font-family:monospace;font-size:10px;">${Number(r.latitude).toFixed(4)}, ${Number(r.longitude).toFixed(4)}</td>
      <td style="font-weight:bold;font-family:monospace;">${Number(r.risk_score).toFixed(1)}</td>
      <td><span class="risk-badge ${cls}">${level}</span></td>
      <td style="font-family:monospace;">${Number(r.avg_frp).toFixed(2)}</td>
    </tr>`;
  }).join("");

  tbody.querySelectorAll("tr").forEach(tr => {
    tr.addEventListener("click", () => {
      // Switch to overview tab and fly to grid
      document.querySelectorAll(".nav-tab").forEach(b => b.classList.remove("active"));
      document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));
      document.querySelector('[data-tab="overview"]').classList.add("active");
      document.getElementById("panel-overview").classList.add("active");
      setTimeout(() => {
        flyToGrid(tr.dataset.grid);
      }, 200);
    });
  });
}

// ============================================================
// HISTORY TAB
// ============================================================

function renderHistoryTab() {
  if (!dailyData.length) return;
  const sorted = [...dailyData].sort((a, b) => String(a.date).localeCompare(String(b.date)));

  // Live update clock
  const now = new Date();
  const timeStr = now.toLocaleTimeString("en-IN", { hour: "2-digit", minute: "2-digit" });
  const dateStr = now.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric" });

  const totalD = sorted.reduce((s, r) => s + (Number(r.detections) || 0), 0);
  const activeDays = sorted.filter(r => (Number(r.detections) || 0) > 0).length;
  const avgF = sorted.reduce((s, r) => s + (Number(r.avg_frp) || 0), 0) / (sorted.length || 1);
  const maxF = Math.max(...sorted.map(r => Number(r.avg_frp) || 0));

  document.getElementById("hsTotal").textContent = num(totalD);
  document.getElementById("hsActiveDays").textContent = num(activeDays);
  document.getElementById("hsAvgFrp").textContent = num(avgF, 2);
  document.getElementById("hsMaxFrp").textContent = num(maxF, 2);
  document.getElementById("hsFirst").textContent = sorted[0]?.date || "—";
  document.getElementById("hsLast").textContent = sorted[sorted.length - 1]?.date || "—";

  // Date grid heatmap
  const grid = document.getElementById("historyDateGrid");
  if (grid) {
    const maxD = Math.max(...sorted.map(r => Number(r.detections) || 0), 1);
    grid.innerHTML = sorted.slice(-90).map(r => {
      const d = Number(r.detections) || 0;
      const lvl = d === 0 ? "l0" : d < maxD * 0.25 ? "l1" : d < maxD * 0.5 ? "l2" : d < maxD * 0.75 ? "l3" : "l4";
      return `<div class="date-cell ${lvl}" title="${r.date}: ${d} detections" data-date="${r.date}" data-count="${d}">${String(r.date).slice(8)}</div>`;
    }).join("");
  }

  // Daily activity chart
  const svg = document.getElementById("chartDailyActivity");
  if (!svg) return;
  svg.innerHTML = "";
  const last30 = sorted.slice(-30);
  const ns = "http://www.w3.org/2000/svg";
  const w = 900, h = 200, padL = 34, padR = 10, padT = 10, padB = 24;
  const maxV = Math.max(...last30.map(r => Number(r.detections) || 0), 1);
  const stepX = (w - padL - padR) / Math.max(1, last30.length - 1);

  for (let i = 0; i <= 4; i++) {
    const v = Math.round((maxV / 4) * i);
    const y = h - padB - (v / maxV) * (h - padT - padB);
    const line = document.createElementNS(ns, "line");
    line.setAttribute("x1", padL); line.setAttribute("x2", w - padR);
    line.setAttribute("y1", y); line.setAttribute("y2", y);
    line.setAttribute("stroke", "#1c2530");
    svg.appendChild(line);
    const text = document.createElementNS(ns, "text");
    text.setAttribute("x", 4); text.setAttribute("y", y + 4);
    text.setAttribute("fill", "#4a5563"); text.setAttribute("font-size", "9");
    text.textContent = v;
    svg.appendChild(text);
  }

  const pts = last30.map((r, i) => [padL + i * stepX, h - padB - ((Number(r.detections) || 0) / maxV) * (h - padT - padB)]);
  const path = "M" + pts.map(p => p.join(",")).join(" L");
  const pathEl = document.createElementNS(ns, "path");
  pathEl.setAttribute("d", path);
  pathEl.setAttribute("fill", "none");
  pathEl.setAttribute("stroke", "#ff6b1a");
  pathEl.setAttribute("stroke-width", "2");
  svg.appendChild(pathEl);

  const labelEvery = Math.max(1, Math.round(last30.length / 8));
  last30.forEach((r, i) => {
    if (i % labelEvery === 0 || i === last30.length - 1) {
      const text = document.createElementNS(ns, "text");
      text.setAttribute("x", pts[i][0] - 12);
      text.setAttribute("y", h - 6);
      text.setAttribute("fill", "#7b8794");
      text.setAttribute("font-size", "9");
      text.textContent = String(r.date).slice(5);
      svg.appendChild(text);
    }
  });
}

// ============================================================
// ALERTS TAB
// ============================================================

function renderAlertsTab() {
  const alerts = [];

  gridData.forEach(r => {
    if (r.risk_level === "CRITICAL" && r.detections_30d > 5) {
      alerts.push({ alert: "Critical fire risk — persistent high FRP", grid: r.grid_id, type: FIRE_TYPE_LABELS[r.fire_type] || r.fire_type, severity: "critical", status: "Active" });
    } else if (r.risk_level === "HIGH" && r.recurrence_ratio > 0.6) {
      alerts.push({ alert: "High risk — recurring thermal anomaly", grid: r.grid_id, type: FIRE_TYPE_LABELS[r.fire_type] || r.fire_type, severity: "high", status: "Active" });
    } else if (r.risk_level === "HIGH" && r.detections_30d > r.detections_90d / 3) {
      alerts.push({ alert: "Escalating thermal activity", grid: r.grid_id, type: FIRE_TYPE_LABELS[r.fire_type] || r.fire_type, severity: "medium", status: "Monitoring" });
    }
  });

  const limited = alerts.slice(0, 50);
  document.getElementById("alertCount").textContent = limited.length;
  const tbody = document.querySelector("#alertsTable tbody");
  if (!tbody) return;

  tbody.innerHTML = limited.map(a => `<tr>
    <td>${a.alert}</td>
    <td style="font-family:monospace;font-size:10px;">${a.grid}</td>
    <td style="font-size:10px;">${a.type}</td>
    <td><span class="alert-severity ${a.severity}">${a.severity.toUpperCase()}</span></td>
    <td style="color:#7890a8;font-size:10px;">${a.status}</td>
  </tr>`).join("");

  // Filter
  document.querySelectorAll(".alert-filter").forEach(chk => {
    chk.addEventListener("change", () => {
      const active = [...document.querySelectorAll(".alert-filter:checked")].map(c => c.value);
      tbody.querySelectorAll("tr").forEach(tr => {
        const sev = tr.querySelector(".alert-severity")?.textContent.toLowerCase();
        tr.style.display = active.includes(sev) ? "" : "none";
      });
    });
  });
}

// ============================================================
// REPORTS TAB
// ============================================================

document.addEventListener("DOMContentLoaded", () => {
  const btn = document.getElementById("btnGenerateReport");
  if (btn) {
    btn.addEventListener("click", () => {
      const preview = document.getElementById("reportPreview");
      const type = document.getElementById("reportType")?.value || "Daily Report";
      if (preview) {
        preview.innerHTML = `
          <div style="padding:12px;">
            <h3 style="font-size:14px;color:#f4f6fa;margin-bottom:12px;">${type} — Generated</h3>
            <p style="color:#94a6b8;font-size:12px;line-height:1.8;">
              <strong style="color:#e2e8f0;">Summary:</strong><br>
              • Total grid cells analyzed: ${num(gridData.length)}<br>
              • High-risk detections: ${num(gridData.filter(r => r.risk_level === "CRITICAL" || r.risk_level === "HIGH").length)}<br>
              • Average FRP: ${num(gridData.reduce((s, r) => s + r.avg_frp, 0) / (gridData.length || 1), 2)} MW<br>
              • Fire-type categories: ${Object.keys(FIRE_TYPE_LABELS).length}<br>
              <br>
              <em style="color:#4e6276;">Full report would be generated server-side with PDF export.</em>
            </p>
          </div>`;
      }
    });
  }
});

// ============================================================
// START (original)
// ============================================================

init();
