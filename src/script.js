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
  // Intro screen theme button (SVG icon)
  const introBtn = document.getElementById('introThemeToggle');
  if (introBtn) {
    introBtn.innerHTML = theme === 'dark'
      ? '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"/></svg>'
      : '<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="4.2"/><path d="M12 2.5v2.4M12 19.1v2.4M2.5 12h2.4M19.1 12h2.4M4.9 4.9l1.7 1.7M17.4 17.4l1.7 1.7M4.9 19.1l1.7-1.7M17.4 6.6l1.7-1.7"/></svg>';
  }
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
let nrtData = [];
let alertsData = [];
let map = null;
let clusterLayer = null;
let satelliteLayer = null;
let fireSiteLayer = null;
let nrtLayer = null;
let top10Layer = null;
let fireSiteData = [];
let riskZoneData = [];
let markerByGrid = {};
let nrtAutoRefreshTimer = null;
const NRT_AUTO_REFRESH_MS = 5 * 60 * 1000; // 5 minutes

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
      // Render forecast when forecast tab shown
      if (btn.dataset.tab === "forecast") {
        setTimeout(renderForecastTab, 100);
      }
    });
  });
}

// ============================================================
// INTRO / LANDING SCREEN (premium load page)
// ============================================================

function populateIntroMetrics() {
  const set = (id, val) => {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
  };

  const totalDetections = gridData.reduce((sum, row) => sum + (row.total_detections || 0), 0);
  const activeCells = gridData.length;
  const highCrit = gridData.filter(row => row.risk_level === "CRITICAL" || row.risk_level === "HIGH");
  const criticalCells = gridData.filter(row => row.risk_level === "CRITICAL").length;

  set("introMetric1", totalDetections.toLocaleString("en-IN"));
  set("introMetric2", activeCells.toLocaleString("en-IN"));
  set("introMetric3", highCrit.length.toLocaleString("en-IN"));
  set("introMetric4", criticalCells.toLocaleString("en-IN"));

  // Trend deltas — last 30 days vs previous 30 days, from real daily activity.
  // Negative = activity is falling (good for fire risk) → shown in green.
  const sorted = dailyData
    .map(r => ({ date: String(r.date || ""), detections: Number(r.detections) || 0, avgFrp: Number(r.avg_frp) || 0 }))
    .filter(r => r.date)
    .sort((a, b) => a.date.localeCompare(b.date));

  const trendPct = (pick) => {
    const n = sorted.length;
    if (n < 40) return null;
    let cur = 0, prev = 0;
    for (let i = n - 30; i < n; i++) cur += pick(sorted[i]);
    for (let i = n - 60; i < n - 30; i++) prev += pick(sorted[i]);
    if (!prev) return null;
    return Math.round(((cur - prev) / prev) * 100);
  };

  const detTrend = trendPct(r => r.detections);
  const frpTrend = trendPct(r => r.detections * r.avgFrp); // total fire intensity
  const nrtLive = nrtData.length;

  const fmtTrend = (el, val) => {
    if (!el) return;
    if (val === null) { el.textContent = "—"; el.className = "intro-metric-delta"; return; }
    el.textContent = (val >= 0 ? "+" : "−") + Math.abs(val) + "%";
    el.className = "intro-metric-delta " + (val >= 0 ? "up" : "down");
  };

  fmtTrend(document.getElementById("introMetric1Delta"), detTrend);
  const delta2 = document.getElementById("introMetric2Delta");
  if (delta2) {
    delta2.textContent = nrtLive ? nrtLive + " live now" : "—";
    delta2.className = "intro-metric-delta";
  }
  fmtTrend(document.getElementById("introMetric3Delta"), frpTrend);
}

const TRANSITION_DURATION_MS = 2400;
let introTransitionActive = false;

function resetTransitionSteps() {
  document.querySelectorAll("#transitionSteps .transition-step").forEach(s => {
    s.classList.remove("active", "done");
  });
}

function updateTransitionSteps(pct) {
  const steps = document.querySelectorAll("#transitionSteps .transition-step");
  const n = steps.length;
  steps.forEach((s, i) => {
    const activeStart = (i / n) * 100;
    const completeAt = ((i + 1) / n) * 100;
    s.classList.toggle("active", pct >= activeStart && pct < completeAt);
    s.classList.toggle("done", pct >= completeAt);
  });
}

function enterDashboard(tab) {
  if (introTransitionActive) return; // guard against double clicks
  introTransitionActive = true;

  if (!tab) tab = "overview";

  // 1. Hide the intro instantly — the opaque overlay covers everything
  const intro = document.getElementById("introScreen");
  if (intro) {
    intro.classList.add("hidden");
    intro.style.display = "none";
  }

  // 2. Show the overlay IMMEDIATELY (no fade-in) so the dashboard never
  //    flashes — it is fully opaque from the very first frame.
  const overlay = document.getElementById("transitionOverlay");
  const fill = document.getElementById("transitionBarFill");
  const pctEl = document.getElementById("transitionPct");
  if (!overlay || !fill) { introTransitionActive = false; return; }
  resetTransitionSteps();
  fill.style.width = "0%";
  if (pctEl) pctEl.textContent = "0%";
  overlay.classList.remove("done");
  overlay.style.display = "flex";
  overlay.classList.add("show");

  // 3. Switch to the target tab underneath (hidden behind the opaque
  //    overlay), so the dashboard is fully rendered by reveal time.
  const tabBtn = document.querySelector('.nav-tab[data-tab="' + tab + '"]');
  if (tabBtn) {
    tabBtn.click(); // reuses initTabs() logic (map resize, chart render, etc.)
  } else {
    document.querySelectorAll(".tab-panel").forEach(p => p.classList.remove("active"));
    const panel = document.getElementById("panel-" + tab);
    if (panel) panel.classList.add("active");
  }

  // 4. Animate the progress bar (ease-out) + live % counter + checklist
  const start = performance.now();
  function frame(now) {
    const t = Math.min(1, (now - start) / TRANSITION_DURATION_MS);
    const eased = 1 - Math.pow(1 - t, 3); // ease-out cubic
    const pct = Math.round(eased * 100);
    fill.style.width = pct + "%";
    if (pctEl) pctEl.textContent = pct + "%";
    updateTransitionSteps(pct);
    if (t < 1) {
      requestAnimationFrame(frame);
    } else {
      finishTransition(overlay);
    }
  }
  requestAnimationFrame(frame);
}

function finishTransition(overlay) {
  // Reveal: lift the active panel into place as the overlay fades out
  const active = document.querySelector(".tab-panel.active");
  if (active) {
    active.classList.remove("panel-enter");
    void active.offsetWidth; // restart the animation
    active.classList.add("panel-enter");
  }
  overlay.classList.add("done");
  setTimeout(() => {
    overlay.style.display = "none";
    introTransitionActive = false;
    window.scrollTo(0, 0);
  }, 500);
}

function scrollIntroTo(id) {
  const intro = document.getElementById("introScreen");
  const target = document.getElementById(id);
  if (!intro || !target) return;
  intro.scrollTo({ top: target.offsetTop - 12, behavior: "smooth" });
}

function initIntro() {
  const open = document.getElementById("introOpenDashboard");
  if (open) open.addEventListener("click", () => enterDashboard("overview"));
  const start = document.getElementById("introGetStarted");
  if (start) start.addEventListener("click", () => enterDashboard("overview"));
  const learn = document.getElementById("introLearnMore");
  if (learn) learn.addEventListener("click", () => scrollIntroTo("introFeatures"));
  document.querySelectorAll("[data-intro-link]").forEach(link => {
    link.addEventListener("click", (e) => {
      e.preventDefault();
      if (link.dataset.introLink === "overview") {
        scrollIntroTo("introFeatures");
      } else {
        enterDashboard(link.dataset.introLink);
      }
    });
  });
  const introTheme = document.getElementById("introThemeToggle");
  if (introTheme) introTheme.addEventListener("click", toggleTheme);
}

// ============================================================
// SATELLITE EVIDENCE VIEWER
// ============================================================

let satEvidenceMap = null;

function gibsEvidenceDate(offsetDays) {
  var d = new Date();
  d.setDate(d.getDate() - (offsetDays || 1));
  return d.getFullYear() + '-' + String(d.getMonth()+1).padStart(2,'0') + '-' + String(d.getDate()).padStart(2,'0');
}

function gibsWmsUrl(lat, lon, dateStr, span, w, h) {
  var minLon = lon - span, maxLon = lon + span;
  var minLat = lat - span, maxLat = lat + span;
  return 'https://gibs.earthdata.nasa.gov/wms/epsg4326/best/wms.cgi'
    + '?SERVICE=WMS&VERSION=1.1.1&REQUEST=GetMap'
    + '&LAYERS=MODIS_Terra_CorrectedReflectance_TrueColor'
    + '&TIME=' + dateStr
    + '&BBOX=' + minLon + ',' + minLat + ',' + maxLon + ',' + maxLat
    + '&SRS=EPSG:4326&WIDTH=' + w + '&HEIGHT=' + h + '&FORMAT=image/jpeg';
}

function showSatelliteEvidence(lat, lon, label) {
  var modal = document.getElementById('satEvidenceModal');
  var coordsEl = document.getElementById('satEvidenceCoords');
  var loadingEl = document.getElementById('satEvidenceLoading');
  var timestampEl = document.getElementById('satEvidenceTimestamp');
  var mapEl = document.getElementById('satEvidenceMap');
  if (!modal || !mapEl) return;

  if (coordsEl) coordsEl.textContent = lat.toFixed(5) + ', ' + lon.toFixed(5);
  if (loadingEl) loadingEl.style.display = 'flex';
  if (timestampEl) timestampEl.textContent = '';
  modal.style.display = 'flex';
  if (satEvidenceMap) { satEvidenceMap.remove(); satEvidenceMap = null; }

  // Dates to try: yesterday, 2d ago, 3d ago
  var dates = [
    { d: gibsEvidenceDate(1), lbl: 'Yesterday', hrs: 24 },
    { d: gibsEvidenceDate(2), lbl: '2 days ago', hrs: 48 },
    { d: gibsEvidenceDate(3), lbl: '3 days ago', hrs: 72 },
  ];
  var span = 0.25; // ~28km box

  function tryDate(idx) {
    if (idx >= dates.length) {
      // All GIBS failed — show Esri fallback via Leaflet
      if (loadingEl) loadingEl.style.display = 'none';
      if (timestampEl) timestampEl.textContent = '\u26a0\ufe0f GIBS unavailable \u00b7 Esri reference imagery (not real-time)';
      satEvidenceMap = L.map(mapEl, { center: [lat,lon], zoom: 13, zoomControl: true, attributionControl: true, dragging: true, scrollWheelZoom: true });
      L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', { attribution: 'Esri (fallback)', maxZoom: 19 }).addTo(satEvidenceMap);
      addEvidenceMarkers(lat, lon);
      return;
    }
    var url = gibsWmsUrl(lat, lon, dates[idx].d, span, 800, 800);
    var img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = function() {
      // GIBS returned a valid image — display it
      if (loadingEl) loadingEl.style.display = 'none';
      var dateText = '🛰️ NASA GIBS · Acquired: ' + dates[idx].d + ' (~' + dates[idx].hrs + 'h ago)';
      if (timestampEl) timestampEl.textContent = dateText;
      // Also update sidebar date info below the button
      var dateInfo = document.getElementById('satEvidenceDateInfo');
      if (dateInfo) dateInfo.textContent = '🛰️ Latest satellite: ' + dates[idx].d + ' (' + dates[idx].lbl + ')';
      mapEl.innerHTML = '';
      mapEl.style.background = '#0b1118';
      mapEl.style.display = 'flex';
      mapEl.style.alignItems = 'center';
      mapEl.style.justifyContent = 'center';
      img.style.width = '100%';
      img.style.height = '100%';
      img.style.objectFit = 'contain';
      img.alt = 'GIBS Satellite Image — ' + dates[idx].d;
      mapEl.appendChild(img);
      // Add crosshair overlay
      var crosshair = document.createElement('div');
      crosshair.style.cssText = 'position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);pointer-events:none;z-index:10;';
      crosshair.innerHTML = '<div style="width:24px;height:24px;border:2px solid #ff382f;border-radius:50%;box-shadow:0 0 12px rgba(255,56,47,0.5);animation:satPulse 1.5s infinite;"></div><div style="position:absolute;top:-8px;left:50%;transform:translateX(-50%);background:rgba(14,20,28,0.9);border:1px solid #22d3ee;border-radius:4px;padding:2px 6px;color:#e2e8f0;font-size:9px;font-family:monospace;white-space:nowrap;">' + lat.toFixed(5) + ', ' + lon.toFixed(5) + '</div>';
      mapEl.style.position = 'relative';
      mapEl.appendChild(crosshair);
    };
    img.onerror = function() {
      // This date failed, try next
      tryDate(idx + 1);
    };
    img.src = url;
  }

  tryDate(0);
}

function addEvidenceMarkers(lat, lon) {
  if (!satEvidenceMap) return;
  var fireIcon = L.divIcon({ className: '', html: '<div style="width:22px;height:22px;background:#ff382f;border:3px solid #fff;border-radius:50%;box-shadow:0 0 18px rgba(255,56,47,0.7);animation:satPulse 1.5s infinite;"></div><style>@keyframes satPulse{0%,100%{transform:scale(1);opacity:1}50%{transform:scale(1.3);opacity:0.7}}</style>', iconSize: [22,22], iconAnchor: [11,11] });
  L.marker([lat, lon], { icon: fireIcon }).addTo(satEvidenceMap);
}

function closeSatelliteEvidence() {
  var modal = document.getElementById('satEvidenceModal');
  if (modal) modal.style.display = 'none';
  if (satEvidenceMap) { satEvidenceMap.remove(); satEvidenceMap = null; }
}

function downloadSatelliteImage() {
  var container = document.getElementById('satEvidenceMapContainer');
  if (!container) return;
  var btn = document.getElementById('satEvidenceDownload');
  if (btn) { btn.textContent = '⏳ Capturing...'; btn.disabled = true; }

  html2canvas(container, {
    useCORS: true,
    allowTaint: true,
    backgroundColor: '#0b1118',
    scale: 2,
  }).then(function(canvas) {
    var link = document.createElement('a');
    link.download = 'AgniRakshak_Evidence_' + Date.now() + '.png';
    link.href = canvas.toDataURL('image/png');
    link.click();
    if (btn) { btn.textContent = '✅ Downloaded!'; setTimeout(function() { btn.textContent = '⬇️ Download'; btn.disabled = false; }, 2000); }
  }).catch(function(err) {
    console.error('Download failed:', err);
    if (btn) { btn.textContent = '❌ Failed'; setTimeout(function() { btn.textContent = '⬇️ Download'; btn.disabled = false; }, 2000); }
  });
}

// Wire up modal close + download buttons
document.addEventListener('DOMContentLoaded', function() {
  var closeBtn = document.getElementById('satEvidenceClose');
  var backdrop = document.getElementById('satEvidenceBackdrop');
  var dlBtn = document.getElementById('satEvidenceDownload');
  if (closeBtn) closeBtn.addEventListener('click', closeSatelliteEvidence);
  if (backdrop) backdrop.addEventListener('click', closeSatelliteEvidence);
  if (dlBtn) dlBtn.addEventListener('click', downloadSatelliteImage);
});

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
    nrtData = window.THERMOSCOPE_DATA.nrtData || [];
    alertsData = window.THERMOSCOPE_DATA.alertsData || [];
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

      try {
        nrtData = await loadCSVWithFallback([
          "../data/processed/nrt_detections.csv",
          "data/processed/nrt_detections.csv",
        ]);
      } catch (error) { console.warn("nrt_detections.csv unavailable.", error); nrtData = []; }

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

  // ==========================================================
  // GEOGRAPHIC FILTER — remove grids in Nepal/China/Tibet
  // Our bounding box (74.5-85E, 23.5-31.5N) spills into Nepal & Tibet.
  // Keep only grids within India's approximate boundaries.
  // ==========================================================
  function isInIndia(lat, lon) {
    // Tibet/China: everything above 30N is outside India in our study area
    if (lat >= 30) return false;
    // Nepal region: between 27N-30N, only Indian territory is west of ~80E
    if (lat >= 27 && lon >= 80) return false;
    // Far east: beyond 84.5E is Nepal/Bangladesh territory
    if (lon >= 84.5) return false;
    return true;
  }
  const beforeGeoFilter = gridData.length;
  gridData = gridData.filter(row => isInIndia(row.latitude, row.longitude));
  riskZoneData = riskZoneData.filter(row => isInIndia(row.latitude, row.longitude));
  const removedByGeo = beforeGeoFilter - gridData.length;
  if (removedByGeo > 0) console.log("Removed " + removedByGeo + " grids outside India (Nepal/China)");
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

  // Filter fire sites outside India
  fireSiteData = fireSiteData.filter(row => isInIndia(row.latitude, row.longitude));

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

  // NRT live layer
  initNrtLayer();
  renderNrtLayer();
  startNrtAutoRefresh();

  // NRT fetch button in sidebar
  initNrtFetchButton();

  // Alert badge in nav
  updateAlertBadge();

  // NRT status readout
  updateNrtReadout();

  // Top 10 map markers (after map is initialized)
  renderTop10OnMap();

  // Premium intro screen — live metrics + enter-dashboard wiring
  populateIntroMetrics();
  initIntro();
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
  const mNrtCount = document.getElementById("mNrtCount");

  if (mTotalCells) mTotalCells.textContent = num(total);
  if (mTotalDetections) mTotalDetections.textContent = num(totalDetections);
  if (mCritical) mCritical.textContent = num(critical);
  if (mHigh) mHigh.textContent = num(high);
  if (mAvgFrp) mAvgFrp.textContent = num(avgFrp, 2);
  if (mNrtCount) mNrtCount.textContent = num(nrtData.length);
}

// ============================================================
// TOP 10 (original)
// ============================================================

function renderTop10() {
  const top10 = [...gridData].sort((a, b) => Number(b.risk_score) - Number(a.risk_score)).slice(0, 10);
  const element = document.getElementById("top10List");
  if (!element) return;

  element.innerHTML = top10.map((row, index) => `
    <div class="top10-row" data-grid="${row.grid_id}" data-rank="${index + 1}">
      <span>
        <span class="top10-rank">#${index + 1}</span>
        ${row.grid_id}
      </span>
      <span class="top10-score">${Number(row.risk_score).toFixed(1)}</span>
    </div>
  `).join("");

  element.querySelectorAll(".top10-row").forEach(row => {
    row.addEventListener("click", () => {
      flyToGrid(row.dataset.grid);
    });
  });

}

// ============================================================
// TOP 10 MAP MARKERS
// ============================================================

const TOP10_RANK_COLORS = [
  "#00e5ff", "#18ffff", "#40c4ff", "#448aff", "#536dfe",
  "#7c4dff", "#e040fb", "#ff4081", "#ff5252", "#ff6e40",
];

function renderTop10OnMap() {
  if (!map) return;
  if (!top10Layer) top10Layer = L.layerGroup();
  top10Layer.clearLayers();

  const top10 = [...gridData]
    .sort((a, b) => Number(b.risk_score) - Number(a.risk_score))
    .slice(0, 10);

  top10.forEach((row, index) => {
    const lat = Number(row.map_latitude ?? row.latitude);
    const lon = Number(row.map_longitude ?? row.longitude);
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) return;

    const rank = index + 1;
    const score = Number(row.risk_score) || 0;
    const riskLevel = String(row.risk_level || "HIGH").toUpperCase();
    const color = TOP10_RANK_COLORS[index] || "#ffae42";
    const fireType = FIRE_TYPE_LABELS[normalizeFireType(row.fire_type)] || row.fire_type || "";
    const radius = 18 - index; // #1=18, #10=9

    // Outer glow ring
    const ring = L.circleMarker([lat, lon], {
      radius: radius + 10,
      color: color,
      weight: 1,
      fillColor: color,
      fillOpacity: 0.08,
      className: "top10-ring",
      interactive: false,
    });
    top10Layer.addLayer(ring);

    // Main marker
    const marker = L.circleMarker([lat, lon], {
      radius,
      color: color,
      weight: 3,
      fillColor: color,
      fillOpacity: 0.8,
      className: "top10-marker",
    });

    // Rank badge via divIcon
    const rankIcon = L.divIcon({
      className: "top10-rank-icon",
      html: `<span class="top10-rank-badge" style="background:${color};">#${rank}</span>`,
      iconSize: [32, 18],
      iconAnchor: [16, radius + 20],
    });
    const rankMarker = L.marker([lat, lon], { icon: rankIcon, interactive: false });
    top10Layer.addLayer(rankMarker);

    // Facility info for Top 10
    const t10Facility = getFacilityInfo(row);
    const t10Geo = reverseGeocode(lat, lon);
    const displayName = row.display_site_name || row.site_name || row.grid_id;
    const isGIS = row.is_gis_confirmed;

    // Popup
    marker.bindPopup(`
      <div style="min-width:240px;font-family:Arial,sans-serif;line-height:1.6;">
        <div style="display:flex;align-items:center;gap:8px;margin-bottom:4px;">
          <span style="display:inline-block;width:28px;height:28px;border-radius:50%;background:${color};color:#fff;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:13px;">${rank}</span>
          <b style="font-size:14px;">Top ${rank} High-Risk Zone</b>
        </div>
        ${t10Facility.name ? `<div style="background:rgba(168,85,247,0.1);border:1px solid rgba(168,85,247,0.2);border-radius:4px;padding:4px 8px;margin:4px 0;font-size:12px;">🏭 <b>${t10Facility.name}</b>${t10Facility.type ? ` · ${t10Facility.type}` : row.display_site_type ? ` · ${row.display_site_type}` : ""} ${isGIS ? `<span style=\"color:#20e889;\">✓</span>` : ""}</div>` : ""}
        ${t10Geo && t10Geo.state !== "Unknown" ? `<div style="background:rgba(34,211,238,0.08);border:1px solid rgba(34,211,238,0.2);border-radius:4px;padding:4px 8px;margin:4px 0;font-size:11px;">🗺️ <b>${t10Geo.state}</b>${t10Geo.nearestCity ? ` · 🏙️ ${t10Geo.nearestCity}` : ""}</div>` : ""}
        <hr style="margin:4px 0;border-color:#2a3a4a;">
        <b>Grid:</b> <code style="background:#1a2533;padding:1px 5px;border-radius:3px;">${row.grid_id}</code><br>
        <b>Risk Score:</b> <span style="font-size:16px;color:${color};font-weight:700;">${score.toFixed(1)}</span><br>
        <b>Risk Level:</b> ${riskLevel}<br>
        <b>Total Detections:</b> ${Number(row.total_detections).toLocaleString("en-IN")}<br>
        <b>Avg FRP:</b> ${Number(row.avg_frp).toFixed(2)} MW<br>
        <b>Max FRP:</b> ${Number(row.max_frp).toFixed(2)} MW<br>
        ${fireType ? `<b>Fire Type:</b> ${fireType}<br>` : ""}
        <b>Coords:</b> ${lat.toFixed(5)}, ${lon.toFixed(5)}
      </div>
    `);

    // Click → fly + show intel
    marker.on("click", () => {
      map.flyTo([lat, lon], 12, { animate: true, duration: 0.8 });
      showGridIntel(row);
      selectFireForChat(row);
    });

    // Tooltip
    marker.bindTooltip(
      `<b>#${rank}</b> &middot; ${score.toFixed(1)} &middot; ${riskLevel} &middot; ${row.grid_id}`,
      { direction: "top", offset: [0, -radius - 10], className: "top10-tooltip" }
    );

    top10Layer.addLayer(marker);
  });

  // Add to map if toggle is on
  const toggle = document.getElementById("lyrTop10");
  if (toggle && toggle.checked && !map.hasLayer(top10Layer)) {
    top10Layer.addTo(map);
  }
}

function toggleTop10Layer() {
  if (!map || !top10Layer) return;
  const toggle = document.getElementById("lyrTop10");
  if (!toggle) return;
  if (toggle.checked) {
    top10Layer.addTo(map);
  } else {
    map.removeLayer(top10Layer);
  }
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

    marker.on("click", () => { showSiteIntel(row); selectFireForChat(row); });
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
    <button class="sat-evidence-btn" onclick="showSatelliteEvidence(${Number(row.latitude)},${Number(row.longitude)},'${title}')">🛰️ Satellite Evidence</button>
    <div id="satEvidenceDateInfo" style="font-size:9px;color:#64748b;margin-top:5px;text-align:center;"></div>
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
    marker.on("click", () => { showRiskZoneIntel(zone); selectFireForChat(zone); });

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
  const zLat = Number(zone.latitude);
  const zLon = Number(zone.longitude);
  const geo = reverseGeocode(zLat, zLon);

  // Find worst cell in this zone to get facility name
  let worstCell = null;
  const mergedIds = String(zone.grid_ids_merged || "").split(";").map(s => s.trim());
  if (mergedIds.length && mergedIds[0]) {
    let maxScore = -1;
    mergedIds.forEach(gid => {
      const cell = gridData.find(r => String(r.grid_id) === gid);
      if (cell && Number(cell.risk_score) > maxScore) {
        maxScore = Number(cell.risk_score);
        worstCell = cell;
      }
    });
  }
  // Fallback: find nearest grid cell by lat/lon
  if (!worstCell) {
    let minDist = Infinity;
    gridData.forEach(r => {
      const d = Math.sqrt(Math.pow(Number(r.latitude) - zLat, 2) + Math.pow(Number(r.longitude) - zLon, 2));
      if (d < minDist) { minDist = d; worstCell = r; }
    });
  }
  const facility = worstCell ? getFacilityInfo(worstCell) : null;
  const displayName = worstCell?.display_site_name || worstCell?.site_name || zoneId;
  const isGIS = worstCell?.is_gis_confirmed;
  const siteType = worstCell?.display_site_type || "";

  element.innerHTML = `
    <div class="grid-id">${displayName}</div>
    ${geo && geo.state !== "Unknown" ? `<div style="background:rgba(34,211,238,0.08);border:1px solid rgba(34,211,238,0.2);border-radius:6px;padding:5px 8px;margin:6px 0;font-size:10.5px;">
      🗺️ <strong>${geo.state}</strong>${geo.nearestCity ? ` · 🏙️ ${geo.nearestCity}${geo.withinCity ? "" : ` (${geo.distanceToCityKm} km)`}` : ""}
    </div>` : ""}
    ${facility && facility.name ? `<div style="background:rgba(168,85,247,0.08);border:1px solid rgba(168,85,247,0.2);border-radius:6px;padding:5px 8px;margin:6px 0;font-size:10.5px;">
      🏭 <strong>${facility.name}</strong>${facility.type ? ` · ${facility.type}` : siteType ? ` · ${siteType}` : ""}
      ${isGIS ? ` <span style="color:#20e889;">✓ Verified</span>` : ""}
    </div>` : ""}
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
    <button class="sat-evidence-btn" onclick="showSatelliteEvidence(${zLat},${zLon},'${zoneId}')">🛰️ Satellite Evidence</button>
    <div id="satEvidenceDateInfo" style="font-size:9px;color:#64748b;margin-top:5px;text-align:center;"></div>
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
  const gLat = Number(row.map_latitude ?? row.latitude);
  const gLon = Number(row.map_longitude ?? row.longitude);
  const geo = reverseGeocode(gLat, gLon);
  const facility = getFacilityInfo(row);

  element.innerHTML = `
    <div class="grid-id">${row.display_site_name || row.grid_id}</div>
    ${geo && geo.state !== "Unknown" ? `<div style="background:rgba(34,211,238,0.08);border:1px solid rgba(34,211,238,0.2);border-radius:6px;padding:5px 8px;margin:6px 0;font-size:10.5px;">
      🗺️ <strong>${geo.state}</strong>${geo.nearestCity ? ` · 🏙️ ${geo.nearestCity}${geo.withinCity ? "" : ` (${geo.distanceToCityKm} km)`}` : ""}
    </div>` : ""}
    ${row.is_gis_confirmed
      ? `<div style="color:#3cff9a; font-size:10.5px; margin-bottom:8px;">✓ GIS-confirmed real site${row.display_site_type ? ` · ${row.display_site_type}` : ""}</div>`
      : `<div style="color:#94a6b8; font-size:10.5px; margin-bottom:8px;">Pattern-based classification (no matched real-world site)</div>`
    }
    ${facility.name ? `<div style="background:rgba(168,85,247,0.08);border:1px solid rgba(168,85,247,0.2);border-radius:6px;padding:5px 8px;margin:6px 0;font-size:10.5px;">
      🏭 <strong>${facility.name}</strong>${facility.type ? ` · ${facility.type}` : ""}
      ${facility.isRealGIS ? ` <span style="color:#20e889;">✓ Verified</span>` : ""}
    </div>` : ""}
    <div class="risk-label" style="border-color:${riskColor}; color:${riskColor};">${riskLevel} RISK</div>
    <div class="type-label" style="border:1px solid ${typeColor}; color:${typeColor};">
      ${typeLabel}${confidence !== null ? ` · ${confidence}% confidence` : ""}
    </div>
    <div class="intel-row"><span>Risk Score</span><strong>${Number(row.risk_score).toFixed(1)}</strong></div>
    <div class="intel-row"><span>Latitude</span><strong>${gLat.toFixed(6)}</strong></div>
    <div class="intel-row"><span>Longitude</span><strong>${gLon.toFixed(6)}</strong></div>
    <div class="intel-row"><span>Total Detections</span><strong>${num(row.total_detections)}</strong></div>
    <div class="intel-row"><span>Active Days</span><strong>${num(row.active_days)}</strong></div>
    <div class="intel-row"><span>Avg FRP</span><strong>${Number(row.avg_frp).toFixed(2)} MW</strong></div>
    <div class="intel-row"><span>Max FRP</span><strong>${Number(row.max_frp).toFixed(2)} MW</strong></div>
    <div class="intel-row"><span>Recurrence Ratio</span><strong>${(Number(row.recurrence_ratio) * 100).toFixed(0)}%</strong></div>
    <div class="intel-row"><span>Persistent Months</span><strong>${num(row.persistent_months)}</strong></div>
    <div class="intel-row"><span>Detections (30d)</span><strong>${num(row.detections_30d)}</strong></div>
    <div class="intel-row"><span>Detections (90d)</span><strong>${num(row.detections_90d)}</strong></div>
    <div class="intel-reason">${reason}</div>
    <button class="sat-evidence-btn" onclick="showSatelliteEvidence(${gLat},${gLon},'${row.display_site_name || row.grid_id}')">🛰️ Satellite Evidence</button>
    <div id="satEvidenceDateInfo" style="font-size:9px;color:#64748b;margin-top:5px;text-align:center;"></div>
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

  const lyrNrt = document.getElementById("lyrNrt");
  if (lyrNrt) {
    lyrNrt.addEventListener("change", toggleNrtLayer);
  }

  const lyrTop10 = document.getElementById("lyrTop10");
  if (lyrTop10) {
    lyrTop10.addEventListener("change", toggleTop10Layer);
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

// Build the merged alert list (engine alerts first, then derived,
// deduped by grid). Shared by the Alerts tab and the Report generator.
function computeAlerts() {
  // === ENGINE ALERTS (from alert_engine.py) ===
  // These are real alerts generated by comparing NRT data
  // against the historical risk model.
  var nowStr = new Date().toISOString().slice(0,19).replace('T',' ');
  const engineAlerts = (alertsData || []).map(a => ({
    alert: a.description || a.alert_type || "Unknown alert",
    grid: a.grid_id || "",
    type: FIRE_TYPE_LABELS[normalizeFireType(a.fire_type)] || a.fire_type || "",
    severity: (a.severity || "medium").toLowerCase(),
    status: a.status || "ACTIVE",
    timestamp: a.timestamp || nowStr,
    nrtFrp: a.nrt_max_frp || 0,
    histRisk: a.historical_risk_score || 0,
    latitude: a.latitude || 0,
    longitude: a.longitude || 0,
    source: "engine",
  }));

  // === FALLBACK: derive alerts from grid data ===
  const derivedAlerts = [];
  gridData.forEach(r => {
    if (r.risk_level === "CRITICAL" && r.detections_30d > 5) {
      derivedAlerts.push({ alert: "Critical fire risk — persistent high FRP", grid: r.grid_id, type: FIRE_TYPE_LABELS[r.fire_type] || r.fire_type, severity: "critical", status: "Active", timestamp: nowStr, source: "derived" });
    } else if (r.risk_level === "HIGH" && r.recurrence_ratio > 0.6) {
      derivedAlerts.push({ alert: "High risk — recurring thermal anomaly", grid: r.grid_id, type: FIRE_TYPE_LABELS[r.fire_type] || r.fire_type, severity: "high", status: "Active", timestamp: nowStr, source: "derived" });
    } else if (r.risk_level === "HIGH" && r.detections_30d > r.detections_90d / 3) {
      derivedAlerts.push({ alert: "Escalating thermal activity", grid: r.grid_id, type: FIRE_TYPE_LABELS[r.fire_type] || r.fire_type, severity: "medium", status: "Monitoring", timestamp: nowStr, source: "derived" });
    }
  });

  // Merge: engine alerts first, then derived (dedup by grid_id)
  const seenGrids = new Set(engineAlerts.map(a => a.grid));
  return [
    ...engineAlerts,
    ...derivedAlerts.filter(a => !seenGrids.has(a.grid)),
  ].slice(0, 100);
}

function renderAlertsTab() {
  const mergedAlerts = computeAlerts();

  document.getElementById("alertCount").textContent = mergedAlerts.length;
  const tbody = document.querySelector("#alertsTable tbody");
  if (!tbody) return;

  tbody.innerHTML = mergedAlerts.map(a => `<tr>
    <td>${a.alert}</td>
    <td style="font-family:monospace;font-size:10px;">${a.grid}</td>
    <td style="font-size:10px;">${a.type}</td>
    <td><span class="alert-severity ${a.severity}">${a.severity.toUpperCase()}</span></td>
    <td style="color:#7890a8;font-size:10px;">${a.status}</td>
    <td style="font-family:monospace;font-size:9px;color:#64748b;">${a.timestamp || nowStr}</td>
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
// REPORTS TAB — WORKING REPORT GENERATOR
// ============================================================
// Reports are built live from the loaded dashboard data and rendered
// in the preview pane. Each report type has its own lookback window;
// Incident Report adds a deep-dive on the most severe active site.
// Print / PDF and standalone HTML download reuse the same markup.
// ============================================================

const REPORT_TYPES = {
  "Daily Report":   { lookbackDays: 1,  accent: "#ff6b1a", desc: "24-hour fire activity snapshot" },
  "Weekly Report":  { lookbackDays: 7,  accent: "#3b82f6", desc: "7-day trend & risk summary" },
  "Monthly Report": { lookbackDays: 30, accent: "#a855f7", desc: "30-day seasonal & risk analysis" },
  "Incident Report":{ lookbackDays: 7,  accent: "#ff382f", desc: "Deep-dive on the most severe active site" },
};

const REPORT_STYLE = `
<style>
  .ar-report { font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; font-size: 12.5px; line-height: 1.7; color: var(--text-body, #e2e8f0); }
  .ar-report h1 { font-size: 22px; margin: 0; color: var(--text-primary, #f1f5f9); letter-spacing: 0.5px; }
  .ar-report h2 { font-size: 13px; font-weight: 700; color: var(--accent, #ff493d); letter-spacing: 1.4px; text-transform: uppercase; border-bottom: 2px solid var(--accent, #ff493d); padding-bottom: 6px; margin: 22px 0 10px; }
  .ar-report .ar-sub { color: var(--text-secondary, #94a3b8); font-size: 12px; margin-top: 4px; }
  .ar-report .ar-meta { display: flex; flex-wrap: wrap; gap: 6px 18px; margin-top: 12px; padding: 10px 12px; background: var(--bg-card-alt, #101820); border: 1px solid var(--border-card, #1e293b); border-radius: 8px; font-size: 11px; color: var(--text-secondary, #94a3b8); }
  .ar-report .ar-meta b { color: var(--text-primary, #f1f5f9); }
  .ar-report .ar-kpis { display: flex; flex-wrap: wrap; gap: 10px; margin-top: 14px; }
  .ar-report .ar-kpi { flex: 1 1 130px; min-width: 120px; background: var(--bg-card-alt, #101820); border: 1px solid var(--border-card, #1e293b); border-radius: 8px; padding: 10px 12px; }
  .ar-report .ar-kpi .k { font-size: 9px; letter-spacing: 1.2px; text-transform: uppercase; color: var(--text-muted, #64748b); }
  .ar-report .ar-kpi .v { font-size: 19px; font-weight: 700; font-family: 'SF Mono', Consolas, monospace; color: var(--text-primary, #f1f5f9); margin-top: 2px; }
  .ar-report .ar-kpi .d { font-size: 10px; color: var(--text-muted, #64748b); }
  .ar-report table { width: 100%; border-collapse: collapse; margin-top: 8px; font-size: 11.5px; }
  .ar-report th { text-align: left; padding: 7px 10px; border-bottom: 2px solid var(--border-accent, #2a3a4a); color: var(--text-secondary, #94a3b8); text-transform: uppercase; font-size: 9.5px; letter-spacing: 0.8px; white-space: nowrap; }
  .ar-report td { padding: 7px 10px; border-bottom: 1px solid var(--border-subtle, #1b2631); vertical-align: top; }
  .ar-report .ar-pill { display: inline-block; padding: 2px 9px; border-radius: 4px; font-size: 10px; font-weight: 700; color: #fff; }
  .ar-report .ar-num { font-family: 'SF Mono', Consolas, monospace; }
  .ar-report .ar-rec { display: flex; gap: 8px; align-items: flex-start; padding: 8px 12px; border-left: 3px solid var(--accent, #ff493d); background: var(--accent-bg, rgba(255, 73, 61, 0.08)); margin: 8px 0; border-radius: 0 6px 6px 0; }
  .ar-report .ar-rec .n { color: var(--accent, #ff493d); font-weight: 700; font-family: monospace; }
  .ar-report .ar-bar { background: var(--bg-card-alt, #101820); border: 1px solid var(--border-card, #1e293b); border-radius: 6px; overflow: hidden; height: 10px; min-width: 60px; }
  .ar-report .ar-bar > div { height: 100%; background: var(--accent, #ff493d); }
  .ar-report .ar-note { font-size: 11px; color: var(--text-muted, #64748b); margin-top: 10px; }
  .ar-report .ar-foot { margin-top: 24px; padding-top: 10px; border-top: 1px solid var(--border-subtle, #1b2631); color: var(--text-muted, #64748b); font-size: 10px; line-height: 1.6; }
  @media print {
    * { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
    .ar-report { color: #111827 !important; font-size: 11px !important; }
    .ar-report h1 { color: #0f172a !important; }
    .ar-report h2 { color: #dc2626 !important; border-color: #dc2626 !important; }
    .ar-report .ar-sub, .ar-report .ar-meta, .ar-report .ar-note, .ar-report .ar-foot { color: #374151 !important; }
    .ar-report .ar-meta, .ar-report .ar-kpi, .ar-report .ar-bar { background: #f8fafc !important; border-color: #d1d5db !important; }
    .ar-report .ar-kpi .k { color: #6b7280 !important; }
    .ar-report .ar-kpi .v, .ar-report .ar-meta b { color: #0f172a !important; }
    .ar-report th { color: #374151 !important; border-color: #9ca3af !important; }
    .ar-report td { border-color: #e5e7eb !important; }
    .ar-report .ar-rec { background: #fef2f2 !important; border-color: #dc2626 !important; }
    .ar-report .ar-rec .n { color: #dc2626 !important; }
    .ar-report .ar-bar > div { background: #dc2626 !important; }
    .ar-report tr, .ar-report table { page-break-inside: avoid; }
  }
</style>
`;

function esc(value) {
  return String(value ?? "").replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

function pctOf(part, total) {
  return total > 0 ? Math.round((part / total) * 100) : 0;
}

function repPill(level) {
  const colors = { CRITICAL: "#ff382f", HIGH: "#ff6b1a", MODERATE: "#ffae42", LOW: "#20e889" };
  return `<span class="ar-pill" style="background:${colors[level] || "#5b6b7a"};">${level}</span>`;
}

function repFirePill(key) {
  const colors = { INDUSTRIAL_PERSISTENT: "#a855f7", AGRICULTURAL_BURNING: "#ffd400", FOREST_WILDFIRE: "#22d3ee", UNCLASSIFIED: "#5b6b7a" };
  const label = FIRE_TYPE_LABELS[key] || key;
  return `<span class="ar-pill" style="background:${colors[key] || "#5b6b7a"};">${label}</span>`;
}

function repSitePill(key) {
  const aliases = { FOREST_WILDFIRE: "FOREST_FIRE", WILDFIRE: "FOREST_FIRE", INDUSTRIAL_PERSISTENT: "INDUSTRIAL", PERSISTENT: "INDUSTRIAL", CROP_BURNING: "AGRICULTURAL_BURNING", AGRICULTURAL: "AGRICULTURAL_BURNING" };
  const k = aliases[key] || key;
  const label = SITE_TYPE_LABELS[k] || k;
  return `<span class="ar-pill" style="background:${SITE_TYPE_COLORS[k] || "#5b6b7a"};">${label}</span>`;
}

function repSeverityPill(sev) {
  const colors = { critical: "#ff382f", high: "#ff6b1a", medium: "#ffae42", elevated: "#ffae42", normal: "#64748b" };
  return `<span class="ar-pill" style="background:${colors[String(sev).toLowerCase()] || "#64748b"};">${String(sev).toUpperCase()}</span>`;
}

function kpiCard(label, value, detail, color) {
  return `<div class="ar-kpi"><div class="k">${label}</div><div class="v" style="${color ? `color:${color};` : ""}">${value}</div><div class="d">${detail}</div></div>`;
}

function buildReportHtml(type) {
  const meta = REPORT_TYPES[type] || REPORT_TYPES["Daily Report"];
  const generatedAt = new Date().toLocaleString("en-IN", { dateStyle: "long", timeStyle: "short" });

  // ---- Core stats ----
  const activeGrids = gridData.length;
  const totalDetections = gridData.reduce((s, r) => s + (r.total_detections || 0), 0);
  const riskDist = { CRITICAL: 0, HIGH: 0, MODERATE: 0, LOW: 0 };
  gridData.forEach(r => { if (riskDist[r.risk_level] !== undefined) riskDist[r.risk_level]++; });
  const avgFrp = activeGrids ? gridData.reduce((s, r) => s + (r.avg_frp || 0), 0) / activeGrids : 0;
  const maxFrp = activeGrids ? Math.max(...gridData.map(r => r.max_frp || 0)) : 0;
  const alerts = computeAlerts();
  const criticalAlerts = alerts.filter(a => a.severity === "critical").length;

  // ---- NRT stats ----
  const nrtCount = nrtData.length;
  const nrtBySev = {};
  nrtData.forEach(d => { const s = String(d.nrt_severity || "normal").toLowerCase(); nrtBySev[s] = (nrtBySev[s] || 0) + 1; });
  const nrtMaxFrp = nrtCount ? Math.max(...nrtData.map(d => Number(d.frp) || 0)) : 0;
  const nrtLatest = nrtData.reduce((m, d) => (String(d.acq_date) > m ? String(d.acq_date) : m), "");

  // ---- Period activity from daily series ----
  const sortedDaily = [...dailyData].filter(r => r.date).sort((a, b) => String(a.date).localeCompare(String(b.date)));
  const cutoff = new Date(); cutoff.setDate(cutoff.getDate() - meta.lookbackDays);
  const cutoffStr = cutoff.toISOString().slice(0, 10);
  const prevCutoff = new Date(cutoff); prevCutoff.setDate(prevCutoff.getDate() - meta.lookbackDays);
  const prevCutoffStr = prevCutoff.toISOString().slice(0, 10);
  const periodRows = sortedDaily.filter(r => String(r.date) >= cutoffStr);
  const prevRows = sortedDaily.filter(r => String(r.date) >= prevCutoffStr && String(r.date) < cutoffStr);
  const periodDetections = periodRows.reduce((s, r) => s + (Number(r.detections) || 0), 0);
  const prevDetections = prevRows.reduce((s, r) => s + (Number(r.detections) || 0), 0);
  const changePct = prevDetections > 0 ? Math.round(((periodDetections - prevDetections) / prevDetections) * 100) : null;
  const peakDay = periodRows.reduce((m, r) => ((Number(r.detections) || 0) > (Number(m.detections) || 0) ? r : m), periodRows[0] || null);

  // ---- Fire type distribution ----
  const ftDist = {};
  gridData.forEach(r => { const k = normalizeFireType(r.fire_type); ftDist[k] = (ftDist[k] || 0) + 1; });
  const siteDist = {};
  fireSiteData.forEach(r => {
    const t = { FOREST_WILDFIRE: "FOREST_FIRE", WILDFIRE: "FOREST_FIRE", INDUSTRIAL_PERSISTENT: "INDUSTRIAL" }[String(r.fire_type).trim().toUpperCase()] || String(r.fire_type).trim().toUpperCase();
    siteDist[t] = (siteDist[t] || 0) + 1;
  });

  // ---- Top zones & NRT hotspots ----
  const top = [...gridData].sort((a, b) => (b.risk_score || 0) - (a.risk_score || 0)).slice(0, 8);
  const topNrt = [...nrtData].sort((a, b) => (Number(b.frp) || 0) - (Number(a.frp) || 0)).slice(0, 5);

  // ---- Incident deep-dive target ----
  let incident = null;
  if (type === "Incident Report" && activeGrids > 0) {
    const alertGridId = alerts[0]?.grid;
    incident = gridData.find(r => r.grid_id === alertGridId && r.detections_30d > 0)
      || [...gridData].sort((a, b) => (b.risk_score || 0) - (a.risk_score || 0))[0];
  }

  // ---- Executive summary ----
  const summaryP = incident
    ? `This incident report centers on <b>${esc(incident.display_site_name || incident.grid_id)}</b> (${Number(incident.latitude).toFixed(4)}, ${Number(incident.longitude).toFixed(4)}), the most severe active thermal site in the monitoring region. It carries a model risk score of <b>${Number(incident.risk_score).toFixed(1)}/100</b> (${repPill(incident.risk_level)}) and is classified as <b>${FIRE_TYPE_LABELS[normalizeFireType(incident.fire_type)] || "Unclassified"}</b>, with ${num(incident.detections_30d)} thermal detections in the last 30 days.`
    : `This ${esc(meta.desc.toLowerCase())} covers ${num(activeGrids)} active 5 km grid cells across North India. Since 2020, FIRMS recorded ${num(totalDetections)} thermal anomalies; ${num(riskDist.CRITICAL)} cells (${pctOf(riskDist.CRITICAL, activeGrids)}%) are rated <b>CRITICAL</b> and ${num(riskDist.HIGH)} (${pctOf(riskDist.HIGH, activeGrids)}%) <b>HIGH</b>. ${periodRows.length ? `${num(periodDetections)} detections fell inside the ${meta.lookbackDays}-day report window${changePct !== null ? ` — ${Math.abs(changePct)}% ${changePct >= 0 ? "higher" : "lower"} than the preceding window` : ""}.` : "No daily activity series is available for the report window."} ${alerts.length ? `${alerts.length} active alert${alerts.length > 1 ? "s" : ""}${criticalAlerts ? ` (including ${criticalAlerts} critical)` : ""} require attention.` : "No active alerts currently."}`;

  // ---- Section: Incident deep-dive ----
  let incidentHtml = "";
  if (incident) {
    incidentHtml = `
  <h2>Incident Deep-Dive</h2>
  <table>
    <tr><th style="width:190px;">Site / Facility</th><td><b>${esc(incident.display_site_name || incident.grid_id)}</b></td></tr>
    <tr><th>Grid ID</th><td class="ar-num">${esc(incident.grid_id)}</td></tr>
    <tr><th>Coordinates</th><td class="ar-num">${Number(incident.latitude).toFixed(5)}, ${Number(incident.longitude).toFixed(5)}</td></tr>
    <tr><th>Coordinate Source</th><td>${incident.is_gis_confirmed ? "Verified against ESA WorldCover (real GIS coordinates)" : "Grid centroid estimate"}</td></tr>
    <tr><th>Risk Score</th><td class="ar-num">${Number(incident.risk_score).toFixed(1)} / 100 &nbsp; ${repPill(incident.risk_level)}</td></tr>
    <tr><th>Fire Type</th><td>${repFirePill(normalizeFireType(incident.fire_type))}${incident.fire_type_confidence ? ` <span class="ar-note">${Math.round(Number(incident.fire_type_confidence) * 100)}% confidence</span>` : ""}</td></tr>
    ${incident.display_site_type ? `<tr><th>Site Type</th><td>${esc(incident.display_site_type)}</td></tr>` : ""}
    <tr><th>Total Detections</th><td class="ar-num">${num(incident.total_detections)}</td></tr>
    <tr><th>Active Days</th><td class="ar-num">${num(incident.active_days)}</td></tr>
    <tr><th>Last 30 Days</th><td class="ar-num">${num(incident.detections_30d)} detections</td></tr>
    <tr><th>Last 90 Days</th><td class="ar-num">${num(incident.detections_90d)} detections</td></tr>
    <tr><th>Avg / Max FRP</th><td class="ar-num">${Number(incident.avg_frp).toFixed(2)} / ${Number(incident.max_frp).toFixed(2)} MW</td></tr>
    <tr><th>Recurrence</th><td class="ar-num">${(Number(incident.recurrence_ratio) * 100).toFixed(0)}% of active months</td></tr>
    <tr><th>Persistence</th><td class="ar-num">${num(incident.persistent_months)} months</td></tr>
  </table>`;
  }

  // ---- Section: Risk distribution ----
  const riskTable = `<table><thead><tr><th>Risk Level</th><th>Grid Cells</th><th>Share</th></tr></thead><tbody>${Object.entries(riskDist).map(([lv, c]) => `<tr><td>${repPill(lv)}</td><td class="ar-num">${num(c)}</td><td class="ar-num">${pctOf(c, activeGrids)}%</td></tr>`).join("")}</tbody></table>`;

  // ---- Section: Fire type distribution ----
  let ftTable = `<table><thead><tr><th>Fire Type</th><th>Grid Cells</th><th>Share</th></tr></thead><tbody>${Object.entries(ftDist).map(([k, c]) => `<tr><td>${repFirePill(k)}</td><td class="ar-num">${num(c)}</td><td class="ar-num">${pctOf(c, activeGrids)}%</td></tr>`).join("")}</tbody></table>`;
  if (Object.keys(siteDist).length) {
    ftTable += `<p class="ar-note">Verified sites (ESA WorldCover + OSM cross-checked):</p><table><thead><tr><th>Site Type</th><th>Sites</th><th>Share</th></tr></thead><tbody>${Object.entries(siteDist).map(([k, c]) => `<tr><td>${repSitePill(k)}</td><td class="ar-num">${num(c)}</td><td class="ar-num">${pctOf(c, fireSiteData.length)}%</td></tr>`).join("")}</tbody></table>`;
  }

  // ---- Section: Period activity ----
  let periodTable = `<p class="ar-note">Daily activity series not available for this window.</p>`;
  if (periodRows.length) {
    const barRows = periodRows.slice(-10);
    const barMax = Math.max(1, ...barRows.map(r => Number(r.detections) || 0));
    periodTable = `
    <p style="margin-top:8px;">Total in window: <b class="ar-num">${num(periodDetections)}</b> · Avg/day: <b class="ar-num">${(periodDetections / periodRows.length).toFixed(1)}</b> · Peak: <b>${esc(String(peakDay?.date || "—"))}</b> (${num(peakDay ? Number(peakDay.detections) || 0 : 0)})${changePct !== null ? ` · vs previous window: <b class="ar-num">${changePct >= 0 ? "+" : ""}${changePct}%</b>` : ""}</p>
    <table><thead><tr><th>Date</th><th>Detections</th><th>Intensity</th></tr></thead><tbody>${barRows.map(r => { const v = Number(r.detections) || 0; const w = Math.max(2, Math.round((v / barMax) * 100)); return `<tr><td class="ar-num" style="white-space:nowrap;">${esc(String(r.date).slice(5))}</td><td class="ar-num">${num(v)}</td><td style="width:45%;"><div class="ar-bar"><div style="width:${w}%;"></div></div></td></tr>`; }).join("")}</tbody></table>`;
  }

  // ---- Section: Top risk zones ----
  const topTable = `<table><thead><tr><th>#</th><th>Site / Grid</th><th>Coordinates</th><th>Risk</th><th>Level</th><th>Detections</th><th>Fire Type</th></tr></thead><tbody>${top.map((r, i) => `<tr><td class="ar-num" style="color:#ff6b5e;font-weight:700;">${i + 1}</td><td>${esc(r.display_site_name || r.grid_id)}</td><td class="ar-num">${Number(r.map_latitude || r.latitude).toFixed(4)}, ${Number(r.map_longitude || r.longitude).toFixed(4)}</td><td class="ar-num">${Number(r.risk_score).toFixed(1)}</td><td>${repPill(r.risk_level)}</td><td class="ar-num">${num(r.total_detections)}</td><td>${repFirePill(normalizeFireType(r.fire_type))}</td></tr>`).join("")}</tbody></table>`;

  // ---- Section: Live NRT ----
  let nrtTable = "";
  if (nrtCount) {
    const sevRows = Object.entries(nrtBySev).map(([s, c]) => `<tr><td>${repSeverityPill(s)}</td><td class="ar-num">${num(c)}</td></tr>`).join("");
    const nrtRows = topNrt.map(d => `<tr><td class="ar-num">${Number(d.frp || 0).toFixed(1)}</td><td>${repSeverityPill(String(d.nrt_severity || "normal").toLowerCase())}</td><td>${esc(d.grid_id || "")}</td><td class="ar-num">${Number(d.latitude).toFixed(4)}, ${Number(d.longitude).toFixed(4)}</td><td class="ar-num">${esc(d.acq_date || "")}</td></tr>`).join("");
    nrtTable = `
    <p class="ar-note">${num(nrtCount)} live detections in the latest NRT pass (max FRP ${Number(nrtMaxFrp).toFixed(1)} MW).</p>
    <table><thead><tr><th>Severity</th><th>Count</th></tr></thead><tbody>${sevRows}</tbody></table>
    <p class="ar-note">Top detections by FRP:</p>
    <table><thead><tr><th>FRP (MW)</th><th>Severity</th><th>Grid</th><th>Coordinates</th><th>Date</th></tr></thead><tbody>${nrtRows}</tbody></table>`;
  }

  // ---- Section: Active alerts ----
  const alertsTable = `<table><thead><tr><th>Alert</th><th>Grid</th><th>Severity</th><th>Status</th><th>Time</th></tr></thead><tbody>${alerts.slice(0, 10).map(a => `<tr><td>${esc(a.alert)}</td><td class="ar-num">${esc(a.grid)}</td><td>${repSeverityPill(a.severity)}</td><td>${esc(a.status)}</td><td class="ar-num">${esc(a.timestamp || "—")}</td></tr>`).join("")}</tbody></table>`;

  // ---- Section: Recommendations (auto-generated) ----
  const recs = [];
  if (riskDist.CRITICAL > 0) {
    const names = top.filter(r => r.risk_level === "CRITICAL").slice(0, 3).map(r => esc(r.display_site_name || r.grid_id)).join(", ");
    recs.push(`Immediately schedule ground verification of critical cells (risk score ≥ 75): <b>${names}</b>.`);
  }
  if ((nrtBySev.critical || 0) > 0) {
    recs.push(`Deploy field response to <b>${nrtBySev.critical}</b> live critical NRT detection${nrtBySev.critical > 1 ? "s" : ""} flagged in the latest satellite pass.`);
  }
  const industrial = gridData.filter(r => normalizeFireType(r.fire_type) === "INDUSTRIAL_PERSISTENT" && r.risk_level !== "LOW").sort((a, b) => (b.risk_score || 0) - (a.risk_score || 0)).slice(0, 3);
  if (industrial.length) {
    recs.push(`Report persistent industrial thermal sources to the State Pollution Control Board (SPCB): <b>${industrial.map(r => esc(r.display_site_name || r.grid_id)).join(", ")}</b>.`);
  }
  const escalating = gridData.filter(r => r.risk_level === "HIGH" && r.detections_30d > r.detections_90d / 3);
  if (escalating.length) {
    recs.push(`Escalating activity at <b>${escalating.length}</b> high-risk cell${escalating.length > 1 ? "s" : ""} — 30-day detections are outpacing the 90-day baseline; step up monitoring frequency.`);
  }
  if (changePct !== null && changePct > 25) {
    recs.push(`Window detections rose <b>${changePct}%</b> versus the prior period; correlate with seasonal crop-burning calendars before committing resources.`);
  }
  if (incident) {
    recs.push(`Open a formal incident record for <b>${esc(incident.display_site_name || incident.grid_id)}</b> and notify the District Disaster Management Office for follow-up inspection.`);
  }
  recs.push("Continue 5-minute NRT auto-monitoring, rerun the alert engine after every fetch, and archive this report for compliance records.");

  // ---- Assemble ----
  const sections = [];
  sections.push(`<div style="padding:14px 16px;background:linear-gradient(135deg,${meta.accent}26,transparent 70%);border-left:4px solid ${meta.accent};border-radius:8px;"><h1>🔥 ${esc(type)}</h1><div class="ar-sub">${esc(meta.desc)} — Region: North India</div></div>`);
  sections.push(`<div class="ar-meta"><span>Generated: <b>${esc(generatedAt)}</b></span><span>Report Type: <b>${esc(type)}</b></span><span>Data: <b>NASA FIRMS · ESA WorldCover · OSM</b></span>${nrtLatest ? `<span>Latest NRT pass: <b>${esc(nrtLatest)}</b></span>` : ""}<span>Model: <b>RandomForest risk score (0–100)</b></span></div>`);
  sections.push(`<h2>Key Indicators</h2><div class="ar-kpis">${kpiCard("Active Grid Cells", num(activeGrids), "5 km FIRMS cells")}${kpiCard("Total Detections", num(totalDetections), "2020 → present")}${kpiCard("Critical Cells", num(riskDist.CRITICAL), "risk score ≥ 75", "#ff382f")}${kpiCard("Active Alerts", num(alerts.length), `${criticalAlerts} critical`, "#ff6b1a")}${kpiCard("Live NRT Detections", num(nrtCount), nrtMaxFrp ? `max FRP ${Number(nrtMaxFrp).toFixed(1)} MW` : "no live pass", "#3b82f6")}${kpiCard("Avg FRP", `${Number(avgFrp).toFixed(2)} MW`, `max ${Number(maxFrp).toFixed(1)} MW`)}</div>`);
  sections.push(`<h2>Executive Summary</h2><p style="margin-top:8px;">${summaryP}</p>`);
  if (incidentHtml) sections.push(incidentHtml);
  sections.push(`<h2>Risk Distribution</h2>${riskTable}`);
  sections.push(`<h2>Fire Type Distribution</h2>${ftTable}`);
  sections.push(`<h2>${meta.lookbackDays === 1 ? "Last 24 Hours" : `Period Activity — Last ${meta.lookbackDays} Days`}</h2>${periodTable}`);
  if (top.length) sections.push(`<h2>Top Risk Zones</h2>${topTable}`);
  if (nrtTable) sections.push(`<h2>Live NRT Detections</h2>${nrtTable}`);
  if (alerts.length) sections.push(`<h2>Active Alerts</h2>${alertsTable}`);
  sections.push(`<h2>Recommendations</h2>${recs.map((r, i) => `<div class="ar-rec"><span class="n">${i + 1}.</span><span>${r}</span></div>`).join("")}`);
  sections.push(`<div class="ar-foot">Auto-generated by <b>AgniRakshak</b> — AI Fire Risk Intelligence &amp; Satellite Monitoring.<br>Source: NASA FIRMS VIIRS/MODIS thermal detections (2020–present), ESA WorldCover 10m land cover, OpenStreetMap facility data.<br>Risk scores are model-based rankings for early warning; they do not confirm the cause of any fire.</div>`);

  return REPORT_STYLE + `<div class="ar-report">${sections.join("")}</div>`;
}

function buildStandaloneReportHtml(type) {
  const title = `${type} — AgniRakshak`;
  return `<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>${esc(title)}</title>
<style>body { margin: 0; padding: 28px 32px; background: #ffffff; } @media print { body { padding: 0; } }</style>
</head>
<body style="--text-body:#1e293b;--text-primary:#0f172a;--text-secondary:#475569;--text-muted:#6b7280;--border-card:#e2e8f0;--border-accent:#94a3b8;--border-subtle:#e5e7eb;--bg-card-alt:#f8fafc;--accent:#dc2626;--accent-bg:rgba(220,38,38,0.06);">
${buildReportHtml(type)}
</body>
</html>`;
}

function downloadReport(type) {
  const html = buildStandaloneReportHtml(type);
  const slug = String(type).toLowerCase().replace(/[^a-z0-9]+/g, "-");
  const dateStr = new Date().toISOString().slice(0, 10);
  const blob = new Blob([html], { type: "text/html;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `agnirakshak-${slug}-${dateStr}.html`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  setTimeout(() => URL.revokeObjectURL(url), 3000);
}

function printReport(type) {
  // Prints the page with @media print rules (see style.css) that hide
  // all dashboard chrome and keep only the report preview visible.
  const preview = document.getElementById("reportPreview");
  if (preview && !preview.querySelector(".ar-report")) {
    preview.innerHTML = buildReportHtml(type);
    const btnPrint = document.getElementById("btnPrintReport");
    const btnDownload = document.getElementById("btnDownloadReport");
    if (btnPrint) btnPrint.disabled = false;
    if (btnDownload) btnDownload.disabled = false;
  }
  window.print();
}

document.addEventListener("DOMContentLoaded", () => {
  const btn = document.getElementById("btnGenerateReport");
  const btnPrint = document.getElementById("btnPrintReport");
  const btnDownload = document.getElementById("btnDownloadReport");
  const preview = document.getElementById("reportPreview");
  const typeEl = document.getElementById("reportType");

  function currentType() { return typeEl?.value || "Daily Report"; }

  function generateReport() {
    if (!preview) return;
    preview.innerHTML = buildReportHtml(currentType());
    if (btnPrint) btnPrint.disabled = false;
    if (btnDownload) btnDownload.disabled = false;
  }

  if (btn) btn.addEventListener("click", generateReport);
  if (typeEl) typeEl.addEventListener("change", generateReport);
  if (btnPrint) btnPrint.addEventListener("click", () => printReport(currentType()));
  if (btnDownload) btnDownload.addEventListener("click", () => downloadReport(currentType()));
});

// ============================================================
// NRT LIVE LAYER
// ============================================================

function initNrtLayer() {
  if (!map) return;
  nrtLayer = L.layerGroup();
  // Don't add to map by default — user toggles it on
}

function renderNrtLayer() {
  if (!nrtLayer || !map) return;
  nrtLayer.clearLayers();

  if (!nrtData.length) {
    console.log("No NRT data loaded.");
    return;
  }

  console.log("Rendering NRT detections:", nrtData.length);

  nrtData.forEach(det => {
    const lat = Number(det.latitude);
    const lon = Number(det.longitude);
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) return;

    const frp = Number(det.frp) || 0;
    const severity = String(det.nrt_severity || "normal");
    const sensor = det.sensor || det.nrt_source || "";
    const acqDate = det.acq_date || "";
    const confidence = Number(det.confidence) || 0;
    const gridId = det.grid_id || "";

    // --- BIGGER markers + pulsing outer ring for visibility ---
    let color, innerColor, radius, weight;
    if (severity === "critical") {
      color = "#ff2d2d"; innerColor = "#ff5555"; radius = 14; weight = 3;
    } else if (severity === "high") {
      color = "#ff6b1a"; innerColor = "#ff8c42"; radius = 12; weight = 2;
    } else if (severity === "elevated") {
      color = "#ffae42"; innerColor = "#ffc766"; radius = 10; weight = 2;
    } else {
      color = "#ff493d"; innerColor = "#ff7070"; radius = 9; weight = 1;
    }

    // Outer pulsing ring (larger, semi-transparent)
    const ring = L.circleMarker([lat, lon], {
      radius: radius + 6,
      color: color,
      weight: 1.5,
      fillColor: color,
      fillOpacity: 0.12,
      className: "nrt-ring-pulse",
      interactive: false,
    });
    nrtLayer.addLayer(ring);

    // Inner solid marker (clickable)
    const marker = L.circleMarker([lat, lon], {
      radius,
      color: color,
      weight,
      fillColor: innerColor,
      fillOpacity: 0.75,
      className: "nrt-pulse-marker",
    });

    // --- LIVE badge icon via divIcon ---
    const liveIcon = L.divIcon({
      className: "nrt-live-badge-icon",
      html: `<span class="nrt-live-badge">LIVE</span>`,
      iconSize: [36, 16],
      iconAnchor: [18, -radius - 4],
    });
    const liveMarker = L.marker([lat, lon], { icon: liveIcon, interactive: false });
    nrtLayer.addLayer(liveMarker);

    // --- Fire type from NRT data ---
    const fireType = normalizeFireType(det.fire_type);
    const fireTypeLabel = FIRE_TYPE_LABELS[fireType] || det.fire_type || "";
    const fireTypeColor = FIRE_TYPE_COLORS[fireType] || "#7890a8";

    // --- Interactive popup with grid link ---
    marker.bindPopup(`
      <div style="min-width:230px;font-family:Arial,sans-serif;line-height:1.6;">
        <div style="display:flex;align-items:center;gap:6px;margin-bottom:4px;">
          <span style="display:inline-block;padding:2px 7px;border-radius:3px;font-size:9px;font-weight:700;color:#fff;background:${color};letter-spacing:0.5px;">LIVE</span>
          <b style="color:${color};">NRT Detection</b>
        </div>
        <hr style="margin:4px 0;border-color:#2a3a4a;">
        <b>FRP:</b> <span style="font-size:14px;color:${color};">${frp.toFixed(1)} MW</span><br>
        <b>Severity:</b> ${severity.toUpperCase()}<br>
        ${fireTypeLabel ? `<b>Fire Type:</b> <span style="color:${fireTypeColor};">${fireTypeLabel}</span><br>` : ""}
        <b>Sensor:</b> ${sensor}<br>
        <b>Confidence:</b> ${confidence}<br>
        <b>Time:</b> ${acqDate}<br>
        <b>Coords:</b> ${lat.toFixed(5)}, ${lon.toFixed(5)}<br>
        ${gridId ? `<b>Grid:</b> <code style="background:#1a2533;padding:1px 5px;border-radius:3px;">${gridId}</code><br>` : ""}
        <hr style="margin:4px 0;border-color:#2a3a4a;">
        <span style="color:#94a6b8;font-size:10px;">Click to zoom &middot; Hover for quick info</span>
      </div>
    `);

    // --- Click: fly to detection + highlight ---
    marker.on("click", () => {
      map.flyTo([lat, lon], 13, { animate: true, duration: 0.8 });
      showNrtIntel(det);
      selectFireForChat(det);
    });

    // --- Tooltip on hover ---
    const ttFireType = fireTypeLabel ? ` &middot; ${fireTypeLabel}` : "";
    marker.bindTooltip(
      `<b>LIVE</b> &middot; ${frp.toFixed(0)} MW &middot; ${severity.toUpperCase()}${ttFireType} &middot; ${sensor}`,
      { direction: "top", offset: [0, -radius - 8], className: "nrt-tooltip" }
    );

    nrtLayer.addLayer(marker);
  });

  if (!map.hasLayer(nrtLayer)) {
    const nrtToggle = document.getElementById("lyrNrt");
    if (nrtToggle && nrtToggle.checked) {
      nrtLayer.addTo(map);
    }
  }
}

function toggleNrtLayer() {
  if (!map || !nrtLayer) return;
  const nrtToggle = document.getElementById("lyrNrt");
  if (!nrtToggle) return;

  if (nrtToggle.checked) {
    nrtLayer.addTo(map);
  } else {
    map.removeLayer(nrtLayer);
  }
}

// ============================================================
// NRT FETCH BUTTON (inside sidebar Live NRT Monitor)
// ============================================================

function initNrtFetchButton() {
  const btn = document.getElementById("btnFetchNrt");
  const status = document.getElementById("nrtFetchStatus");
  if (!btn) return;

  btn.addEventListener("click", () => {
    btn.classList.add("fetching");
    btn.textContent = "⏳ Updating...";
    if (status) {
      status.style.display = "block";
      status.textContent = "Fetching recent FIRMS data, updating grids & alerts...";
      status.style.color = "#ffae42";
    }

    // Trigger auto_update.py via Streamlit query param
    // This fetches new data, updates historical, recomputes grids, and refreshes
    try {
      var url = new URL(window.parent.location.href);
      url.searchParams.set('refresh', '1');
      window.parent.location.href = url.toString();
    } catch(e) {
      // Fallback: simple reload
      window.parent.location.reload();
    }
  });
}

// ============================================================
// NRT INTEL PANEL (right sidebar)
// ============================================================

function showNrtIntel(det) {
  const el = document.getElementById("selectedGrid");
  if (!el) return;

  const frp = Number(det.frp) || 0;
  const severity = String(det.nrt_severity || "normal").toUpperCase();
  const sensor = det.sensor || det.nrt_source || "";
  const acqDate = det.acq_date || "";
  const confidence = Number(det.confidence) || 0;
  const gridId = det.grid_id || "";
  const lat = Number(det.latitude);
  const lon = Number(det.longitude);
  const ageHrs = Number(det.age_hours);
  const ageStr = Number.isFinite(ageHrs) ? `${ageHrs.toFixed(1)}h ago` : "";

  const sevColors = { CRITICAL: "#ff2d2d", HIGH: "#ff6b1a", ELEVATED: "#ffae42", NORMAL: "#ff493d" };
  const sevColor = sevColors[severity] || "#ff493d";

  // Fire type classification
  const ft = normalizeFireType(det.fire_type);
  const ftLabel = FIRE_TYPE_LABELS[ft] || det.fire_type || "";
  const ftColor = FIRE_TYPE_COLORS[ft] || "#7890a8";
  const ftConfidence = Number(det.fire_type_confidence) || 0;
  const ftReason = det.fire_type_reason || "";

  // Reverse geocode for location info
  const geo = reverseGeocode(lat, lon);

  el.innerHTML = `
    <div style="display:flex;align-items:center;gap:6px;margin-bottom:6px;">
      <span class="nrt-live-badge" style="font-size:11px;">LIVE</span>
      <div class="grid-id" style="font-size:15px;">NRT Detection</div>
    </div>
    ${geo && geo.state !== "Unknown" ? `<div style="background:rgba(34,211,238,0.08);border:1px solid rgba(34,211,238,0.2);border-radius:6px;padding:6px 8px;margin-bottom:6px;font-size:11px;">
      🗺️ <strong>${geo.state}</strong>${geo.nearestCity ? ` · 🏙️ ${geo.nearestCity}${geo.withinCity ? "" : ` (${geo.distanceToCityKm} km)`}` : ""}
    </div>` : ""}
    <div class="risk-label" style="border-color:${sevColor};color:${sevColor};font-size:13px;">
      ${severity} SEVERITY
    </div>
    ${ftLabel ? `<div class="type-label" style="border:1px solid ${ftColor};color:${ftColor};font-size:12px;margin:6px 0;">
      🔥 ${ftLabel}${ftConfidence > 0 ? ` · ${Math.round(ftConfidence * 100)}%` : ""}
    </div>` : ""}
    <div class="intel-row"><span>FRP</span><strong style="font-size:16px;color:${sevColor};">${frp.toFixed(1)} MW</strong></div>
    <div class="intel-row"><span>Sensor</span><strong>${sensor}</strong></div>
    <div class="intel-row"><span>Confidence</span><strong>${confidence}</strong></div>
    <div class="intel-row"><span>Time</span><strong>${acqDate}</strong></div>
    ${ageStr ? `<div class="intel-row"><span>Age</span><strong>${ageStr}</strong></div>` : ""}
    <div class="intel-row"><span>Latitude</span><strong>${lat.toFixed(6)}</strong></div>
    <div class="intel-row"><span>Longitude</span><strong>${lon.toFixed(6)}</strong></div>
    ${gridId ? `<div class="intel-row"><span>Grid Cell</span><strong style="font-family:monospace;font-size:11px;">${gridId}</strong></div>` : ""}
    ${ftReason ? `<div class="intel-reason" style="margin-top:8px;">${ftReason}</div>` : ""}
    <button class="sat-evidence-btn" onclick="showSatelliteEvidence(${lat},${lon},'NRT Detection')">🛰️ Satellite Evidence</button>
    <div id="satEvidenceDateInfo" style="font-size:9px;color:#64748b;margin-top:5px;text-align:center;"></div>
  `;
}

// ============================================================
// NRT AUTO-REFRESH
// ============================================================
// In Streamlit mode the data is baked into the page.
// This timer triggers a page reload to pick up fresh data
// from a cron-triggered fetch_nrt.py + alert_engine.py run.
// ============================================================

function startNrtAutoRefresh() {
  if (nrtAutoRefreshTimer) clearInterval(nrtAutoRefreshTimer);
  nrtAutoRefreshTimer = setInterval(() => {
    console.log("[NRT] Auto-refresh: reloading dashboard data...");
    // In Streamlit mode, trigger a rerun via Streamlit's
    // component message. In standalone mode, just reload.
    if (window.THERMOSCOPE_DATA) {
      window.parent.postMessage({ type: "streamlit:rerun" }, "*");
    }
  }, NRT_AUTO_REFRESH_MS);
  console.log(`[NRT] Auto-refresh every ${NRT_AUTO_REFRESH_MS / 1000}s`);
}

function stopNrtAutoRefresh() {
  if (nrtAutoRefreshTimer) {
    clearInterval(nrtAutoRefreshTimer);
    nrtAutoRefreshTimer = null;
  }
}

// ============================================================
// NRT STATUS READOUT
// ============================================================

function updateNrtReadout() {
  const el = document.getElementById("nrtReadout");
  if (!el) return;
  const count = nrtData.length;
  if (count === 0) {
    el.innerHTML = `<span style="color:#64748b;">No NRT data yet — run fetch_nrt.py</span>`;
  } else {
    const ts = window.THERMOSCOPE_DATA?.nrtTimestamp || "";
    el.innerHTML = `<span style="color:#ff6b5e;">● ${count.toLocaleString("en-IN")} live detections</span>${ts ? ` · fetched ${ts}` : ""}`;
  }
}

// ============================================================
// ALERT BADGE IN NAV
// ============================================================

function updateAlertBadge() {
  const badge = document.getElementById("alertBadge");
  const alertsTab = document.querySelector(".nav-tab[data-tab='alerts']");
  if (!badge || !alertsTab) return;

  const count = alertsData.length;
  if (count > 0) {
    badge.textContent = count > 99 ? "99+" : count;
    badge.style.display = "inline-flex";
  } else {
    badge.style.display = "none";
  }
}

// ============================================================
// XAI CHATBOT — FIRE KNOWLEDGE BASE
// ============================================================

const FIRE_KNOWLEDGE = {
  INDUSTRIAL_PERSISTENT: {
    emoji: "🏭",
    label: "Industrial / Persistent Source",
    severity: "HIGH",
    seasonPeak: "Year-round (continuous)",
    legalFramework: [
      "Environment Protection Act 1986, Section 5",
      "Air (Prevention & Control of Pollution) Act 1981",
      "Factories Act 1948, Section 41A (Safety Officers)",
      "CPCB Emission Standards for Thermal Power Plants",
      "MoEFCC Coastal Regulation Zone norms"
    ],
    causes: [
      "Continuous thermal emissions from factories, refineries, or power plants",
      "Flaring of waste gas at petrochemical facilities",
      "Coke oven operations in steel plants",
      "Uncontrolled emissions from brick kilns",
      "Spontaneous combustion in coal stockpiles",
      "Leakage in chemical storage causing spontaneous ignition",
      "Electrical short circuits in industrial complexes"
    ],
    precautions: [
      "Maintain safe buffer zone (500m+) around industrial thermal sources",
      "Install continuous emissions monitoring systems (CEMS)",
      "Regular inspection of flaring and venting equipment",
      "Firebreak maintenance around coal storage areas",
      "Real-time thermal anomaly alerting for plant operators",
      "Automatic fire suppression systems in high-risk zones",
      "Emergency shutdown protocols for chemical processes"
    ],
    actions: [
      "Report to State Pollution Control Board (SPCB) for emission violations",
      "Invoke CPCB National Air Quality Standards (NAAQS) compliance check",
      "Deploy CPCB regional team for on-site inspection",
      "Cross-reference with CPCB Continuous Ambient Air Quality Monitoring data",
      "File complaint on CPCB CPGRAMS portal if repeated violations",
      "Notify District Disaster Management Authority (DDMA)",
      "Activate Industrial Emergency Response Plan"
    ],
    agencies: ["CPCB / SPCB", "MoEFCC", "Factory Inspectorate", "NDMA", "District Administration", "National Disaster Response Force (NDRF)", "Industrial Safety Department"],
    impact: "Persistent industrial thermal emissions degrade local air quality (PM2.5, SO2, NOx), cause respiratory health issues in nearby communities, and indicate potential regulatory non-compliance. Can escalate to major industrial disasters if uncontrolled.",
    emergencyProtocol: {
      immediate: ["Evacuate 1km radius", "Activate industrial siren", "Call Fire Brigade + NDRF", "Shut down adjacent chemical processes"],
      shortTerm: ["Air quality monitoring every 15 min", "Health screening camps for affected population", "CPCB emergency assessment team deployment"],
      longTerm: ["Mandatory CEMS installation", "Revised Environmental Impact Assessment", "Community health surveillance program"]
    }
  },
  AGRICULTURAL_BURNING: {
    emoji: "🌾",
    label: "Agricultural Burning",
    severity: "MEDIUM-HIGH",
    seasonPeak: "Oct-Nov (stubble), Apr-May (pre-monsoon clearing)",
    legalFramework: [
      "National Green Tribunal (NGT) Order 2015 on stubble burning",
      "Section 188 IPC — Disobedience of public servant order",
      "Disaster Management Act 2005, Section 51-60",
      "Punjab Preservation of Subsoil Water Act 2009",
      "Commission for Air Quality Management (CAQM) Ordinance 2020"
    ],
    causes: [
      "Post-harvest stubble burning (rice wheat cycle in Punjab/Haryana/UP)",
      "Land clearing before next cropping season",
      "Lack of affordable crop residue management machinery",
      "Traditional farming practices and time pressure",
      "Economics — burning is cheapest option vs. happy seeder rental",
      "Zero tolerance window too short between harvest and sowing"
    ],
    precautions: [
      "Use Happy Seeder / Super SMS machinery for in-situ crop residue management",
      "Create community-level crop residue banks for shared equipment",
      "Establish village-level monitoring committees",
      "Indoor air purifiers for vulnerable populations during burning season",
      "Schedule burning in controlled, low-wind conditions if unavoidable",
      "Bio-decomposer spray (Pusa decomposer) to decompose stubble in-field"
    ],
    actions: [
      "Alert District Magistrate and sub-divisional magistrate immediately",
      "File FIR under Section 188 IPC / Disaster Management Act 2005",
      "Report to Punjab/Haryana/UP Pollution Control Board",
      "Invoke National Green Tribunal (NGT) directives on stubble burning",
      "Activate GRAP (Graded Response Action Plan) if in NCR region",
      "Impose financial penalty as per CAQM guidelines (₹5,000-25,000)",
      "Deploy drone surveillance for real-time monitoring"
    ],
    agencies: ["District Agriculture Office", "SPCB", "NGT", "District Magistrate", "NDRF (if escalated)", "CAQM (Commission for Air Quality Management)", "ISRO / NRSC for satellite monitoring"],
    impact: "Stubble burning contributes ~25-30% of Delhi NCR winter air pollution (AQI crosses 500 'severe'), causes severe respiratory illness (30% increase in hospital admissions), reduces visibility to <100m on highways, violates NGT orders, and wastes potential bio-fuel/compost resource.",
    emergencyProtocol: {
      immediate: ["Alert local fire brigade", "Issue public health advisory (N95 masks, stay indoors)", "Deploy water tankers for dust suppression", "Activate anti-smog guns in NCR"],
      shortTerm: ["GRAP Stage III/IV implementation", "School closure advisory if AQI > 400", "Free health camps in affected villages", "Satellite-based daily hotspot monitoring"],
      longTerm: ["Happy Seeder subsidy increase to 80%", "CPCB-mandated crop residue management plan", "In-situ decomposition research funding", "Inter-state coordination for transboundary pollution"]
    }
  },
  FOREST_WILDFIRE: {
    emoji: "🌲",
    label: "Forest / Wildfire",
    severity: "HIGH-CRITICAL",
    seasonPeak: "Mar-Jun (pre-monsoon dry season)",
    legalFramework: [
      "Indian Forest Act 1927, Section 26 (forest fire offense)",
      "Forest (Conservation) Act 1980",
      "Wildlife Protection Act 1972 (for protected areas)",
      "National Disaster Management Act 2005",
      "NDMA Guidelines on Forest Fires 2019"
    ],
    causes: [
      "Dry season lightning strikes in forest areas",
      "Abandoned campfires and cigarettes by trekkers",
      "Deliberate setting for land encroachment",
      "Extreme heat events and drought conditions",
      "Forest floor accumulation of dry leaf litter and deadwood",
      "Shifting cultivation (jhum) escaped control",
      "Forest product collection (tendu, resin) causing ignition"
    ],
    precautions: [
      "Maintain fire lines (cleared strips) in forest divisions",
      "Deploy fire watch towers with thermal cameras in high-risk zones",
      "Community-based fire management training for forest fringe villages",
      "Seasonal bans on forest entry during peak fire months (Mar-Jun)",
      "Pre-position fire fighting equipment at forest beat offices",
      "Satellite-based early warning system (FIRMS NRT integration)",
      "Insurance coverage for forest fringe communities"
    ],
    actions: [
      "Alert State Forest Department and DFO (Divisional Forest Officer) immediately",
      "Activate NDRF/SDRF if fire threatens human settlements",
      "Implement NDMA wildfire response protocol",
      "Evacuate forest fringe villages if fire front approaches",
      "Aerial fire suppression via helicopter/air tanker if available",
      "Create firebreak by controlled back-burning ahead of fire front",
      "Coordinate with ITBP/Army for large-scale firefighting"
    ],
    agencies: ["State Forest Department", "NDRF / SDRF", "NDMA", "ITBP / Army (if needed)", "District Disaster Management Authority", "Wildlife Institute of India", "Forest Survey of India (FSI)"],
    impact: "Forest fires destroy biodiversity (India lost 35,000+ hectares in 2023), release massive CO2 and PM2.5, cause soil erosion and watershed damage, threaten wildlife habitats, can spread to human settlements, and cost ₹100+ crore in suppression annually.",
    emergencyProtocol: {
      immediate: ["Activate forest fire control room", "Deploy fire beat guards + community volunteers", "Evacuate settlements within 2km of fire front", "Request Indian Air Force helicopter support if >50ha"],
      shortTerm: ["Establish base camps near fire line", "Coordinate with neighboring forest divisions", "Health monitoring for firefighters (smoke inhalation)", "Wildlife rescue operations for affected areas"],
      longTerm: ["Post-fire reforestation program", "Community forest fire management plans", "Satellite-based fire risk mapping (FSI)", "Fire-resistant species plantation in fire-prone zones"]
    }
  },
  MINING: {
    emoji: "⛏️",
    label: "Mining Activity",
    severity: "HIGH",
    seasonPeak: "Year-round (peak in dry months)",
    legalFramework: [
      "Mines and Minerals (Development & Regulation) Act 1957",
      "Coal Mines Regulations 2017 (CMR 2017)",
      "Mines Act 1952, Section 39 (fire precautions)",
      "DGMS Circular on Mine Fires",
      "Environment Protection Act 1986"
    ],
    causes: [
      "Spontaneous combustion in coal seams (underground mines)",
      "Blasting operations in open-cast mines",
      "Methane gas ignition in coal mines",
      "Dumping of overburden with residual coal content",
      "Equipment fires in mining operations",
      "Electrical faults in mine infrastructure"
    ],
    precautions: [
      "Deploy methane drainage systems in underground coal mines",
      "Regular fire safety audits per Coal Mines Regulations 2017",
      "Install real-time gas monitoring and thermal sensors",
      "Maintain fire suppression infrastructure at pit mouths",
      "Segregate overburden dumps to prevent spontaneous combustion",
      "Nitrogen injection to inert goaf areas",
      "Mandatory firefighting drills quarterly"
    ],
    actions: [
      "Alert DGMS (Directorate General of Mines Safety) immediately",
      "Invoke Coal India safety protocols for mine fire response",
      "Evacuate miners and activate mine rescue teams",
      "Report to SPCB for environmental violation",
      "Emergency closure of affected mine sections per CMR 2017",
      "Deploy mine rescue station teams (SDMF)",
      "Environmental impact assessment of mine fire emissions"
    ],
    agencies: ["DGMS", "Coal India / State Mining Corp", "SPCB", "NDMA", "District Administration", "Mine Rescue Station", "Central Mine Planning & Design Institute (CMPDI)"],
    impact: "Mine fires cause land subsidence (affecting surface structures), release toxic gases (CO, SO2, H2S), contaminate groundwater rendering it unusable, render land unusable for decades, pose fatal risks to miners, and cause massive economic loss to mining companies.",
    emergencyProtocol: {
      immediate: ["Immediate mine evacuation (all personnel)", "Activate mine rescue team", "Seal affected section with sand/clay", "Gas monitoring at all access points"],
      shortTerm: ["Continuous atmospheric monitoring", "Water injection to cool fire zone", "DGMS investigation team deployment", "Worker health screening"],
      longTerm: ["Mine fire remediation plan (inert gas injection)", "Surface subsidence monitoring", "Groundwater contamination remediation", "Mine closure/rehabilitation plan if unresolvable"]
    }
  },
  UNCLASSIFIED: {
    emoji: "❓",
    label: "Unclassified Fire",
    severity: "UNKNOWN",
    seasonPeak: "Unknown",
    legalFramework: ["District Disaster Management Plan", "Disaster Management Act 2005"],
    causes: [
      "Insufficient historical data for pattern classification",
      "Mixed land use with multiple fire sources",
      "One-time or sporadic thermal event",
      "Seasonal or weather-related fire",
      "Possible data quality issue in satellite detection"
    ],
    precautions: [
      "Conduct ground-truth verification of satellite detection",
      "Cross-reference with local administration reports",
      "Monitor for recurring patterns over next 30 days",
      "Check nearby land use for potential fire sources",
      "Verify with multiple satellite sources for confirmation"
    ],
    actions: [
      "Report to District Disaster Management Office for investigation",
      "Deploy field team for ground-truth verification",
      "Monitor next 48 hours for repeat detections",
      "Cross-reference with local fire brigade incident reports",
      "Reclassify after gathering additional ground data"
    ],
    agencies: ["District Administration", "Local Fire Brigade", "SPCB", "Remote Sensing Centre", "SDRF"],
    impact: "Unverified thermal detections may represent emerging fire risks or data artifacts. Ground truthing is essential to determine actual risk level and appropriate response.",
    emergencyProtocol: {
      immediate: ["Alert district control room", "Dispatch reconnaissance team", "Activate satellite monitoring for 48 hours"],
      shortTerm: ["Ground verification within 24 hours", "Cross-check with local fire incident records"],
      longTerm: ["Update classification model with new data", "Add to monitoring watchlist"]
    }
  }
};

// ============================================================
// XAI CHATBOT — FEATURE IMPORTANCE ENGINE (ENHANCED)
// ============================================================

function computeXAI(fireData) {
  const features = [];

  // Land Cover
  const lc = String(fireData.landcover_class || "").toLowerCase();
  let lcScore = 20;
  let lcReason = "Unknown land cover";
  if (lc.includes("built") || lc.includes("urban") || lc.includes("industrial")) {
    lcScore = 85; lcReason = "Built-up/urban area → industrial indicator";
  } else if (lc.includes("crop") || lc.includes("grass") || lc.includes("agri")) {
    lcScore = 75; lcReason = "Cropland/grassland → agricultural indicator";
  } else if (lc.includes("tree") || lc.includes("forest")) {
    lcScore = 70; lcReason = "Tree cover/forest → wildfire indicator";
  } else if (lc.includes("bare") || lc.includes("rock")) {
    lcScore = 40; lcReason = "Bare ground → possible mining or controlled burn";
  } else if (lc.includes("water")) {
    lcScore = 10; lcReason = "Near water body → low fire association";
  }
  features.push({ name: "Land Cover", score: lcScore, color: "#22d3ee", reason: lcReason });

  // Recurrence
  const rec = Number(fireData.recurrence_ratio) || 0;
  features.push({ name: "Recurrence", score: Math.round(rec * 100), color: "#a855f7", reason: `Heat recurs ${(rec * 100).toFixed(0)}% of observation days` });

  // FRP Intensity
  const avgFrp = Number(fireData.avg_frp) || 0;
  const maxFrp = Number(fireData.max_frp) || 1;
  const frpScore = Math.min(100, Math.round((avgFrp / Math.max(maxFrp, 1)) * 100));
  features.push({ name: "FRP Intensity", score: frpScore, color: "#ff382f", reason: `Avg FRP ${avgFrp.toFixed(1)} MW (max observed: ${maxFrp.toFixed(1)} MW)` });

  // Persistence
  const persMonths = Number(fireData.persistent_months) || 0;
  const persScore = Math.min(100, Math.round((persMonths / 12) * 100));
  features.push({ name: "Persistence", score: persScore, color: "#ff6b1a", reason: `Active across ${persMonths} months` });

  // Multi-satellite
  const multiSat = Number(fireData.multi_satellite_activity) || 0;
  const msScore = multiSat ? 80 : 15;
  features.push({ name: "Multi-Satellite", score: msScore, color: "#20e889", reason: multiSat ? "Confirmed by multiple VIIRS sensors" : "Single satellite detection" });

  // Proximity to facility
  const dist = Number(fireData.named_facility_distance_km);
  let proxScore = 30;
  let proxReason = "No facility proximity data";
  if (Number.isFinite(dist)) {
    proxScore = dist <= 1 ? 95 : dist <= 3 ? 80 : dist <= 5 ? 60 : dist <= 10 ? 40 : 20;
    proxReason = `${dist.toFixed(1)} km from named facility`;
  }
  features.push({ name: "Proximity", score: proxScore, color: "#ffd400", reason: proxReason });

  return features;
}

function computeOverallSeverity(fireData, features) {
  // Weighted composite severity score 0-100
  const weights = { "Land Cover": 0.20, "Recurrence": 0.20, "FRP Intensity": 0.25, "Persistence": 0.15, "Multi-Satellite": 0.10, "Proximity": 0.10 };
  let score = 0;
  features.forEach(f => { score += (f.score || 0) * (weights[f.name] || 0.1); });
  return Math.round(score);
}

function getSeverityLabel(score) {
  if (score >= 80) return { label: "CRITICAL", color: "#ff382f", emoji: "🔴" };
  if (score >= 60) return { label: "HIGH", color: "#ff6b1a", emoji: "🟠" };
  if (score >= 40) return { label: "MODERATE", color: "#ffae42", emoji: "🟡" };
  return { label: "LOW", color: "#20e889", emoji: "🟢" };
}

function renderXAIChart(features) {
  let html = '<div style="margin:8px 0;">';
  features.forEach(f => {
    html += `<div class="chat-xai-bar">
      <span class="chat-xai-label">${f.name}</span>
      <div class="chat-xai-track"><div class="chat-xai-fill" style="width:${f.score}%;background:${f.color};"></div></div>
      <span class="chat-xai-pct">${f.score}%</span>
    </div>`;
  });
  html += '</div>';
  return html;
}

// ============================================================
// XAI CHATBOT — SEASONAL CONTEXT
// ============================================================

function getSeasonalContext() {
  const now = new Date();
  const month = now.getMonth() + 1;
  const contexts = [];
  if (month >= 10 || month <= 11) contexts.push("🌾 Post-harvest stubble burning season — high agricultural fire risk in Punjab/Haryana/UP");
  if (month >= 3 && month <= 6) contexts.push("🔥 Pre-monsoon dry season — peak forest fire risk across Himalayan and Central Indian forests");
  if (month >= 11 || month <= 2) contexts.push("🌫️ Winter inversion — pollutants trapped near ground, industrial emissions more impactful");
  if (month >= 6 && month <= 9) contexts.push("🌧️ Monsoon season — reduced fire risk, but lightning-caused forest fires possible");
  if (contexts.length === 0) contexts.push("📅 Transitional season — moderate fire risk across all categories");
  return contexts;
}

// ============================================================
// XAI CHATBOT — ALERT CONTEXT
// ============================================================

function getAlertContext(gridId) {
  if (!alertsData || !alertsData.length) return null;
  const matching = alertsData.filter(a => String(a.grid_id) === String(gridId));
  return matching.length ? matching : null;
}

function getActiveAlertCount() {
  if (!alertsData) return 0;
  return alertsData.filter(a => String(a.status).toUpperCase() === "ACTIVE").length;
}

// ============================================================
// XAI CHATBOT — GEMINI API (ENHANCED)
// ============================================================

const GEMINI_MODEL = "gemini-2.0-flash";
const GEMINI_ENDPOINT = `https://generativelanguage.googleapis.com/v1beta/models/${GEMINI_MODEL}:generateContent`;
const GEMINI_SYSTEM = `You are AgniRakshak AI, an expert in fire risk analysis, satellite-based thermal monitoring, and Indian disaster management.
You MUST respond in the SAME LANGUAGE the user writes in. If the user writes in Hinglish (Hindi written in English script like "ye kya hai", "batao", "kisko risk hai"), respond in Hinglish. If they write in pure Hindi (Devanagari), respond in Hindi. If English, respond in English.
Analyze the provided fire data and give clear, actionable explanations.
Reference NDMA guidelines, NDRF protocols, and CPCB standards where applicable.
Be concise but thorough. Use bullet points and emojis for readability.
Always include: severity assessment, key risk factors, immediate actions, responsible agencies, and long-term recommendations.
When comparing fires, use the statistical data provided. When discussing trends, calculate growth rate from the detection counts.
You can answer general questions about fire safety, climate, geography of India, disaster management, and any topic related to your expertise. Be helpful and conversational.`;

// ============================================================
// XAI CHATBOT — LANGUAGE DETECTION
// ============================================================

function detectLanguage(query) {
  const q = query.toLowerCase();
  // Hindi/Devanagari characters
  if (/[ऀ-ॿ]/.test(query)) return "hindi";
  // Hinglish patterns
  const hinglishWords = ["kya", "hai", "hain", "ka", "ki", "ke", "ko", "se", "me", "mein", "ye", "wo", "yeh", "woh", "aur", "ya", "par", "pe", "nahi", "nhi", "bhi", "jo", "jo", "tum", "aap", "hum", "mai", "mera", "tera", "uska", "batao", "bata", "bolo", "sunao", "dekhlo", "kisko", "kis", "konsa", "kaise", "kyun", "kyu", "abhi", "yaha", "waha", "idhar", "udhar", "jaise", "waise", "tab", "phir", "toh", "tha", "thi", "hoga", "hogi", "karega", "karegi", "chahiye", "sakte", "ho sakta", "sakta", "sakti", "wala", "wali", "wale", "gaya", "gai", "diya", "liya", "karo", "karna", "karne", "bolte", "bol", "samajh", "samjho"];
  const hinglishCount = hinglishWords.filter(w => q.includes(w)).length;
  if (hinglishCount >= 2) return "hinglish";
  // Common Hinglish question patterns
  if (/\b(kya|kaun|kiska|kaise|kyun|kyu|kitna|kab|kaha|kahan)\b/.test(q)) return "hinglish";
  return "english";
}

// ============================================================
// XAI CHATBOT — GEOGRAPHIC KNOWLEDGE BASE
// ============================================================

const GEO_KNOWLEDGE = {
  states: {
    "up": { name: "Uttar Pradesh", full: "Uttar Pradesh", capitals: ["Lucknow"], majorDistricts: ["Lucknow", "Kanpur", "Agra", "Varanasi", "Meerut", "Prayagraj", "Bareilly", "Jhansi", "Gorakhpur", "Noida", "Ghaziabad"], fireNote: "UP has high agricultural burning (Oct-Nov) and industrial thermal activity near Kanpur, Varanasi belt." },
    "uttar pradesh": { name: "Uttar Pradesh", full: "Uttar Pradesh", capitals: ["Lucknow"], majorDistricts: ["Lucknow", "Kanpur", "Agra", "Varanasi", "Meerut"], fireNote: "UP has high agricultural burning (Oct-Nov) and industrial thermal activity near Kanpur, Varanasi belt." },
    "delhi": { name: "Delhi", full: "National Capital Territory of Delhi", capitals: ["New Delhi"], majorDistricts: ["New Delhi", "Central Delhi", "South Delhi", "North Delhi", "East Delhi", "West Delhi"], fireNote: "Delhi NCR receives transboundary pollution from stubble burning in Punjab/Haryana. Industrial hotspots in outer Delhi." },
    "ncr": { name: "Delhi NCR", full: "National Capital Region", capitals: ["New Delhi"], majorDistricts: ["Gurugram", "Noida", "Ghaziabad", "Faridabad", "Sonipat"], fireNote: "NCR is most affected by stubble burning. GRAP (Graded Response Action Plan) activates when AQI crosses 300+." },
    "haryana": { name: "Haryana", full: "Haryana", capitals: ["Chandigarh"], majorDistricts: ["Gurugram", "Faridabad", "Sonipat", "Panipat", "Hisar", "Karnal"], fireNote: "Major stubble burning state (Oct-Nov). Industrial emissions from Panipat refinery, Hisar sugar mills." },
    "punjab": { name: "Punjab", full: "Punjab", capitals: ["Chandigarh"], majorDistricts: ["Ludhiana", "Amritsar", "Jalandhar", "Patiala", "Bathinda", "Ferozpur"], fireNote: "Highest stubble burning intensity in India (Oct-Nov). Rice-wheat cycle creates massive stubble problem." },
    "rajasthan": { name: "Rajasthan", full: "Rajasthan", capitals: ["Jaipur"], majorDistricts: ["Jaipur", "Jodhpur", "Kota", "Udaipur", "Ajmer", "Bikaner"], fireNote: "Forest fires in Aravalli range (Mar-Jun). Industrial thermal activity near Kota-Chittorgarh belt." },
    "mp": { name: "Madhya Pradesh", full: "Madhya Pradesh", capitals: ["Bhopal"], majorDistricts: ["Bhopal", "Indore", "Jabalpur", "Gwalior", "Ujjain"], fireNote: "Large forest fire zone in Satpura-Vindhyas. Coal mine fires in Singrauli belt." },
    "madhya pradesh": { name: "Madhya Pradesh", full: "Madhya Pradesh", capitals: ["Bhopal"], majorDistricts: ["Bhopal", "Indore", "Jabalpur", "Gwalior"], fireNote: "Large forest fire zone in Satpura-Vindhyas. Coal mine fires in Singrauli belt." },
    "jharkhand": { name: "Jharkhand", full: "Jharkhand", capitals: ["Ranchi"], majorDistricts: ["Ranchi", "Jamshedpur", "Dhanbad", "Bokaro", "Hazaribagh"], fireNote: "Major coal mining state. Jharia mine fires have burned for 100+ years. High industrial fire risk." },
    "bihar": { name: "Bihar", full: "Bihar", capitals: ["Patna"], majorDistricts: ["Patna", "Gaya", "Muzaffarpur", "Bhagalpur", "Munger"], fireNote: "Agricultural residue burning in Kosi region. Forest fires in Rajgir hills." },
    "uttarakhand": { name: "Uttarakhand", full: "Uttarakhand", capitals: ["Dehradun"], majorDistricts: ["Dehradun", "Haridwar", "Nainital", "Almora", "Chamoli"], fireNote: "Severe forest fires in Himalayan foothills (Mar-Jun). 2024 fires burned 1000+ hectares." },
    "uk": { name: "Uttarakhand", full: "Uttarakhand", capitals: ["Dehradun"], majorDistricts: ["Dehradun", "Haridwar", "Nainital"], fireNote: "Severe forest fires in Himalayan foothills (Mar-Jun)." },
    "himachal": { name: "Himachal Pradesh", full: "Himachal Pradesh", capitals: ["Shimla"], majorDistricts: ["Shimla", "Mandi", "Kullu", "Kangra", "Solan"], fireNote: "Forest fires in pine forests during dry season. Chir pine needles are highly flammable." },
    "himachal pradesh": { name: "Himachal Pradesh", full: "Himachal Pradesh", capitals: ["Shimla"], majorDistricts: ["Shimla", "Mandi", "Kullu"], fireNote: "Forest fires in pine forests during dry season." },
  },
  cities: {
    "delhi": "Delhi NCR — Major transboundary pollution from stubble burning. AQI crosses 500 in Nov.",
    "kanpur": "Kanpur, UP — Industrial hub with leather tanneries. High industrial thermal emissions.",
    "ludhiana": "Ludhiana, Punjab — Major industrial city + surrounded by agricultural burning zones.",
    "ranchi": "Ranchi, Jharkhand — Coal mining region. Jharia fires visible from space.",
    "jaipur": "Jaipur, Rajasthan — Industrial corridor. Forest fires in nearby Aravalli range.",
    "lucknow": "Lucknow, UP — Agricultural + urban fires. Near sugarcane belt.",
    "patna": "Patna, Bihar — Agricultural burning in surrounding districts.",
    "dehradun": "Dehradun, Uttarakhand — Gateway to Himalayan forest fire zone.",
    "bhopal": "Bhopal, MP — Near Satpura forest fires. Coal fires in nearby Singrauli.",
    "gurugram": "Gurugram, Haryana (NCR) — Industrial emissions + stubble burning impact.",
  },
  fireStats: {
    delhi_ncr_stubble: "Delhi NCR receives ~25-30% of its winter air pollution from stubble burning in Punjab/Haryana/UP.",
    forest_fire_india: "India loses ~35,000 hectares of forest annually to fires. Uttarakhand, MP, Chhattisgarh are worst affected.",
    coal_mine_fires: "Jharia coal mine fires in Jharkhand have been burning for 100+ years. 70+ fires active.",
    industrial_india: "India has 200+ critically polluted industrial clusters identified by CPCB.",
    satellite_coverage: "Thermoscope monitors North India using VIIRS satellites (S-NPP, NOAA-20, NOAA-21) with 375m resolution.",
  }
};

// ============================================================
// XAI CHATBOT — REVERSE GEOCODING (lat/lon → state, city)
// ============================================================

const STATE_BOUNDARIES = [
  // Small states checked FIRST (more precise bounding boxes)
  { state: "Delhi", latMin: 28.40, latMax: 28.88, lonMin: 76.83, lonMax: 77.34, cities: [
    { name: "New Delhi", lat: 28.61, lon: 77.21, radius: 0.15 },
    { name: "North Delhi", lat: 28.70, lon: 77.18, radius: 0.12 },
    { name: "South Delhi", lat: 28.52, lon: 77.20, radius: 0.12 },
    { name: "East Delhi", lat: 28.63, lon: 77.30, radius: 0.10 },
    { name: "West Delhi", lat: 28.63, lon: 77.10, radius: 0.10 },
    { name: "Central Delhi", lat: 28.64, lon: 77.22, radius: 0.08 },
  ]},
  // Haryana — ends at ~77.3 east (border with UP), south ~27.7
  { state: "Haryana", latMin: 27.7, latMax: 30.9, lonMin: 74.9, lonMax: 77.3, cities: [
    { name: "Gurugram", lat: 28.46, lon: 77.03, radius: 0.12 },
    { name: "Faridabad", lat: 28.41, lon: 77.32, radius: 0.10 },
    { name: "Sonipat", lat: 28.99, lon: 77.02, radius: 0.15 },
    { name: "Panipat", lat: 29.39, lon: 76.97, radius: 0.15 },
    { name: "Hisar", lat: 29.15, lon: 75.72, radius: 0.18 },
    { name: "Karnal", lat: 29.69, lon: 76.99, radius: 0.15 },
    { name: "Ambala", lat: 30.37, lon: 76.78, radius: 0.15 },
    { name: "Rewari", lat: 28.23, lon: 76.72, radius: 0.10 },
    { name: "Bhiwani", lat: 28.79, lon: 76.14, radius: 0.15 },
    { name: "Rohtak", lat: 28.90, lon: 76.58, radius: 0.12 },
  ]},
  // Punjab — narrow band 29.5-32.5 lat, 73.5-77.0 lon
  { state: "Punjab", latMin: 29.5, latMax: 32.5, lonMin: 73.5, lonMax: 77.0, cities: [
    { name: "Ludhiana", lat: 30.90, lon: 75.86, radius: 0.20 },
    { name: "Amritsar", lat: 31.63, lon: 74.87, radius: 0.20 },
    { name: "Jalandhar", lat: 31.33, lon: 75.58, radius: 0.18 },
    { name: "Patiala", lat: 30.34, lon: 76.39, radius: 0.15 },
    { name: "Bathinda", lat: 30.21, lon: 74.95, radius: 0.18 },
    { name: "Ferozpur", lat: 30.92, lon: 74.62, radius: 0.15 },
    { name: "Mohali", lat: 30.70, lon: 76.72, radius: 0.10 },
    { name: "Moga", lat: 30.81, lon: 75.17, radius: 0.12 },
    { name: "Sangrur", lat: 30.25, lon: 75.84, radius: 0.12 },
    { name: "Hoshiarpur", lat: 31.51, lon: 75.91, radius: 0.12 },
    { name: "Pathankot", lat: 32.27, lon: 75.65, radius: 0.12 },
    { name: "Gurdaspur", lat: 32.04, lon: 74.79, radius: 0.12 },
  ]},
  // Rajasthan — ends at ~76.5 east (border with UP/MP)
  { state: "Rajasthan", latMin: 23.3, latMax: 30.2, lonMin: 69.5, lonMax: 76.5, cities: [
    { name: "Jaipur", lat: 26.92, lon: 75.79, radius: 0.25 },
    { name: "Jodhpur", lat: 26.24, lon: 73.02, radius: 0.25 },
    { name: "Kota", lat: 25.18, lon: 75.86, radius: 0.20 },
    { name: "Udaipur", lat: 24.58, lon: 73.71, radius: 0.20 },
    { name: "Ajmer", lat: 26.45, lon: 74.64, radius: 0.18 },
    { name: "Bikaner", lat: 28.02, lon: 73.32, radius: 0.20 },
    { name: "Alwar", lat: 27.55, lon: 76.63, radius: 0.18 },
    { name: "Bharatpur", lat: 27.22, lon: 77.49, radius: 0.12 },
    { name: "Dholpur", lat: 26.70, lon: 77.90, radius: 0.12 },
    { name: "Sawai Madhopur", lat: 26.02, lon: 76.35, radius: 0.15 },
    { name: "Chittorgarh", lat: 24.88, lon: 74.62, radius: 0.15 },
    { name: "Baran", lat: 25.10, lon: 76.35, radius: 0.12 },
    { name: "Karauli", lat: 26.50, lon: 77.02, radius: 0.10 },
  ]},
  // Uttarakhand — northern hill state
  { state: "Uttarakhand", latMin: 28.4, latMax: 31.4, lonMin: 77.5, lonMax: 81.0, cities: [
    { name: "Dehradun", lat: 30.32, lon: 78.03, radius: 0.22 },
    { name: "Haridwar", lat: 29.95, lon: 78.16, radius: 0.18 },
    { name: "Nainital", lat: 29.38, lon: 79.45, radius: 0.18 },
    { name: "Haldwani", lat: 29.22, lon: 79.53, radius: 0.12 },
    { name: "Rishikesh", lat: 30.09, lon: 78.27, radius: 0.10 },
    { name: "Almora", lat: 29.60, lon: 79.66, radius: 0.12 },
    { name: "Pithoragarh", lat: 29.58, lon: 80.22, radius: 0.12 },
    { name: "Chamoli", lat: 30.40, lon: 79.33, radius: 0.12 },
  ]},
  // Himachal Pradesh — northern hill state
  { state: "Himachal Pradesh", latMin: 30.4, latMax: 33.2, lonMin: 75.8, lonMax: 79.0, cities: [
    { name: "Shimla", lat: 31.10, lon: 77.17, radius: 0.18 },
    { name: "Mandi", lat: 31.71, lon: 76.93, radius: 0.18 },
    { name: "Kullu", lat: 31.96, lon: 77.11, radius: 0.18 },
    { name: "Kangra", lat: 32.10, lon: 76.27, radius: 0.18 },
    { name: "Solan", lat: 30.91, lon: 77.10, radius: 0.10 },
    { name: "Hamirpur", lat: 31.68, lon: 76.53, radius: 0.10 },
  ]},
  // Jharkhand — checked before UP/MP to avoid overlap
  { state: "Jharkhand", latMin: 21.9, latMax: 24.7, lonMin: 83.3, lonMax: 87.9, cities: [
    { name: "Ranchi", lat: 23.35, lon: 85.33, radius: 0.22 },
    { name: "Jamshedpur", lat: 22.80, lon: 86.18, radius: 0.18 },
    { name: "Dhanbad", lat: 23.79, lon: 86.43, radius: 0.18 },
    { name: "Bokaro", lat: 23.67, lon: 86.15, radius: 0.15 },
    { name: "Hazaribagh", lat: 23.99, lon: 85.36, radius: 0.18 },
    { name: "Deoghar", lat: 24.48, lon: 86.70, radius: 0.12 },
    { name: "Gumla", lat: 23.07, lon: 84.54, radius: 0.12 },
    { name: "Lohardaga", lat: 23.43, lon: 84.68, radius: 0.10 },
  ]},
  // Bihar — checked before UP
  { state: "Bihar", latMin: 24.2, latMax: 27.5, lonMin: 83.2, lonMax: 88.2, cities: [
    { name: "Patna", lat: 25.61, lon: 85.14, radius: 0.25 },
    { name: "Gaya", lat: 24.79, lon: 85.00, radius: 0.18 },
    { name: "Muzaffarpur", lat: 26.12, lon: 85.39, radius: 0.18 },
    { name: "Bhagalpur", lat: 25.24, lon: 86.99, radius: 0.18 },
    { name: "Darbhanga", lat: 26.15, lon: 86.10, radius: 0.12 },
    { name: "Ara", lat: 25.55, lon: 84.67, radius: 0.10 },
    { name: "Munger", lat: 25.38, lon: 86.47, radius: 0.10 },
  ]},
  // Chhattisgarh — checked before MP, tight boundary to avoid capturing MP Singrauli region
  { state: "Chhattisgarh", latMin: 17.8, latMax: 23.9, lonMin: 80.3, lonMax: 84.0, cities: [
    { name: "Raipur", lat: 21.25, lon: 81.63, radius: 0.25 },
    { name: "Bilaspur", lat: 22.08, lon: 82.14, radius: 0.20 },
    { name: "Durg", lat: 21.19, lon: 81.28, radius: 0.15 },
    { name: "Korba", lat: 22.34, lon: 82.68, radius: 0.15 },
    { name: "Jagdalpur", lat: 19.09, lon: 82.00, radius: 0.12 },
    { name: "Ambikapur", lat: 23.12, lon: 83.20, radius: 0.12 },
  ]},
  // Madhya Pradesh — precise boundary to avoid UP overlap
  // West border ~74.0, East border ~82.7 (Singrauli at 82.68 is IN MP!)
  // North border varies: ~26.9 near Gwalior, ~23.5 near UP border
  // CRITICAL: MP extends to 82.7 east at Singrauli latitude (24.19)
  { state: "Madhya Pradesh", latMin: 21.1, latMax: 26.9, lonMin: 74.0, lonMax: 82.7, cities: [
    { name: "Bhopal", lat: 23.26, lon: 77.41, radius: 0.25 },
    { name: "Indore", lat: 22.72, lon: 75.86, radius: 0.25 },
    { name: "Jabalpur", lat: 23.18, lon: 79.95, radius: 0.22 },
    { name: "Gwalior", lat: 26.22, lon: 78.18, radius: 0.20 },
    { name: "Ujjain", lat: 23.18, lon: 75.79, radius: 0.18 },
    { name: "Singrauli", lat: 24.19, lon: 82.68, radius: 0.25 },
    { name: "Sagar", lat: 23.84, lon: 78.74, radius: 0.15 },
    { name: "Satna", lat: 24.60, lon: 80.83, radius: 0.15 },
    { name: "Rewa", lat: 24.53, lon: 81.30, radius: 0.15 },
    { name: "Katni", lat: 23.83, lon: 80.39, radius: 0.12 },
    { name: "Narsinghpur", lat: 22.92, lon: 79.19, radius: 0.12 },
    { name: "Balaghat", lat: 21.81, lon: 80.19, radius: 0.12 },
    { name: "Chhindwara", lat: 22.06, lon: 78.94, radius: 0.12 },
    { name: "Betul", lat: 21.83, lon: 77.93, radius: 0.12 },
    { name: "Harda", lat: 22.34, lon: 77.10, radius: 0.10 },
    { name: "Dewas", lat: 23.00, lon: 76.06, radius: 0.12 },
    { name: "Ratlam", lat: 23.32, lon: 75.04, radius: 0.12 },
    { name: "Jhabua", lat: 22.77, lon: 74.59, radius: 0.10 },
  ]},
  // Uttar Pradesh — PRECISE boundaries, excluded Singrauli/MP region
  // South border: ~24.5 (above MP), East: up to ~84.3 (Gorakhpur)
  // West: starts ~77.3 (after Haryana), North: ~30.5
  { state: "Uttar Pradesh", latMin: 24.5, latMax: 30.5, lonMin: 77.3, lonMax: 84.3, cities: [
    { name: "Lucknow", lat: 26.85, lon: 80.95, radius: 0.30 },
    { name: "Kanpur", lat: 26.45, lon: 80.35, radius: 0.25 },
    { name: "Agra", lat: 27.18, lon: 78.02, radius: 0.20 },
    { name: "Varanasi", lat: 25.32, lon: 83.01, radius: 0.20 },
    { name: "Meerut", lat: 28.98, lon: 77.71, radius: 0.20 },
    { name: "Prayagraj", lat: 25.43, lon: 81.85, radius: 0.20 },
    { name: "Bareilly", lat: 28.37, lon: 79.43, radius: 0.20 },
    { name: "Gorakhpur", lat: 26.76, lon: 83.37, radius: 0.20 },
    { name: "Jhansi", lat: 25.45, lon: 78.57, radius: 0.18 },
    { name: "Noida", lat: 28.57, lon: 77.36, radius: 0.12 },
    { name: "Ghaziabad", lat: 28.67, lon: 77.42, radius: 0.12 },
    { name: "Aligarh", lat: 27.90, lon: 78.09, radius: 0.18 },
    { name: "Moradabad", lat: 28.84, lon: 78.77, radius: 0.18 },
    { name: "Saharanpur", lat: 29.96, lon: 77.55, radius: 0.18 },
    { name: "Firozabad", lat: 27.16, lon: 78.40, radius: 0.12 },
    { name: "Banda", lat: 25.48, lon: 80.34, radius: 0.15 },
    { name: "Chitrakoot", lat: 25.20, lon: 80.88, radius: 0.10 },
    { name: "Mirzapur", lat: 25.14, lon: 82.57, radius: 0.12 },
    { name: "Sonbhadra", lat: 24.68, lon: 83.07, radius: 0.15 },
    { name: "Azamgarh", lat: 26.07, lon: 83.19, radius: 0.12 },
    { name: "Ballia", lat: 25.76, lon: 84.15, radius: 0.12 },
    { name: "Basti", lat: 26.79, lon: 82.74, radius: 0.12 },
    { name: "Mahrajganj", lat: 27.38, lon: 83.30, radius: 0.10 },
    { name: "Kanpur Dehat", lat: 26.33, lon: 79.96, radius: 0.10 },
    { name: "Unnao", lat: 26.54, lon: 80.49, radius: 0.10 },
    { name: "Sitapur", lat: 27.57, lon: 80.68, radius: 0.10 },
    { name: "Lakhimpur Kheri", lat: 27.94, lon: 80.70, radius: 0.10 },
    { name: "Bahraich", lat: 27.57, lon: 81.60, radius: 0.10 },
    { name: "Gonda", lat: 27.13, lon: 81.94, radius: 0.10 },
    { name: "Faizabad", lat: 26.77, lon: 82.13, radius: 0.10 },
    { name: "Ambedkar Nagar", lat: 26.44, lon: 82.58, radius: 0.10 },
    { name: "Deoria", lat: 26.50, lon: 83.79, radius: 0.10 },
    { name: "Kushinagar", lat: 26.74, lon: 83.89, radius: 0.10 },
    { name: "Mau", lat: 25.94, lon: 83.56, radius: 0.10 },
  ]},
];

function reverseGeocode(lat, lon) {
  if (!Number.isFinite(lat) || !Number.isFinite(lon)) return null;

  // Find state
  let state = null;
  for (const sb of STATE_BOUNDARIES) {
    if (lat >= sb.latMin && lat <= sb.latMax && lon >= sb.lonMin && lon <= sb.lonMax) {
      state = sb;
      break;
    }
  }
  if (!state) return { state: "Unknown", city: "Unknown", district: "Unknown" };

  // Find nearest city within state
  let nearestCity = null;
  let minDist = Infinity;
  for (const city of state.cities) {
    const dLat = Math.abs(lat - city.lat);
    const dLon = Math.abs(lon - city.lon);
    const dist = Math.sqrt(dLat * dLat + dLon * dLon);
    if (dist < minDist) { minDist = dist; nearestCity = city; }
  }

  const distKm = (minDist * 111).toFixed(1); // rough km conversion
  const withinCity = nearestCity && minDist <= nearestCity.radius;

  return {
    state: state.state,
    city: nearestCity ? nearestCity.name : "Unknown",
    distanceToCityKm: distKm,
    withinCity: withinCity,
    nearestCity: nearestCity?.name || "",
  };
}

function getFacilityInfo(fireData) {
  const name = fireData.display_site_name || fireData.site_name || "";
  const type = fireData.display_site_type || fireData.site_type || "";
  const source = fireData.coordinate_source || "";
  const dist = fireData.named_facility_distance_km;
  const isReal = String(source).toUpperCase().includes("REAL_GIS");
  return { name, type, source, distance: dist, isRealGIS: isReal };
}

function getGeminiKey() { return localStorage.getItem("thermoscope-gemini-key") || ""; }
function setGeminiKey(key) { localStorage.setItem("thermoscope-gemini-key", key); }

async function callGemini(prompt, fireContext) {
  const key = getGeminiKey();
  if (!key) return null;

  const seasonal = getSeasonalContext().join("\n");
  const alerts = fireContext ? getAlertContext(fireContext.grid_id) : null;
  const ctxParts = [];
  if (fireContext) ctxParts.push(`Fire Data:\n${JSON.stringify(fireContext, null, 2)}`);
  if (seasonal) ctxParts.push(`Seasonal Context:\n${seasonal}`);
  if (alerts) ctxParts.push(`Active Alerts for this grid:\n${JSON.stringify(alerts.slice(0,3), null, 2)}`);

  try {
    const resp = await fetch(`${GEMINI_ENDPOINT}?key=${key}`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        system_instruction: { parts: [{ text: GEMINI_SYSTEM }] },
        contents: [{ parts: [{ text: prompt + (ctxParts.length ? "\n\n" + ctxParts.join("\n\n") : "") }] }],
        generationConfig: { temperature: 0.7, maxOutputTokens: 1500 }
      })
    });
    if (!resp.ok) return null;
    const data = await resp.json();
    return data.candidates?.[0]?.content?.parts?.[0]?.text || null;
  } catch (e) {
    console.warn("Gemini API error:", e);
    return null;
  }
}

// ============================================================
// XAI CHATBOT — SMART QUERY ROUTER
// ============================================================

const INTENT_RULES = [
  { intent: "greeting", patterns: ["hello", "hi ", "hey", "namaste", "namaskar", "hlo", "hii", "good morning", "good evening", "kaise ho", "kya haal", "sup", "yo"] },
  { intent: "about", patterns: ["who are you", "what are you", "about you", "tum kaun ho", "tumhara naam", "your name", "介绍", "about agnirakshak", "agnirakshak kya hai", "project kya hai", "ye kya hai", "kya karta hai"] },
  { intent: "explain", patterns: ["why", "classif", "explain", "reason", "how was", "basis", "determin", "kyun", "kyu", "kaise", "kaise pata", "kyun bola"] },
  { intent: "risks", patterns: ["risk", "danger", "threat", "impact", "hazard", "harm", "effect", "khatra", "nuksan", "nuksaan", "asar", "effect", "dikkat"] },
  { intent: "actions", patterns: ["action", "precaution", "safety", "prevent", "measure", "plan", "respond", "protocol", "what to do", "kya karein", "kya karna", "upay", "bachav", "suraksha"] },
  { intent: "compare", patterns: ["compare", "similar", "same type", "other", "versus", "different", "alag", "baki", "dusra"] },
  { intent: "trend", patterns: ["grow", "trend", "increas", "decreas", "worsen", "improv", "getting", "badh", "ghat", "barh"] },
  { intent: "emergency", patterns: ["emergency", "urgent", "critical", "immediate", "now", "help", "bachao", "turant", "abhi", "jaldi"] },
  { intent: "legal", patterns: ["legal", "law", "act", "regulation", "rule", "compliance", "violation", "penalty", "fine", "FIR", "kanoon", "kanun", "jurmana", "sazaa"] },
  { intent: "seasonal", patterns: ["season", "month", "when", "time of year", "period", "mausam", "kaunsa month", " kab"] },
  { intent: "agencies", patterns: ["agency", "who", "department", "ministry", "report to", "contact", "kaunsa dept", "kaun"] },
  { intent: "nrt", patterns: ["live", "current", "now", "today", "latest", "real.time", "abhi", "filhal"] },
  { intent: "stats", patterns: ["stat", "number", "count", "total", "how many", "data", "kitna", "kitne", "sankhya", "ginti"] },
  { intent: "geo", patterns: ["state", "city", "district", "region", "area", "where", "kaha", "kahan", "kis state", "kis rajya", "kaunsa state", "kaunsa sheher", "which state", "which city", "which region", "kaunsa area", "up bihar", "jharkhand", "punjab haryana", "uttarakhand"] },
  { intent: "about_fire", patterns: ["fire", "aag", "agni", "flame", "jalna", "jala", "burning", "burn"] },
  { intent: "about_satellite", patterns: ["satellite", "nasa", "firms", "viirs", "remote sensing", "space", "upar se", "upar se dekhna"] },
  { intent: "key", patterns: ["api key", "setkey", "gemini key", "configure"] }
];

function detectIntent(query) {
  const q = query.toLowerCase().trim();
  for (const rule of INTENT_RULES) {
    if (rule.patterns.some(p => q.includes(p))) return rule.intent;
  }
  return "general";
}

// ============================================================
// XAI CHATBOT — RULE-BASED RESPONSES (ENHANCED)
// ============================================================

function ruleBasedResponse(query, fireData) {
  const intent = detectIntent(query);
  const ft = normalizeFireType(fireData?.fire_type);
  const kb = FIRE_KNOWLEDGE[ft] || FIRE_KNOWLEDGE.UNCLASSIFIED;
  const features = fireData ? computeXAI(fireData) : [];
  const severity = features.length ? getSeverityLabel(computeOverallSeverity(fireData, features)) : null;

  switch (intent) {
    case "greeting": return generateGreetingResponse();
    case "about": return generateAboutResponse();
    case "geo": return generateGeoResponse(query);
    case "about_fire": return generateAboutFireResponse(query, fireData, kb);
    case "about_satellite": return generateAboutSatelliteResponse();
    case "explain": return generateExplainResponse(fireData, kb, features, severity);
    case "risks": return generateRiskResponse(fireData, kb, features, severity);
    case "actions": return generateActionsResponse(fireData, kb);
    case "compare": return generateComparison(fireData);
    case "trend": return generateTrendAnalysis(fireData);
    case "emergency": return generateEmergencyResponse(fireData, kb, severity);
    case "legal": return generateLegalResponse(kb);
    case "seasonal": return generateSeasonalResponse();
    case "agencies": return generateAgenciesResponse(kb);
    case "nrt": return generateNRTResponse();
    case "stats": return generateStatsResponse();
    case "key": return "Set your Gemini API key via the ⚙️ button in the header.";
    default: return generateGeneralResponse(fireData, kb, features, severity, query);
  }
}

function generateGreetingResponse() {
  const hour = new Date().getHours();
  let timeGreeting = hour < 12 ? "🌅 Good morning / Namaste!" : hour < 17 ? "☀️ Good afternoon / Namaskar!" : "🌙 Good evening / Namaste!";
  let text = `${timeGreeting} 🙏<br><br>`;
  text += `Main <strong>AgniRakshak AI</strong> hoon — aapka fire risk analysis assistant! 🔥<br><br>`;
  text += `<strong>Main ye sab kar sakta hoon:</strong><br>`;
  text += `• 🔍 Fire classification kyun hua — reason & XAI explanation<br>`;
  text += `• ⚠️ Risk assessment — kitna khatra hai<br>`;
  text += `• 🛡️ Safety precautions & action plans — kya karna hai<br>`;
  text += `• 🚨 Emergency protocols — turant kya karein<br>`;
  text += `• 📊 Data analysis — stats, comparison, trends<br>`;
  text += `• 🌍 Geographic info — kaunsa state, city, region<br>`;
  text += `• 🛰️ Satellite monitoring — kaise kaam karta hai<br>`;
  text += `• 📅 Seasonal context — abhi ka mausam & fire season<br>`;
  text += `• 📜 Legal framework — kaun sa act lagta hai<br><br>`;
  text += `<strong>Kuch bhi puchho — Hinglish, Hindi, ya English — main samajhta hoon!</strong> 😊<br><br>`;
  text += `<em>💡 Map pe koi bhi fire marker click karo aur main uska full analysis karunga!</em>`;
  return text;
}

function generateAboutResponse() {
  let text = `🤖 <strong>AgniRakshak AI</strong> — AI-Enabled Fire Risk Intelligence\n\n`;
  text += `Main <strong>AgniRakshak</strong> project ka AI assistant hoon. Ye system NASA FIRMS satellite data use karke fire risk monitor karta hai.\n\n`;
  text += `<strong>Kya karta hai ye system:</strong>\n`;
  text += `• 🛰️ NASA FIRMS VIIRS satellites se real-time fire detections track karta hai\n`;
  text += `• 🧠 ML model se fire risk score calculate karta hai (0-100)\n`;
  text += `• 🔥 Fire types classify karta hai: Industrial, Agricultural, Forest, Mining\n`;
  text += `• 📊 Historical data (2020-present) se patterns analyze karta hai\n`;
  text += `• 🗺️ Regional risk zones map pe dikhata hai\n`;
  text += `• 📡 Live NRT (Near Real-Time) monitoring karta hai\n\n`;
  text += `<strong>Coverage:</strong> North India + surrounding states\n`;
  text += `<strong>Data:</strong> ${gridData.length.toLocaleString("en-IN")} grid cells | ${gridData.reduce((s,r) => s + (Number(r.total_detections)||0), 0).toLocaleString("en-IN")} total FIRMS detections\n\n`;
  text += `<em>Main aapke har sawaal ka jawab de sakta hoon — fire, risk, safety, geography, kuch bhi puchho!</em>`;
  return text.replace(/\n/g, "<br>");
}

function generateGeoResponse(query) {
  const q = query.toLowerCase();
  const lang = detectLanguage(query);
  // Check for state mentions
  let foundState = null;
  let foundCity = null;
  for (const [key, state] of Object.entries(GEO_KNOWLEDGE.states)) {
    if (q.includes(key)) { foundState = state; break; }
  }
  for (const [city, info] of Object.entries(GEO_KNOWLEDGE.cities)) {
    if (q.includes(city)) { foundCity = { name: city, info }; break; }
  }
  if (foundCity) {
    let text = `📍 <strong>${foundCity.name.toUpperCase()}</strong>\n\n`;
    text += `${foundCity.info}\n\n`;
    // Find fires in this city's state
    const stateKey = Object.keys(GEO_KNOWLEDGE.states).find(k => q.includes(k));
    if (stateKey) {
      const stateFires = gridData.filter(r => {
        const lat = Number(r.latitude) || 0;
        const lon = Number(r.longitude) || 0;
        return lat > 0 && lon > 0;
      });
      text += `<strong>Thermoscope data mein ${foundCity.name} ke nearby fires:</strong> ${stateFires.length} grid cells tracked.`;
    }
    return text.replace(/\n/g, "<br>");
  }
  if (foundState) {
    let text = `📍 <strong>${foundState.full}</strong>\n\n`;
    text += `Capital: ${foundState.capitals[0]}\n`;
    text += `Major Districts: ${foundState.majorDistricts.join(", ")}\n\n`;
    text += `🔥 <strong>Fire Situation:</strong>\n${foundState.fireNote}\n\n`;
    // Count fires in this state's approximate lat/lon range
    text += `📊 Thermoscope monitoring: North India region covers parts of this state.`;
    return text.replace(/\n/g, "<br>");
  }
  // General geography question
  let text = `🌍 <strong>Geographic Fire Information</strong>\n\n`;
  text += `Thermoscope North India region monitor karta hai. Yahan major fire-prone states hain:\n\n`;
  text += `• 🌾 <strong>Punjab/Haryana</strong> — Stubble burning (Oct-Nov)\n`;
  text += `• 🏭 <strong>UP (Kanpur, Varanasi)</strong> — Industrial emissions\n`;
  text += `• 🌲 <strong>Uttarakhand/HP</strong> — Forest fires (Mar-Jun)\n`;
  text += `• ⛏️ <strong>Jharkhand</strong> — Coal mine fires (Dhanbad/Jharia)\n`;
  text += `• 🏭 <strong>Delhi NCR</strong> — Transboundary pollution + industrial\n\n`;
  text += `<em>Kisi specific state ya city ke baare mein puchho!</em>`;
  return text.replace(/\n/g, "<br>");
}

function generateAboutFireResponse(query, fireData, kb) {
  const q = query.toLowerCase();
  let text = `🔥 <strong>Fire se related jaankari:</strong><br><br>`;
  if (fireData) {
    text += `<strong>Selected fire:</strong> ${kb.label}<br>`;
    text += `Risk Score: ${Number(fireData.risk_score || 0).toFixed(1)}/100<br>`;
    text += `Risk Level: ${fireData.risk_level || "N/A"}<br>`;
    text += `Avg FRP: ${Number(fireData.avg_frp || 0).toFixed(1)} MW<br><br>`;
  }
  text += `<strong>Fire Types jo track karte hain:</strong><br>`;
  text += `• 🏭 Industrial — Factories, refineries, power plants<br>`;
  text += `• 🌾 Agricultural — Stubble burning, crop residue<br>`;
  text += `• 🌲 Forest — Wildfires, jungle mein aag<br>`;
  text += `• ⛏️ Mining — Coal mine fires, blasting<br><br>`;
  text += `<strong>Fire Radiative Power (FRP):</strong> Ye batata hai fire kitna powerful hai MW mein. Zyada FRP = zyada intense fire.<br><br>`;
  text += `<em>Koi specific fire type ke baare mein detail chahiye toh batao!</em>`;
  return text;
}

function generateAboutSatelliteResponse() {
  let text = `🛰️ <strong>Satellite Fire Monitoring — Kaise kaam karta hai:</strong><br><br>`;
  text += `<strong>Satellites used:</strong><br>`;
  text += `• VIIRS S-NPP (NASA Suomi NPP)<br>`;
  text += `• VIIRS NOAA-20<br>`;
  text += `• VIIRS NOAA-21<br><br>`;
  text += `<strong>Technology:</strong><br>`;
  text += `• 375m resolution thermal detection<br>`;
  text += `• Detects fires as small as 0.5 MW<br>`;
  text += `• Passes over India 2-4 times daily<br>`;
  text += `• NRT (Near Real-Time) data available within 3 hours<br><br>`;
  text += `<strong>NASA FIRMS:</strong> Fire Information for Resource Management System — free global fire data service.<br><br>`;
  text += `<strong>Thermoscope uses:</strong><br>`;
  text += `• Historical data: 2020-present (500+ CSV files)<br>`;
  text += `• Live monitoring: Last 24-48 hours NRT<br>`;
  text += `• Grid system: 0.05° cells (~5km) for spatial analysis<br>`;
  text += `• ML model: Random Forest for risk prediction<br><br>`;
  text += `<em>3 satellites milke poore North India cover karte hain!</em>`;
  return text;
}

function generateExplainResponse(fireData, kb, features, severity) {
  if (!fireData) return "⚠️ Select a fire marker on the map first to get a classification explanation.";
  let text = `${kb.emoji} <strong>Why classified as ${kb.label}?</strong><br><br>`;
  if (severity) text += `${severity.emoji} <strong>Overall Severity: <span style="color:${severity.color}">${severity.label}</span></strong><br>`;
  text += `Fire type reason: <em>${fireData.fire_type_reason || "Pattern-based classification"}</em><br>`;
  text += `Confidence: <strong>${((fireData.fire_type_confidence || 0) * 100).toFixed(0)}%</strong><br><br>`;
  text += `<strong>📊 Feature Importance Breakdown:</strong>`;
  text += renderXAIChart(features);
  text += `<br><strong>📝 Detailed Analysis:</strong><br>`;
  features.forEach(f => { text += `• <em>${f.name}</em> (${f.score}%): ${f.reason}<br>`; });
  text += `<br><strong>💡 Key Insight:</strong> `;
  const topFeature = [...features].sort((a, b) => b.score - a.score)[0];
  if (topFeature) text += `The strongest signal is <strong>${topFeature.name}</strong> at ${topFeature.score}%. ${topFeature.reason}.`;
  return text;
}

function generateRiskResponse(fireData, kb, features, severity) {
  let text = `${kb.emoji} <strong>Risk Assessment: ${kb.label}</strong><br><br>`;
  if (severity) text += `${severity.emoji} Severity Level: <strong style="color:${severity.color}">${severity.label}</strong><br>`;
  if (fireData) {
    text += `Risk Score: <strong>${Number(fireData.risk_score || 0).toFixed(1)}/100</strong> | Risk Level: <strong>${fireData.risk_level || "N/A"}</strong><br>`;
    text += `Avg FRP: <strong>${Number(fireData.avg_frp || 0).toFixed(1)} MW</strong> | Max FRP: <strong>${Number(fireData.max_frp || 0).toFixed(1)} MW</strong><br>`;
  }
  text += `<br><strong>🔴 Probable Causes:</strong><br>`;
  kb.causes.forEach(c => { text += `• ${c}<br>`; });
  text += `<br><strong>💥 Impact Assessment:</strong><br>${kb.impact}`;
  const alerts = fireData ? getAlertContext(fireData.grid_id) : null;
  if (alerts && alerts.length) {
    text += `<br><br><strong>🚨 Active Alerts:</strong> ${alerts.length} alert(s) for this grid`;
    alerts.slice(0, 2).forEach(a => { text += `<br>• [${(a.severity || "medium").toUpperCase()}] ${a.alert_type || "ALERT"}`; });
  }
  return text;
}

function generateActionsResponse(fireData, kb) {
  let text = `${kb.emoji} <strong>Action Plan & Precautions</strong><br><br>`;
  text += `<strong>🛡️ Safety Precautions:</strong><br>`;
  kb.precautions.forEach((p, i) => { text += `${i+1}. ${p}<br>`; });
  text += `<br><strong>⚡ Recommended Actions:</strong><br>`;
  kb.actions.forEach((a, i) => { text += `${i+1}. ${a}<br>`; });
  text += `<br><strong>🏛️ Responsible Agencies:</strong><br>`;
  kb.agencies.forEach(a => { text += `• ${a}<br>`; });
  if (kb.legalFramework) {
    text += `<br><strong>📜 Legal Framework:</strong><br>`;
    kb.legalFramework.forEach(l => { text += `• ${l}<br>`; });
  }
  return text;
}

function generateEmergencyResponse(fireData, kb, severity) {
  const ep = kb.emergencyProtocol;
  if (!ep) return generateActionsResponse(fireData, kb);
  let text = `${kb.emoji} <strong>🚨 Emergency Response Protocol</strong><br><br>`;
  if (severity) text += `${severity.emoji} Severity: <strong style="color:${severity.color}">${severity.label}</strong><br><br>`;
  text += `<strong>⚡ IMMEDIATE (0-1 hours):</strong><br>`;
  ep.immediate.forEach(a => { text += `• 🔴 ${a}<br>`; });
  text += `<br><strong>📋 SHORT-TERM (1-72 hours):</strong><br>`;
  ep.shortTerm.forEach(a => { text += `• 🟡 ${a}<br>`; });
  text += `<br><strong>📅 LONG-TERM (1-4 weeks):</strong><br>`;
  ep.longTerm.forEach(a => { text += `• 🟢 ${a}<br>`; });
  text += `<br><strong>🏛️ Agencies to contact:</strong><br>`;
  kb.agencies.forEach(a => { text += `• ${a}<br>`; });
  return text;
}

function generateLegalResponse(kb) {
  let text = `📜 <strong>Legal Framework & Compliance</strong><br><br>`;
  if (kb.legalFramework) {
    kb.legalFramework.forEach(l => { text += `• ${l}<br>`; });
  }
  text += `<br><strong>Key Penalties:</strong><br>`;
  text += `• IPC Section 188: Up to 1 month imprisonment or ₹200 fine<br>`;
  text += `• Disaster Management Act 2005: Up to 1 year imprisonment or ₹1 lakh fine<br>`;
  text += `• NGT can impose penalty up to ₹5 crore for environmental damage<br>`;
  text += `• CPCB: Closure of non-compliant units + compensation<br>`;
  return text;
}

function generateSeasonalResponse() {
  const contexts = getSeasonalContext();
  let text = `📅 <strong>Seasonal Fire Context</strong><br><br>`;
  contexts.forEach(c => { text += `${c}<br>`; });
  text += `<br><strong>Peak Risk Months by Type:</strong><br>`;
  text += `• 🌾 Agricultural: <strong>Oct-Nov</strong> (stubble) + <strong>Apr-May</strong> (pre-monsoon)<br>`;
  text += `• 🌲 Forest: <strong>Mar-Jun</strong> (pre-monsoon dry)<br>`;
  text += `• 🏭 Industrial: <strong>Year-round</strong> (continuous)<br>`;
  text += `• ⛏️ Mining: <strong>Year-round</strong> (peak in dry months)<br>`;
  return text;
}

function generateAgenciesResponse(kb) {
  let text = `🏛️ <strong>Responsible Agencies & Contacts</strong><br><br>`;
  kb.agencies.forEach(a => { text += `• <strong>${a}</strong><br>`; });
  text += `<br><strong>Emergency Numbers:</strong><br>`;
  text += `• 🚒 Fire Brigade: <strong>101</strong><br>`;
  text += `• 🚑 Ambulance: <strong>108</strong><br>`;
  text += `• 🚔 Police: <strong>100</strong><br>`;
  text += `• 🆘 NDMA: <strong>1070</strong><br>`;
  text += `• 🌿 NDRF: <strong>011-24363260</strong><br>`;
  return text;
}

function generateNRTResponse() {
  const nrtCount = nrtData.length;
  let text = `📡 <strong>Live NRT Status</strong><br><br>`;
  text += `Detections: <strong>${nrtCount.toLocaleString("en-IN")}</strong><br>`;
  if (nrtCount > 0) {
    const bySeverity = {};
    nrtData.forEach(d => { const s = d.nrt_severity || "normal"; bySeverity[s] = (bySeverity[s] || 0) + 1; });
    text += `<br><strong>By Severity:</strong><br>`;
    Object.entries(bySeverity).sort((a,b) => b[1]-a[1]).forEach(([s, c]) => {
      const emoji = { critical: "🔴", high: "🟠", elevated: "🟡", normal: "🟢" }[s] || "⚪";
      text += `${emoji} ${s.toUpperCase()}: <strong>${c}</strong><br>`;
    });
  }
  const alertCount = getActiveAlertCount();
  text += `<br>Active Alerts: <strong>${alertCount}</strong>`;
  return text;
}

function generateStatsResponse() {
  let text = `📊 <strong>Dashboard Statistics</strong><br><br>`;
  text += `Total Grid Cells: <strong>${gridData.length.toLocaleString("en-IN")}</strong><br>`;
  const crit = gridData.filter(r => r.risk_level === "CRITICAL").length;
  const high = gridData.filter(r => r.risk_level === "HIGH").length;
  text += `Critical Risk: <strong>${crit.toLocaleString("en-IN")}</strong><br>`;
  text += `High Risk: <strong>${high.toLocaleString("en-IN")}</strong><br>`;
  const byType = {};
  gridData.forEach(r => { const t = normalizeFireType(r.fire_type); byType[t] = (byType[t] || 0) + 1; });
  text += `<br><strong>By Fire Type:</strong><br>`;
  Object.entries(byType).sort((a,b) => b[1]-a[1]).forEach(([t, c]) => {
    text += `${FIRE_KNOWLEDGE[t]?.emoji || "❓"} ${FIRE_KNOWLEDGE[t]?.label || t}: <strong>${c.toLocaleString("en-IN")}</strong><br>`;
  });
  text += `<br>NRT Live Detections: <strong>${nrtData.length}</strong><br>`;
  text += `Active Alerts: <strong>${getActiveAlertCount()}</strong>`;
  return text;
}

function generateGeneralResponse(fireData, kb, features, severity, query) {
  const q = (query || "").toLowerCase();
  const lang = detectLanguage(query || "");
  // If no fire selected, give helpful general response
  if (!fireData) {
    let text = `🤖 <strong>Mujhe aapka sawaal samajh nahi aaya</strong>, lekin main in cheezon mein help kar sakta hoon:<br><br>`;
    text += `<strong>🔥 Fire Analysis:</strong><br>`;
    text += `• Map pe koi fire marker click karo → main uska analysis karunga<br>`;
    text += `• "Why this classification?" → classification reason<br>`;
    text += `• "What are the risks?" → risk assessment<br>`;
    text += `• "Emergency protocol" → emergency response plan<br><br>`;
    text += `<strong>📊 Data & Stats:</strong><br>`;
    text += `• "Dashboard stats" → total grid cells, risk levels<br>`;
    text += `• "Live NRT status" → current satellite detections<br>`;
    text += `• "Seasonal context" → current fire season info<br><br>`;
    text += `<strong>🌍 General Info:</strong><br>`;
    text += `• "Which state mein risk hai?" → geographic fire info<br>`;
    text += `• "About AgniRakshak" → project details<br>`;
    text += `• "Satellite kaise kaam karta hai?" → monitoring tech<br>`;
    text += `• "Emergency number" → 101 (fire), 108 (ambulance), 100 (police)<br><br>`;
    text += `<em>Kuch bhi puchho — fire, geography, safety, data, kuch bhi! Main jawab dunga. 😊</em>`;
    return text;
  }
  // Fire selected but unmatched query — give fire summary + suggestions
  let text = `${kb.emoji} <strong>${kb.label}</strong><br><br>`;
  if (severity) text += `${severity.emoji} Severity: <strong style="color:${severity.color}">${severity.label}</strong><br>`;
  text += `<strong>Causes:</strong><br>`;
  kb.causes.slice(0, 3).forEach(c => { text += `• ${c}<br>`; });
  text += `<br><strong>Impact:</strong> ${kb.impact}<br><br>`;
  text += `<em>💡 Aap ye bhi puchh sakte ho: risks, actions, emergency protocol, legal framework, comparison, trend, ya geographic info!</em>`;
  return text;
}

function generateComparison(fireData) {
  const ft = normalizeFireType(fireData?.fire_type);
  const sameType = gridData.filter(r => normalizeFireType(r.fire_type) === ft);
  if (sameType.length < 2) return `🔍 Not enough ${FIRE_KNOWLEDGE[ft]?.label || ft} sites for comparison (found ${sameType.length}).`;

  const stats = {
    count: sameType.length,
    avgRisk: sameType.reduce((s, r) => s + (Number(r.risk_score) || 0), 0) / sameType.length,
    avgFrp: sameType.reduce((s, r) => s + (Number(r.avg_frp) || 0), 0) / sameType.length,
    avgRec: sameType.reduce((s, r) => s + (Number(r.recurrence_ratio) || 0), 0) / sameType.length,
    avgPersist: sameType.reduce((s, r) => s + (Number(r.persistent_months) || 0), 0) / sameType.length,
    maxRisk: Math.max(...sameType.map(r => Number(r.risk_score) || 0)),
    minRisk: Math.min(...sameType.map(r => Number(r.risk_score) || 0)),
  };
  const myRisk = Number(fireData?.risk_score) || 0;
  const myFrp = Number(fireData?.avg_frp) || 0;
  const myRec = Number(fireData?.recurrence_ratio) || 0;

  let text = `📊 <strong>Comparison: ${sameType.length} similar ${FIRE_KNOWLEDGE[ft]?.emoji || ""} ${FIRE_KNOWLEDGE[ft]?.label || ft} fires</strong><br><br>`;
  text += `<div class="chat-compare-row"><span>Metric</span><span>This Fire → Avg (${sameType.length} sites)</span></div>`;
  text += `<div class="chat-compare-row"><span>Risk Score</span><span>${myRisk.toFixed(1)} → ${stats.avgRisk.toFixed(1)} <span class="chat-compare-highlight">${myRisk > stats.avgRisk ? "▲ +" + (myRisk - stats.avgRisk).toFixed(1) : "▼ -" + (stats.avgRisk - myRisk).toFixed(1)}</span></span></div>`;
  text += `<div class="chat-compare-row"><span>Avg FRP</span><span>${myFrp.toFixed(1)} → ${stats.avgFrp.toFixed(1)} MW</span></div>`;
  text += `<div class="chat-compare-row"><span>Recurrence</span><span>${(myRec * 100).toFixed(0)}% → ${(stats.avgRec * 100).toFixed(0)}%</span></div>`;
  text += `<div class="chat-compare-row"><span>Persistence</span><span>${(Number(fireData?.persistent_months) || 0)} → ${stats.avgPersist.toFixed(1)} months</span></div>`;
  text += `<div class="chat-compare-row"><span>Risk Range</span><span>${stats.minRisk.toFixed(0)} - ${stats.maxRisk.toFixed(0)}</span></div>`;
  text += `<div class="chat-compare-row"><span>Total Sites</span><span>${sameType.length.toLocaleString("en-IN")}</span></div>`;
  text += `<br><em>${myRisk > stats.avgRisk ? "📈 This fire scores ABOVE average — higher priority for monitoring." : myRisk < stats.avgRisk ? "📉 This fire scores below average — lower relative risk." : "➡️ This fire is at the average risk level for its type."}</em>`;
  return text;
}

function generateTrendAnalysis(fireData) {
  const d30 = Number(fireData?.detections_30d) || 0;
  const d90 = Number(fireData?.detections_90d) || 0;
  const d90avg = d90 / 3;
  const growthRate = d90avg > 0 ? ((d30 - d90avg) / d90avg * 100) : 0;
  let trend = "stable", emoji = "➡️";
  if (d30 > d90avg * 1.5) { trend = "INCREASING"; emoji = "📈"; }
  else if (d30 < d90avg * 0.6) { trend = "DECREASING"; emoji = "📉"; }

  let text = `${emoji} <strong>Fire Activity Trend Analysis</strong><br><br>`;
  text += `<div class="chat-compare-row"><span>30-day detections</span><span><strong>${d30.toLocaleString("en-IN")}</strong></span></div>`;
  text += `<div class="chat-compare-row"><span>90-day detections</span><span>${d90.toLocaleString("en-IN")} (avg ${d90avg.toFixed(0)}/mo)</span></div>`;
  text += `<div class="chat-compare-row"><span>Growth Rate</span><span class="chat-compare-highlight">${growthRate >= 0 ? "+" : ""}${growthRate.toFixed(1)}%</span></div>`;
  text += `<div class="chat-compare-row"><span>Trend</span><span><strong>${trend}</strong></span></div>`;
  text += `<br>`;
  if (trend === "INCREASING") {
    text += `⚠️ <strong>Activity is accelerating (+${growthRate.toFixed(0)}%).</strong> This may indicate an emerging fire source or seasonal intensification. Recommend increased monitoring frequency and ground verification.`;
  } else if (trend === "DECREASING") {
    text += `✅ <strong>Activity is declining (${growthRate.toFixed(0)}%).</strong> The fire source may be seasonal or temporarily inactive. Continue periodic monitoring.`;
  } else {
    text += `➡️ <strong>Activity is stable.</strong> Consistent with historical patterns. No immediate escalation detected.`;
  }
  return text;
}

// ============================================================
// XAI CHATBOT — UI LOGIC (ENHANCED)
// ============================================================

let chatContext = null;
let chatOpen = false;
let chatMessages = [];
let chatHistory = []; // conversation memory

function initChatbot() {
  const fab = document.getElementById("chatbotFab");
  const panel = document.getElementById("chatbotPanel");
  const closeBtn = document.getElementById("chatbotClose");
  const minimizeBtn = document.getElementById("chatbotMinimize");
  const sendBtn = document.getElementById("chatbotSend");
  const input = document.getElementById("chatbotInput");

  if (!fab || !panel) return;

  fab.addEventListener("click", () => {
    chatOpen = !chatOpen;
    panel.style.display = chatOpen ? "flex" : "none";
    if (chatOpen && chatMessages.length === 0) showWelcome();
    if (chatOpen) { setTimeout(() => input?.focus(), 100); }
  });
  closeBtn.addEventListener("click", () => { chatOpen = false; panel.style.display = "none"; });
  minimizeBtn.addEventListener("click", () => { chatOpen = false; panel.style.display = "none"; });
  sendBtn.addEventListener("click", sendUserMessage);
  input.addEventListener("keydown", e => { if (e.key === "Enter") sendUserMessage(); });
}

function showWelcome() {
  const key = getGeminiKey();
  const nrtCount = nrtData.length;
  const alertCount = getActiveAlertCount();
  const season = getSeasonalContext()[0] || "";

  let welcome = `👋 Hello / Namaste! I'm <strong>AgniRakshak AI</strong> 🔥<br><br>`;
  welcome += `Main fire classifications explain karta hoon, precautions suggest karta hoon, aur emergency protocols provide karta hoon.`;
  welcome += ` Aap <strong>Hinglish, Hindi, ya English</strong> mein baat kar sakte ho — main sab samajhta hoon! 😊<br><br>`;
  welcome += `📊 <strong>${gridData.length.toLocaleString("en-IN")}</strong> grid cells | 📡 <strong>${nrtCount}</strong> live detections | 🚨 <strong>${alertCount}</strong> alerts<br>`;
  if (season) welcome += `${season}<br>`;
  welcome += `<br>🎯 <strong>Quick Start:</strong> Map pe koi fire marker click karo ya neeche koi button dabao!`;
  if (!key) welcome += `<br><br><em>💡 AI responses ke liye "set api key" type karo.</em>`;

  const actions = [
    { label: "🔍 Ye classification kyun hua?", action: "explain" },
    { label: "⚠️ Risks kya hain?", action: "risks" },
    { label: "🛡️ Kya karna chahiye?", action: "actions" },
    { label: "🚨 Emergency protocol", action: "emergency" },
    { label: "📊 Compare similar fires?", action: "compare" },
    { label: "📈 Fire badh raha hai?", action: "trend" },
    { label: "🌍 Kis state mein risk hai?", action: "geo" },
    { label: "📅 Seasonal context", action: "seasonal" },
    { label: "📡 Live NRT status", action: "nrt" },
    { label: "📊 Dashboard stats", action: "stats" },
    { label: "🛰️ Satellite kaise kaam karta hai?", action: "satellite" }
  ];
  addBotMessage(welcome, actions);
}

function addBotMessage(html, quickActions) {
  const container = document.getElementById("chatbotMessages");
  if (!container) return;
  const msgDiv = document.createElement("div");
  msgDiv.className = "chat-msg bot";
  msgDiv.innerHTML = `<div class="chat-msg-avatar">🤖</div><div class="chat-msg-bubble">${html}</div>`;
  container.appendChild(msgDiv);

  if (quickActions && quickActions.length) {
    const qaDiv = document.createElement("div");
    qaDiv.className = "chat-quick-actions";
    qaDiv.style.paddingLeft = "38px";
    quickActions.forEach(qa => {
      const btn = document.createElement("button");
      btn.className = "chat-quick-btn";
      btn.textContent = qa.label;
      btn.addEventListener("click", () => handleQuickAction(qa.action));
      qaDiv.appendChild(btn);
    });
    container.appendChild(qaDiv);
  }
  container.scrollTop = container.scrollHeight;
  chatMessages.push({ role: "bot", html });
}

function addUserMessage(text) {
  const container = document.getElementById("chatbotMessages");
  if (!container) return;
  const msgDiv = document.createElement("div");
  msgDiv.className = "chat-msg user";
  msgDiv.innerHTML = `<div class="chat-msg-avatar">👤</div><div class="chat-msg-bubble">${text}</div>`;
  container.appendChild(msgDiv);
  container.scrollTop = container.scrollHeight;
  chatMessages.push({ role: "user", html: text });
  chatHistory.push({ role: "user", content: text });
}

function showTyping() {
  const container = document.getElementById("chatbotMessages");
  if (!container) return;
  const typing = document.createElement("div");
  typing.className = "chat-typing";
  typing.id = "chatTyping";
  typing.innerHTML = '<div class="chat-typing-dot"></div><div class="chat-typing-dot"></div><div class="chat-typing-dot"></div>';
  container.appendChild(typing);
  container.scrollTop = container.scrollHeight;
}

function hideTyping() { const el = document.getElementById("chatTyping"); if (el) el.remove(); }

function updateSelectedFireDisplay() {
  const el = document.getElementById("chatbotSelectedFire");
  if (!el) return;
  if (chatContext) {
    const name = chatContext.display_site_name || chatContext.site_name || chatContext.grid_id || "Unknown";
    el.textContent = `📍 ${name}`;
    el.style.display = "inline-block";
  } else {
    el.style.display = "none";
  }
}

function sendUserMessage() {
  const input = document.getElementById("chatbotInput");
  if (!input) return;
  const text = input.value.trim();
  if (!text) return;
  input.value = "";
  addUserMessage(text);
  processUserQuery(text);
}

async function processUserQuery(query) {
  const intent = detectIntent(query);

  // API key setup
  if (intent === "key") {
    const existing = getGeminiKey();
    const newKey = prompt("Enter your Gemini API Key (get one at aistudio.google.com):", existing);
    if (newKey !== null && newKey.trim()) {
      setGeminiKey(newKey.trim());
      addBotMessage("✅ Gemini API key saved! I'll now use AI-powered responses.");
    }
    return;
  }

  // Fire-specific intents
  const needsFire = ["explain", "risks", "actions", "compare", "trend", "emergency", "legal", "agencies"];
  if (needsFire.includes(intent) && !chatContext) {
    addBotMessage("⚠️ Please click a fire marker on the map first to select a fire for analysis.", [
      { label: "📡 Live NRT status", action: "nrt" },
      { label: "📊 Dashboard stats", action: "stats" },
      { label: "📅 Seasonal context", action: "seasonal" }
    ]);
    return;
  }

  // Try Gemini first
  showTyping();
  const geminiResp = await callGemini(query, chatContext);
  hideTyping();

  if (geminiResp) {
    // Add context-aware follow-ups after Gemini response
    const followUps = [];
    if (chatContext) {
      followUps.push({ label: "🔍 Why this classification?", action: "explain" });
      followUps.push({ label: "🚨 Emergency protocol", action: "emergency" });
      followUps.push({ label: "📊 Compare similar?", action: "compare" });
      followUps.push({ label: "📈 Trend analysis", action: "trend" });
    }
    followUps.push({ label: "📡 Live NRT", action: "nrt" });
    addBotMessage(geminiResp.replace(/\n/g, "<br>"), followUps);
  } else {
    const resp = ruleBasedResponse(query, chatContext);
    addBotMessage(resp);
  }
}

function handleQuickAction(action) {
  if (action === "key") { processUserQuery("set api key"); return; }
  if (action === "nrt") { addUserMessage("📡 Live NRT status"); showTyping(); setTimeout(() => { hideTyping(); addBotMessage(generateNRTResponse()); }, 400); return; }
  if (action === "stats") { addUserMessage("📊 Dashboard stats"); showTyping(); setTimeout(() => { hideTyping(); addBotMessage(generateStatsResponse()); }, 400); return; }
  if (action === "seasonal") { addUserMessage("📅 Seasonal context"); showTyping(); setTimeout(() => { hideTyping(); addBotMessage(generateSeasonalResponse()); }, 400); return; }
  if (action === "satellite") { addUserMessage("🛰️ Satellite kaise kaam karta hai?"); showTyping(); setTimeout(() => { hideTyping(); addBotMessage(generateAboutSatelliteResponse()); }, 400); return; }
  if (action === "geo") { addUserMessage("🌍 Kis state mein risk hai?"); showTyping(); setTimeout(() => { hideTyping(); addBotMessage(generateGeoResponse("state fire risk")); }, 400); return; }
  if (action === "emergency") {
    if (!chatContext) { addBotMessage("⚠️ Select a fire marker first."); return; }
    addUserMessage("🚨 Emergency protocol");
    showTyping(); setTimeout(() => { hideTyping(); addBotMessage(generateEmergencyResponse(chatContext, FIRE_KNOWLEDGE[normalizeFireType(chatContext.fire_type)] || FIRE_KNOWLEDGE.UNCLASSIFIED, null)); }, 500);
    return;
  }
  if (action === "legal") {
    if (!chatContext) { addBotMessage("⚠️ Select a fire marker first."); return; }
    addUserMessage("📜 Legal framework");
    showTyping(); setTimeout(() => { hideTyping(); addBotMessage(generateLegalResponse(FIRE_KNOWLEDGE[normalizeFireType(chatContext.fire_type)] || FIRE_KNOWLEDGE.UNCLASSIFIED)); }, 400);
    return;
  }
  if (action === "agencies") {
    if (!chatContext) { addBotMessage("⚠️ Select a fire marker first."); return; }
    addUserMessage("🏛️ Responsible agencies");
    showTyping(); setTimeout(() => { hideTyping(); addBotMessage(generateAgenciesResponse(FIRE_KNOWLEDGE[normalizeFireType(chatContext.fire_type)] || FIRE_KNOWLEDGE.UNCLASSIFIED)); }, 400);
    return;
  }

  const queryMap = {
    explain: "Explain why this fire was classified this way",
    risks: "What are the risks and impacts?",
    actions: "What actions and precautions should be taken?",
    compare: "Compare with similar fires",
    trend: "Is this fire growing?"
  };
  if (queryMap[action]) {
    if (!chatContext) { addBotMessage("⚠️ Please click a fire marker on the map first."); return; }
    addUserMessage(queryMap[action]);
    showTyping(); setTimeout(() => { hideTyping(); addBotMessage(ruleBasedResponse(queryMap[action], chatContext)); }, 500);
  }
}

// ============================================================
// XAI CHATBOT — MAP INTEGRATION (ENHANCED)
// ============================================================

function selectFireForChat(fireData) {
  chatContext = fireData;
  updateSelectedFireDisplay();

  if (!chatOpen) {
    chatOpen = true;
    const panel = document.getElementById("chatbotPanel");
    if (panel) panel.style.display = "flex";
    if (chatMessages.length === 0) showWelcome();
  }

  const name = fireData.display_site_name || fireData.site_name || fireData.grid_id || "Unknown";
  const ft = normalizeFireType(fireData.fire_type);
  const kb = FIRE_KNOWLEDGE[ft] || FIRE_KNOWLEDGE.UNCLASSIFIED;
  const features = computeXAI(fireData);
  const severity = getSeverityLabel(computeOverallSeverity(fireData, features));
  const alerts = getAlertContext(fireData.grid_id);

  // Reverse geocode — state, city, district
  const lat = Number(fireData.latitude || fireData.map_latitude) || 0;
  const lon = Number(fireData.longitude || fireData.map_longitude) || 0;
  const geo = reverseGeocode(lat, lon);
  const facility = getFacilityInfo(fireData);

  addUserMessage(`📍 Selected: ${name}`);

  showTyping();
  setTimeout(() => {
    hideTyping();
    let text = `${kb.emoji} <strong>${name}</strong><br><br>`;

    // Geographic location block
    if (geo && geo.state !== "Unknown") {
      text += `<div style="background:rgba(34,211,238,0.08);border:1px solid rgba(34,211,238,0.2);border-radius:8px;padding:8px 10px;margin-bottom:8px;">`;
      text += `<strong style="color:#22d3ee;">📍 Location:</strong><br>`;
      text += `🗺️ State: <strong>${geo.state}</strong><br>`;
      if (geo.nearestCity) {
        text += `🏙️ Nearest City: <strong>${geo.nearestCity}</strong>`;
        text += geo.withinCity ? ` <span style="color:#20e889;">(within city)</span>` : ` (${geo.distanceToCityKm} km away)`;
        text += `<br>`;
      }
      text += `🌐 Coords: ${lat.toFixed(4)}, ${lon.toFixed(4)}`;
      text += `</div>`;
    }

    // Facility / Industry info block
    if (facility.name || facility.isRealGIS) {
      text += `<div style="background:rgba(168,85,247,0.08);border:1px solid rgba(168,85,247,0.2);border-radius:8px;padding:8px 10px;margin-bottom:8px;">`;
      text += `<strong style="color:#a855f7;">🏭 Facility Info:</strong><br>`;
      if (facility.name) text += `Name: <strong>${facility.name}</strong><br>`;
      if (facility.type) text += `Type: <strong>${facility.type}</strong><br>`;
      if (facility.isRealGIS) text += `✓ <span style="color:#20e889;">GIS-verified real facility</span><br>`;
      if (facility.distance != null) text += `Distance: ${Number(facility.distance).toFixed(1)} km from thermal source`;
      text += `</div>`;
    }

    // Fire type + risk block
    text += `<strong style="color:${severity.color};">${severity.emoji} ${kb.label}</strong><br>`;
    text += `Risk: <span style="color:${severity.color}"><strong>${fireData.risk_level || "N/A"}</strong></span> | Score: <strong>${Number(fireData.risk_score || 0).toFixed(1)}</strong>/100<br>`;
    text += `Severity: <strong style="color:${severity.color}">${severity.label}</strong> (${computeOverallSeverity(fireData, features)}/100)<br>`;
    text += `FRP: ${Number(fireData.avg_frp || 0).toFixed(1)} MW avg | ${Number(fireData.max_frp || 0).toFixed(1)} MW max<br>`;
    if (alerts && alerts.length) text += `🚨 <strong>${alerts.length}</strong> active alert(s) for this grid<br>`;

    text += `<br><strong>📊 Feature Importance:</strong>`;
    text += renderXAIChart(features);
    features.slice(0, 3).forEach(f => { text += `• <em>${f.name}</em>: ${f.reason}<br>`; });
    const season = getSeasonalContext()[0];
    if (season) text += `<br>${season}`;

    const followUps = [
      { label: "🔍 Why this classification?", action: "explain" },
      { label: "⚠️ Risks kya hain?", action: "risks" },
      { label: "🛡️ Kya karna chahiye?", action: "actions" },
      { label: "🚨 Emergency protocol", action: "emergency" },
      { label: "📊 Compare similar fires?", action: "compare" },
      { label: "📈 Fire badh raha hai?", action: "trend" },
      { label: "📜 Legal framework", action: "legal" },
      { label: "🏛️ Kaun contact karein?", action: "agencies" }
    ];
    addBotMessage(text, followUps);
  }, 500);
}

// FORECAST TAB RENDERING

function renderForecastTab() {
  console.log("renderForecastTab called");
  // Try main data first, then separate _FC_DATA variable
  var fd = (window.THERMOSCOPE_DATA && window.THERMOSCOPE_DATA.forecastData && Object.keys(window.THERMOSCOPE_DATA.forecastData).length > 0)
    ? window.THERMOSCOPE_DATA.forecastData
    : (window._FC_DATA && Object.keys(window._FC_DATA).length > 0) ? window._FC_DATA : null;
  console.log("forecastData source:", fd ? "FOUND" : "MISSING");
  if (!fd || !fd.summary) { console.warn("Forecast data not loaded yet, retrying..."); setTimeout(renderForecastTab, 300); return; }
  var s = fd.summary; var ri = s.readiness_index;
  var se = document.getElementById('readinessScore');
  var le = document.getElementById('readinessLevel');
  var fe = document.getElementById('readinessFill');
  if(se){se.textContent=ri.score;se.style.color=ri.color;}
  if(le){le.textContent=ri.level;le.style.color=ri.color;}
  if(fe){fe.style.width=ri.score+'%';fe.style.background=ri.color;}
  fcS('fcCurrentYear',s.current_total_detections.toLocaleString('en-IN'));
  fcS('fcCurrentDet',s.current_year+' detections (partial)');
  fcS('fcPredicted',s.predicted_total_detections.toLocaleString('en-IN'));
  fcS('fcPredictedDet',s.next_year+' predicted');
  var te={GROWING:'📈',STABLE:'➡️',DECLINING:'📉'};
  fcS('fcTrend',(te[s.trend]||'')+' '+s.trend);
  fcS('fcTrendPct',(s.trend_pct>0?'+':'')+s.trend_pct+'% YoY');
  fcML('peakMonthsList',s.peak_months,true); fcML('lowMonthsList',s.low_months,false);
  fcBarChart(fd.monthly_patterns); fcHeat(fd.monthly_heatmap); fcTrend(fd.yearly_trend);
  fcSeason(fd.seasonal_by_year); fcGrid(fd.grid_forecasts);
  fcRenderTypeSection(fd); fcRenderTypeBarChart(fd);
  fcRenderDistricts(fd); fcRenderAlerts(fd);
}
function fcS(id,t){var e=document.getElementById(id);if(e)e.textContent=t;}
function fcML(cid,months,isPeak){
  var el=document.getElementById(cid);if(!el||!months)return;
  el.innerHTML=months.map(function(m,i){
    var bg=isPeak?'rgba(255,'+(73-i*20)+','+(61-i*20)+',0.15)':'rgba(32,232,137,0.12)';
    var tc=isPeak?'#ff6b5e':'#20e889';var ic=isPeak?'🔥':'🌿';
    return'<div class=forecast-month-item><span class=forecast-month-name>'+ic+' '+m.month+'</span><span class=forecast-month-intensity style=background:'+bg+';color:'+tc+';>'+m.intensity+'%</span></div>';
  }).join('');
}
function fcBarChart(p) {
  var el=document.getElementById('chartForecastMonthly');if(!el||!p)return;
  var mo=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  var mx=Math.max.apply(null,p.map(function(x){return x.intensity_pct;}));
  var h='<div class="fc-bars"><div class="fc-bars-axis">';
  for(var i=4;i>=0;i--){h+='<span>'+Math.round(mx*i/4)+'%</span>';}
  h+='</div><div class="fc-bars-body"><div class="fc-bars-grid">';
  for(var i=0;i<4;i++){h+='<div class="fc-bars-gridline"></div>';}
  h+='</div>';
  p.forEach(function(v,i){
    var pct=(v.intensity_pct/mx)*100;
    var c=v.intensity_pct>50?'#ff493d':v.intensity_pct>20?'#ffae42':'#20e889';
    h+='<div class="fc-bar-col"><div class="fc-bar-val">'+Math.round(v.intensity_pct)+'%</div>';
    h+='<div class="fc-bar-track"><div class="fc-bar-fill" style="height:'+pct+'%;background:'+c+'"></div></div>';
    h+='<div class="fc-bar-month">'+mo[i]+'</div>';
    h+='<div class="fc-bar-avg">'+Math.round(v.avg_detections).toLocaleString('en-IN')+'</div></div>';
  });
  h+='</div></div>';el.innerHTML=h;
}
function fcHeat(hm) {
  var el=document.getElementById('forecastHeatmap');if(!el||!hm)return;
  var mo=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
  var h='<table class=forecast-heatmap><thead><tr><th></th>';mo.forEach(function(m){h+='<th>'+m+'</th>';});h+='</tr></thead><tbody>';
  hm.forEach(function(r){h+='<tr><td class=year-label>'+r.year+'</td>';
    for(var m=1;m<=12;m++){var v=r[String(m)]||0;var raw=r['raw_'+m]||0;var pct=Math.round(v);
      var cr=Math.round(255*v/100);var cg=Math.round(100*(1-v/100));var cb=Math.round(60*(1-v/100));
      var bg='rgba('+cr+','+cg+','+cb+','+(0.15+v/100*0.6)+')';var fg=v>50?'#fff':'var(--text-secondary)';
      h+='<td style=background:'+bg+';color:'+fg+'; title='+mo[m-1]+' '+r.year+': '+raw.toLocaleString('en-IN')+'>'+pct+'</td>';}
    h+='</tr>';});h+='</tbody></table>';el.innerHTML=h;
}
function fcTrend(tr) {
  var el=document.getElementById('chartForecastTrend');if(!el||!tr||!tr.years||!tr.years.length)return;
  var yrs=tr.years;
  var mx=Math.max.apply(null,yrs.map(function(y){return y.detections;}));
  var tc={GROWING:'#ff382f',STABLE:'#20e889',DECLINING:'#22d3ee'};
  var h='<div class="fc-trend">';
  h+='<div class="fc-trend-label" style="color:'+(tc[tr.trend]||'#94a3b8')+'">'+tr.trend+': '+(tr.slope>0?'+':'')+Math.round(tr.slope).toLocaleString('en-IN')+'/yr</div>';
  h+='<div class="fc-trend-chart">';
  for(var i=0;i<4;i++){h+='<div class="fc-trend-gridline"><span>'+Math.round(mx*(3-i)/3).toLocaleString('en-IN')+'</span></div>';}
  h+='<svg class="fc-trend-svg" preserveAspectRatio="none" viewBox="0 0 100 100">';
  h+='<defs><linearGradient id="trendAreaGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#ff493d" stop-opacity="0.3"/><stop offset="100%" stop-color="#ff493d" stop-opacity="0"/></linearGradient></defs>';
  var pts=yrs.map(function(yr,idx){return{pct:yr.detections/mx*100,year:yr.year,det:yr.detections,idx:idx};});
  h+='<polygon points="0,100 '+pts.map(function(p){return p.idx/(pts.length-1)*100+','+(100-p.pct);}).join(' ')+' 100,100" fill="url(#trendAreaGrad)"/>';
  h+='<polyline points="'+pts.map(function(p){return p.idx/(pts.length-1)*100+','+(100-p.pct);}).join(' ')+'" fill="none" stroke="#ff493d" stroke-width="0.5" vector-effect="non-scaling-stroke"/>';
  pts.forEach(function(p){h+='<circle cx="'+(p.idx/(pts.length-1)*100)+'" cy="'+(100-p.pct)+'" r="1.5" fill="#ff493d" stroke="#0e141c" stroke-width="0.5" vector-effect="non-scaling-stroke"/>';});
  h+='</svg>';
  h+='<div class="fc-trend-labels">';
  pts.forEach(function(p){h+='<div class="fc-trend-point"><div class="fc-trend-val">'+p.det.toLocaleString('en-IN')+'</div><div class="fc-trend-yr">'+p.year+'</div></div>';});
  h+='</div></div></div>';el.innerHTML=h;
}
function fcSeason(sd) {
  var el=document.getElementById('chartSeasonalStack');var lg=document.getElementById('legendSeasonal');
  if(!el||!sd)return;
  var yrs=Object.keys(sd).sort();var sn=['pre_monsoon','monsoon','post_monsoon','winter'];
  var sc={pre_monsoon:'#ff493d',monsoon:'#22d3ee',post_monsoon:'#ffae42',winter:'#a855f7'};
  var sl={pre_monsoon:'Pre-Monsoon',monsoon:'Monsoon',post_monsoon:'Post-Monsoon',winter:'Winter'};
  var mT=0;
  yrs.forEach(function(y){var t=sn.reduce(function(s,k){return s+(sd[y][k]||0);},0);if(t>mT)mT=t;});
  var h='<div class="fc-seasonal"><div class="fc-seasonal-labels">';
  for(var i=3;i>=0;i--){h+='<span>'+Math.round(mT*i/3).toLocaleString('en-IN')+'</span>';}
  h+='</div><div class="fc-seasonal-body">';
  yrs.forEach(function(y){
    h+='<div class="fc-season-col"><div class="fc-season-stack">';
    sn.forEach(function(k){var v=sd[y][k]||0;var pct=(v/mT)*100;h+='<div class="fc-season-seg" style="height:'+pct+'%;background:'+sc[k]+'" title="'+sl[k]+': '+v.toLocaleString('en-IN')+'"></div>';});
    h+='</div><div class="fc-season-yr">'+y+'</div></div>';
  });
  h+='</div></div>';el.innerHTML=h;
  if(lg)lg.innerHTML=sn.map(function(k){return'<span class="chart-legend-item"><span class="chart-legend-dot" style="background:'+sc[k]+'"></span>'+sl[k]+'</span>';}).join('');
}
function fcGrid(fcs) {
  var tb=document.querySelector('#forecastGridTable tbody');if(!tb||!fcs)return;
  var tc={INDUSTRIAL_PERSISTENT:'#a855f7',AGRICULTURAL_BURNING:'#ffd400',FOREST_WILDFIRE:'#22d3ee',MINING:'#f97316',UNKNOWN:'#5b6b7a'};
  var tl={INDUSTRIAL_PERSISTENT:'Industrial',AGRICULTURAL_BURNING:'Agricultural',FOREST_WILDFIRE:'Wildfire',MINING:'Mining',UNKNOWN:'Unclassified'};
  tb.innerHTML=fcs.slice(0,20).map(function(f,i){
    var c=tc[f.fire_type]||'#5b6b7a',lb=tl[f.fire_type]||f.fire_type,st=f.season_totals;
    var rc=f.risk_score>80?'#ff382f':f.risk_score>50?'#ffae42':'#20e889';
    return'<tr style=cursor:pointer onclick=flyToForecast('+f.lat+','+f.lon+')>'+
    '<td style=font-weight:700>'+(i+1)+'</td>'+
    '<td><code style=background:var(--bg-map);padding:2px 6px;border-radius:3px;font-size:10px>'+f.grid_id+'</code></td>'+
    '<td style=font-weight:600>'+(f.site_name||f.grid_id)+'</td>'+
    '<td><span style=background:'+c+'22;color:'+c+';padding:2px 8px;border-radius:4px;font-size:10px;font-weight:700>'+lb+'</span></td>'+
    '<td style=font-weight:700;font-family:monospace;color:'+rc+'>'+f.risk_score+'</td>'+
    '<td style=font-weight:700>🔥 '+f.peak_month+'</td>'+
    '<td style=font-family:monospace>'+st.pre_monsoon+'</td>'+
    '<td style=font-family:monospace;color:#22d3ee>'+st.monsoon+'</td>'+
    '<td style=font-family:monospace;color:#ffae42>'+st.post_monsoon+'</td>'+
    '<td style=font-family:monospace;color:#a855f7>'+st.winter+'</td></tr>';
  }).join('');
}
function flyToForecast(lat,lon){if(map)map.flyTo([lat,lon],12,{animate:true,duration:0.8});}


// ============================================================
// FORECAST: Fire Type Tabs + Readiness Cards
// ============================================================
function fcRenderTypeSection(fd) {
  if (!fd || !fd.by_type) return;
  var bt = fd.by_type;
  var readiness = bt.readiness;
  var typeTotals = bt.type_totals;
  var tabs = document.getElementById('fcTypeTabs');
  var cards = document.getElementById('fcTypeReadinessCards');
  if (!tabs || !cards) return;
  var typeKeys = Object.keys(readiness);
  var typeLabels = {INDUSTRIAL_PERSISTENT:'\u{1F3ED} Industrial',AGRICULTURAL_BURNING:'\u{1F33E} Agricultural',FOREST_WILDFIRE:'\u{1F332} Forest',UNCLASSIFIED:'\u2753 Unclassified'};
  var typeColors = {INDUSTRIAL_PERSISTENT:'#a855f7',AGRICULTURAL_BURNING:'#ffd400',FOREST_WILDFIRE:'#22d3ee',UNCLASSIFIED:'#5b6b7a'};
  var h = '<button class="fc-type-tab active" data-type="all" onclick="fcFilterType(\'all\')">All Types</button>';
  typeKeys.forEach(function(k){
    h += '<button class="fc-type-tab" data-type="'+k+'" onclick="fcFilterType(\''+k+'\')">'+(typeLabels[k]||k)+'</button>';
  });
  tabs.innerHTML = h;
  h = '';
  typeKeys.forEach(function(k){
    var r = readiness[k]; var tt = typeTotals[k] || {}; var label = typeLabels[k] || k;
    h += '<div class="fc-type-card" data-type="'+k+'" style="border-left:4px solid '+r.color+'">';
    h += '<div class="fc-type-card-header"><span class="fc-type-card-label">'+label+'</span>';
    h += '<span class="fc-type-card-score" style="color:'+r.color+'">'+r.score+'</span></div>';
    h += '<div class="fc-type-card-level" style="color:'+r.color+'">'+r.level+'</div>';
    h += '<div class="fc-type-card-bar"><div class="fc-type-card-fill" style="width:'+r.score+'%;background:'+r.color+'"></div></div>';
    h += '<div class="fc-type-card-stats">'+(tt.detections||0).toLocaleString('en-IN')+' detections \u00b7 '+(tt.grids||0)+' grids</div></div>';
  });
  cards.innerHTML = h;
}
function fcFilterType(type) {
  document.querySelectorAll('.fc-type-tab').forEach(function(t){t.classList.toggle('active',t.dataset.type===type);});
  document.querySelectorAll('.fc-type-card').forEach(function(c){c.style.display=(type==='all'||c.dataset.type===type)?'':'none';});
}
function fcRenderTypeBarChart(fd) {
  var el=document.getElementById('fcTypeBarChart');if(!el||!fd||!fd.by_type)return;
  var readiness=fd.by_type.readiness;
  var typeLabels={INDUSTRIAL_PERSISTENT:'Industrial',AGRICULTURAL_BURNING:'Agricultural',FOREST_WILDFIRE:'Forest',UNCLASSIFIED:'Unclassified'};
  var typeColors={INDUSTRIAL_PERSISTENT:'#a855f7',AGRICULTURAL_BURNING:'#ffd400',FOREST_WILDFIRE:'#22d3ee',UNCLASSIFIED:'#5b6b7a'};
  var h='<div class="fc-bars"><div class="fc-bars-axis">';
  for(var i=4;i>=0;i--){h+='<span>'+Math.round(100*i/4)+'%</span>';}
  h+='</div><div class="fc-bars-body"><div class="fc-bars-grid">';
  for(var i=0;i<4;i++){h+='<div class="fc-bars-gridline"></div>';}
  h+='</div>';
  Object.keys(readiness).forEach(function(k){
    var r=readiness[k];var c=typeColors[k]||'#5b6b7a';
    h+='<div class="fc-bar-col"><div class="fc-bar-val">'+r.score+'%</div>';
    h+='<div class="fc-bar-track"><div class="fc-bar-fill" style="height:'+r.score+'%;background:'+c+'"></div></div>';
    h+='<div class="fc-bar-month">'+(typeLabels[k]||k)+'</div>';
    h+='<div class="fc-bar-avg">'+r.level+'</div></div>';
  });
  h+='</div></div>';el.innerHTML=h;
}
function fcRenderDistricts(fd) {
  var el=document.getElementById('fcDistrictCards');if(!el||!fd||!fd.districts)return;
  var typeColors={INDUSTRIAL_PERSISTENT:'#a855f7',AGRICULTURAL_BURNING:'#ffd400',FOREST_WILDFIRE:'#22d3ee',UNCLASSIFIED:'#5b6b7a'};
  var typeShort={INDUSTRIAL_PERSISTENT:'Industrial',AGRICULTURAL_BURNING:'Agri',FOREST_WILDFIRE:'Forest',UNCLASSIFIED:'Unclass.'};
  var h='';
  fd.districts.forEach(function(d){
    var r=d.readiness;var tc=typeColors[d.top_fire_type]||'#5b6b7a';var tl=typeShort[d.top_fire_type]||d.top_fire_type;
    h+='<div class="fc-district-card" style="border-top:3px solid '+r.color+'">';
    h+='<div class="fc-district-header"><div class="fc-district-name">'+d.district+'</div>';
    h+='<div class="fc-district-state">'+d.state+'</div></div>';
    h+='<div class="fc-district-score" style="color:'+r.color+'">'+r.score+'<span class="fc-district-score-label">'+r.level+'</span></div>';
    h+='<div class="fc-district-bar"><div style="width:'+r.score+'%;background:'+r.color+'"></div></div>';
    h+='<div class="fc-district-meta"><span>\u{1F4CA} '+d.n_grids+' grids</span>';
    h+='<span>\u{1F525} '+d.total_detections.toLocaleString('en-IN')+' det.</span>';
    h+='<span style="color:'+tc+'">'+tl+'</span></div>';
    h+='<div class="fc-district-meta"><span>\u{1F4C5} Peak: '+d.peak_month+'</span>';
    h+='<span>\u26A1 Avg Risk: '+d.avg_risk+'</span></div>';
    if(d.fire_type_dist&&Object.keys(d.fire_type_dist).length>0){
      var total=Object.values(d.fire_type_dist).reduce(function(a,b){return a+b;},0);
      h+='<div class="fc-district-typebar">';
      Object.keys(d.fire_type_dist).forEach(function(ft){
        var pct=(d.fire_type_dist[ft]/total*100);var c=typeColors[ft]||'#5b6b7a';
        if(pct>5)h+='<div style="width:'+pct+'%;background:'+c+'" title="'+ft+': '+d.fire_type_dist[ft]+'"></div>';
      });
      h+='</div>';
    }
    h+='</div>';
  });
  el.innerHTML=h;
}
function fcRenderAlerts(fd) {
  var el=document.getElementById('fcAlertEscalation');if(!el||!fd||!fd.escalation_alerts)return;
  var alerts=fd.escalation_alerts;
  if(alerts.length===0){el.innerHTML='<div style="text-align:center;color:var(--text-dim);padding:30px">\u2705 No threshold breaches detected.</div>';return;}
  var critical=alerts.filter(function(a){return a.severity==='CRITICAL';}).length;
  var high=alerts.filter(function(a){return a.severity==='HIGH';}).length;
  var h='<div class="fc-alert-summary">';
  if(critical>0)h+='<div class="fc-alert-count fc-alert-critical">\u{1F534} '+critical+' CRITICAL</div>';
  if(high>0)h+='<div class="fc-alert-count fc-alert-high">\u{1F7E0} '+high+' HIGH</div>';
  h+='<div class="fc-alert-count fc-alert-total">\u{1F4CB} '+alerts.length+' Total Alerts</div></div>';
  alerts.forEach(function(a){
    h+='<div class="fc-alert-card" style="border-left:4px solid '+a.color+'">';
    h+='<div class="fc-alert-header"><span class="fc-alert-icon">'+a.icon+'</span>';
    h+='<span class="fc-alert-title">'+a.title+'</span>';
    h+='<span class="fc-alert-severity" style="background:'+a.color+'">'+a.severity+'</span></div>';
    h+='<div class="fc-alert-desc">'+a.description+'</div>';
    if(a.actions&&a.actions.length>0){h+='<div class="fc-alert-actions"><strong>Recommended Actions:</strong><ul>';a.actions.forEach(function(act){h+='<li>'+act+'</li>';});h+='</ul></div>';}
    if(a.agencies&&a.agencies.length>0){h+='<div class="fc-alert-agencies">';a.agencies.forEach(function(ag){h+='<span class="fc-alert-agency">'+ag+'</span>';});h+='</div>';}
    h+='</div>';
  });
  el.innerHTML=h;
}

// ============================================================
// START (original)
// ============================================================

init();
initChatbot();
// Render forecast on load (after a small delay for DOM readiness)
setTimeout(renderForecastTab, 500);
