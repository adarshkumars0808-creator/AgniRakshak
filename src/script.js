// ============================================================
// AGNIRAKSHAK — PRECISE FIRMS GRID DASHBOARD
// ============================================================

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

// Verified, merged site layer (verified_fire_sites.csv). These are
// the ACTUAL categories/spelling produced by
// verify_and_merge_sites.py, kept separate from the aliases above
// on purpose — every row here has already been checked against
// real ESA WorldCover land cover, so it needs no further
// normalization/guessing.
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
let heatLayer = null;
let clusterLayer = null;
let satelliteLayer = null;
let fireSiteLayer = null;
let fireSiteData = [];
let riskZoneData = [];

let markerByGrid = {};


// ============================================================
// NUMBER FORMAT
// ============================================================

function num(value, decimals = 0) {

  const n = Number(value);

  if (!Number.isFinite(n)) {
    return "0";
  }

  return n.toLocaleString("en-IN", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}


// ============================================================
// CONFIDENCE
// ============================================================

function confidence01(value) {

  let n = Number(value);

  if (!Number.isFinite(n)) {
    return null;
  }

  if (n > 1) {
    n = n / 100;
  }

  return Math.max(0, Math.min(1, n));
}


function confidencePercent(value) {

  const c = confidence01(value);

  if (c === null) {
    return null;
  }

  return Math.round(c * 100);
}


// ============================================================
// FIRE TYPE NORMALIZATION
// ============================================================

function normalizeFireType(value) {

  if (
    value === null ||
    value === undefined
  ) {
    return "UNCLASSIFIED";
  }

  let v = String(value)
    .trim()
    .toUpperCase()
    .replace(/-/g, "_")
    .replace(/\//g, "_")
    .replace(/\s+/g, "_");

  const aliases = {

    INDUSTRIAL:
      "INDUSTRIAL_PERSISTENT",

    PERSISTENT:
      "INDUSTRIAL_PERSISTENT",

    INDUSTRIAL_PERSISTENT_SOURCE:
      "INDUSTRIAL_PERSISTENT",

    INDUSTRIAL_SOURCE:
      "INDUSTRIAL_PERSISTENT",

    AGRICULTURAL:
      "AGRICULTURAL_BURNING",

    CROP_BURNING:
      "AGRICULTURAL_BURNING",

    CROP_FIRE:
      "AGRICULTURAL_BURNING",

    FOREST:
      "FOREST_WILDFIRE",

    WILDFIRE:
      "FOREST_WILDFIRE",

    FOREST_FIRE:
      "FOREST_WILDFIRE",

    WILDLAND_FIRE:
      "FOREST_WILDFIRE",

    UNKNOWN:
      "UNCLASSIFIED",

    NONE:
      "UNCLASSIFIED",

    NULL:
      "UNCLASSIFIED",

    "":
      "UNCLASSIFIED",
  };

  v = aliases[v] || v;

  if (
    FIRE_TYPE_COLORS[v]
  ) {
    return v;
  }

  return "UNCLASSIFIED";
}


// ============================================================
// VALID COORDINATES
// ============================================================

function hasValidCoordinates(row) {

  const lat = Number(row.latitude);
  const lon = Number(row.longitude);

  return (
    Number.isFinite(lat) &&
    Number.isFinite(lon) &&
    lat >= 6 &&
    lat <= 38 &&
    lon >= 68 &&
    lon <= 98
  );
}


// ============================================================
// REAL FIRMS CELL
// ============================================================
//
// IMPORTANT:
//
// We DO NOT use recent_activity here.
//
// We DO NOT use detections_30d.
//
// We DO NOT use detections_90d.
//
// The supplied risk_predictions.csv already contains
// actual FIRMS-supported grids.
//
// Every row in the supplied CSV has total_detections >= 1.
//
// Therefore all valid rows are genuine active FIRMS grids.
// ============================================================

function isActiveFirmsCell(row) {

  const total =
    Number(row.total_detections);

  return (
    Number.isFinite(total) &&
    total > 0
  );
}


// ============================================================
// LOAD CSV
// ============================================================

async function loadCSV(path) {

  const response =
    await fetch(path);

  if (!response.ok) {

    throw new Error(
      `${path} -> HTTP ${response.status}`
    );
  }

  const text =
    await response.text();

  return Papa.parse(
    text,
    {
      header: true,
      dynamicTyping: true,
      skipEmptyLines: true,
    }
  ).data;
}


// ============================================================
// CSV FALLBACK
// ============================================================

async function loadCSVWithFallback(
  candidates
) {

  let lastError = null;

  for (
    const path of candidates
  ) {

    try {

      return await loadCSV(path);

    } catch (error) {

      lastError = error;
    }
  }

  throw lastError;
}


// ============================================================
// INIT
// ============================================================

async function init() {

  // ==========================================================
  // STREAMLIT MODE
  // ==========================================================

  if (
    window.THERMOSCOPE_DATA
  ) {

    gridData =
      window.THERMOSCOPE_DATA.gridData || [];

    dailyData =
      window.THERMOSCOPE_DATA.dailyData || [];

    fireSiteData =
      window.THERMOSCOPE_DATA.fireSiteData || [];

    riskZoneData =
      window.THERMOSCOPE_DATA.riskZoneData || [];

  }


  // ==========================================================
  // STANDALONE MODE
  // ==========================================================

  else {

    try {

      gridData =
        await loadCSVWithFallback([
          "../data/processed/risk_predictions.csv",
          "data/processed/risk_predictions.csv",
          "data/risk_predictions.csv",
        ]);


      dailyData =
        await loadCSVWithFallback([
          "../data/processed/daily_activity.csv",
          "data/processed/daily_activity.csv",
          "data/daily_activity.csv",
        ]);


      // ------------------------------------------------------
      // FIRE TYPE CSV
      // ------------------------------------------------------

      try {

        const fireTypes =
          await loadCSVWithFallback([
            "../data/processed/fire_type_predictions.csv",
            "data/processed/fire_type_predictions.csv",
            "data/fire_type_predictions.csv",
          ]);


        const byGrid = {};


        fireTypes.forEach(
          row => {

            const id =
              String(
                row.grid_id ?? ""
              ).trim();

            if (id) {

              byGrid[id] = row;
            }
          }
        );


        gridData.forEach(
          row => {

            const id =
              String(
                row.grid_id ?? ""
              ).trim();

            const fire =
              byGrid[id];

            if (!fire) {
              return;
            }

            row.fire_type =
              fire.fire_type;

            row.fire_type_confidence =
              fire.fire_type_confidence;

            row.fire_type_reason =
              fire.fire_type_reason;

            row.coordinate_source =
              fire.coordinate_source;

            row.display_latitude =
              fire.display_latitude;

            row.display_longitude =
              fire.display_longitude;

            row.display_site_name =
              fire.display_site_name;

            row.display_site_type =
              fire.display_site_type;
          }
        );

      } catch (error) {

        console.warn(
          "Fire-type CSV unavailable.",
          error
        );
      }


      // ------------------------------------------------------
      // VERIFIED, MERGED FIRE SITES (satellite/land-cover
      // checked — this is what the Fire Type map layer uses)
      // ------------------------------------------------------

      try {

        fireSiteData =
          await loadCSVWithFallback([
            "../data/processed/verified_fire_sites.csv",
            "data/processed/verified_fire_sites.csv",
            "data/verified_fire_sites.csv",
          ]);

      } catch (error) {

        console.warn(
          "verified_fire_sites.csv unavailable — Fire Type layer will be empty.",
          error
        );

        fireSiteData = [];
      }


      // ------------------------------------------------------
      // REGIONAL RISK ZONES (aggregated risk_predictions.csv —
      // this is what the Risk Level map layer's discrete
      // markers use; the heatmap still uses full-resolution
      // gridData)
      // ------------------------------------------------------

      try {

        riskZoneData =
          await loadCSVWithFallback([
            "../data/processed/risk_zones.csv",
            "data/processed/risk_zones.csv",
            "data/risk_zones.csv",
          ]);

      } catch (error) {

        console.warn(
          "risk_zones.csv unavailable — falling back to raw grid markers.",
          error
        );

        riskZoneData = [];
      }

    } catch (error) {

      const element =
        document.getElementById(
          "dataReadout"
        );

      if (element) {

        element.textContent =
          "Failed to load dashboard data.";
      }

      console.error(error);

      return;
    }
  }


  // ==========================================================
  // NORMALIZE DATA
  // ==========================================================

  gridData.forEach(
    row => {

      row.grid_id =
        String(
          row.grid_id ?? ""
        ).trim();


      row.risk_level =
        String(
          row.risk_level ?? "LOW"
        )
        .trim()
        .toUpperCase();


      row.fire_type =
        normalizeFireType(
          row.fire_type
        );


      row.latitude =
        Number(row.latitude);


      row.longitude =
        Number(row.longitude);


      row.total_detections =
        Number(
          row.total_detections
        ) || 0;


      row.active_days =
        Number(
          row.active_days
        ) || 0;


      row.avg_frp =
        Number(
          row.avg_frp
        ) || 0;


      row.max_frp =
        Number(
          row.max_frp
        ) || 0;


      row.recurrence_ratio =
        Number(
          row.recurrence_ratio
        ) || 0;


      row.persistent_months =
        Number(
          row.persistent_months
        ) || 0;


      row.detections_30d =
        Number(
          row.detections_30d
        ) || 0;


      row.detections_90d =
        Number(
          row.detections_90d
        ) || 0;


      row.risk_score =
        Number(
          row.risk_score
        ) || 0;


      row.fire_type_confidence =
        Number(
          row.fire_type_confidence
        ) || 0;


      // --------------------------------------------------
      // GIS-CONFIRMED REAL SITE
      // --------------------------------------------------
      // classify_fire_type.py snaps a grid cell to a real
      // OSM industrial/agricultural/forest site when one is
      // close enough. coordinate_source tells us whether
      // that happened, or whether this row is still just a
      // raw 5km FIRMS grid cell with a pattern-based guess.

      const source =
        String(
          row.coordinate_source ?? ""
        ).toUpperCase();

      row.is_gis_confirmed =
        source.includes("REAL_GIS");

      const dLat =
        Number(row.display_latitude);

      const dLon =
        Number(row.display_longitude);

      const hasDisplayCoords =
        Number.isFinite(dLat) &&
        Number.isFinite(dLon);

      // Plot at the real site's coordinate when we have one,
      // otherwise fall back to the raw grid centroid.
      row.map_latitude =
        row.is_gis_confirmed && hasDisplayCoords
          ? dLat
          : row.latitude;

      row.map_longitude =
        row.is_gis_confirmed && hasDisplayCoords
          ? dLon
          : row.longitude;

      row.display_site_name =
        row.display_site_name || "";

      row.display_site_type =
        row.display_site_type || "";
    }
  );


  // ==========================================================
  // PRECISE ACTIVE GRID FILTER
  // ==========================================================
  //
  // Only remove:
  //
  // 1. Missing grid ID
  // 2. Invalid coordinates
  // 3. Zero FIRMS detections
  //
  // NO RECENT-DATE FILTER.
  // ==========================================================

  const originalCount =
    gridData.length;


  gridData =
    gridData.filter(
      row => {

        if (!row.grid_id) {
          return false;
        }

        if (
          !hasValidCoordinates(row)
        ) {
          return false;
        }

        if (
          !isActiveFirmsCell(row)
        ) {
          return false;
        }

        return true;
      }
    );


  console.log(
    "Original prediction rows:",
    originalCount
  );


  console.log(
    "Actual FIRMS active grids:",
    gridData.length
  );


  // ==========================================================
  // FIRE TYPE COUNTS
  // ==========================================================

  const distribution =
    gridData.reduce(
      (acc, row) => {

        const type =
          normalizeFireType(
            row.fire_type
          );

        acc[type] =
          (acc[type] || 0) + 1;

        return acc;

      },
      {}
    );


  console.log(
    "FIRMS fire-type distribution:",
    distribution
  );


  // ==========================================================
  // UPDATE DATA SOURCE CARD
  // ==========================================================

  const readout =
    document.getElementById(
      "dataReadout"
    );


  if (readout) {

    readout.innerHTML =
      `● risk_predictions.csv<br>
       ${gridData.length.toLocaleString("en-IN")}
       active FIRMS grid cells shown`;
  }


  // ==========================================================
  // NORMALIZE FIRE SITE DATA (verified_fire_sites.csv)
  // ==========================================================

  fireSiteData.forEach(
    row => {

      row.fire_type =
        String(row.fire_type ?? "")
          .trim()
          .toUpperCase();

      row.latitude = Number(row.latitude);
      row.longitude = Number(row.longitude);
      row.total_detections = Number(row.total_detections) || 0;
      row.n_grids_merged = Number(row.n_grids_merged) || 1;
      row.site_name = row.site_name || "";
      row.verification_reason = row.verification_reason || "";
      row.landcover_class = row.landcover_class || "";

      row.named_facility_distance_km =
        row.named_facility_distance_km != null && row.named_facility_distance_km !== ""
          ? Number(row.named_facility_distance_km)
          : null;
    }
  );

  console.log(
    `Verified fire sites loaded: ${fireSiteData.length} ` +
    `(land-cover checked, ${fireSiteData.reduce((s, r) => s + r.n_grids_merged, 0)} raw grid cells merged into them)`
  );


  // ==========================================================
  // NORMALIZE RISK ZONE DATA (risk_zones.csv)
  // ==========================================================

  riskZoneData.forEach(
    row => {

      row.risk_level =
        String(row.risk_level ?? "")
          .trim()
          .toUpperCase();

      row.latitude = Number(row.latitude);
      row.longitude = Number(row.longitude);
      row.risk_score = Number(row.risk_score) || 0;
      row.avg_risk_score = Number(row.avg_risk_score) || 0;
      row.total_detections = Number(row.total_detections) || 0;
      row.n_grids_merged = Number(row.n_grids_merged) || 1;
    }
  );

  console.log(
    `Regional risk zones loaded: ${riskZoneData.length} ` +
    `(from ${riskZoneData.reduce((s, r) => s + r.n_grids_merged, 0)} raw grid cells)`
  );


  // ==========================================================
  // RENDER
  // ==========================================================

  renderMetrics();

  renderTop10();

  initMap();

  setDefaultDateRange();

  renderChart();

  bindControls();

  rebuildLayers();
}


// ============================================================
// METRICS
// ============================================================

function renderMetrics() {

  const total =
    gridData.length;


  const totalDetections =
    gridData.reduce(
      (sum, row) =>
        sum +
        Number(
          row.total_detections || 0
        ),
      0
    );


  const critical =
    gridData.filter(
      row =>
        row.risk_level === "CRITICAL"
    ).length;


  const high =
    gridData.filter(
      row =>
        row.risk_level === "HIGH"
    ).length;


  const avgFrp =
    total > 0
      ? gridData.reduce(
          (sum, row) =>
            sum +
            Number(
              row.avg_frp || 0
            ),
          0
        ) / total
      : 0;


  const mTotalCells =
    document.getElementById(
      "mTotalCells"
    );

  const mTotalDetections =
    document.getElementById(
      "mTotalDetections"
    );

  const mCritical =
    document.getElementById(
      "mCritical"
    );

  const mHigh =
    document.getElementById(
      "mHigh"
    );

  const mAvgFrp =
    document.getElementById(
      "mAvgFrp"
    );


  if (mTotalCells) {

    mTotalCells.textContent =
      num(total);
  }


  if (mTotalDetections) {

    mTotalDetections.textContent =
      num(totalDetections);
  }


  if (mCritical) {

    mCritical.textContent =
      num(critical);
  }


  if (mHigh) {

    mHigh.textContent =
      num(high);
  }


  if (mAvgFrp) {

    mAvgFrp.textContent =
      num(avgFrp, 2);
  }
}


// ============================================================
// TOP 10
// ============================================================

function renderTop10() {

  const top10 =
    [...gridData]
      .sort(
        (a, b) =>
          Number(b.risk_score) -
          Number(a.risk_score)
      )
      .slice(0, 10);


  const element =
    document.getElementById(
      "top10List"
    );


  if (!element) {
    return;
  }


  element.innerHTML =
    top10
      .map(
        (row, index) => `

        <div
          class="top10-row"
          data-grid="${row.grid_id}"
        >

          <span>

            <span class="top10-rank">
              #${index + 1}
            </span>

            ${row.grid_id}

          </span>

          <span class="top10-score">
            ${Number(
              row.risk_score
            ).toFixed(1)}
          </span>

        </div>
      `
      )
      .join("");


  element
    .querySelectorAll(
      ".top10-row"
    )
    .forEach(
      row => {

        row.addEventListener(
          "click",
          () =>
            flyToGrid(
              row.dataset.grid
            )
        );
      }
    );
}


// ============================================================
// MAP
// ============================================================

function initMap() {

  map =
    L.map(
      "map",
      {
        preferCanvas: true,
      }
    )
    .setView(
      [28.5, 78.5],
      7
    );


  L.tileLayer(
    "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png",
    {
      attribution:
        "&copy; OpenStreetMap, &copy; CARTO",

      maxZoom: 19,
    }
  ).addTo(map);


  // Real satellite imagery (Esri World Imagery — free, no API key).
  // Toggled on/off from the sidebar; the dark CARTO layer above
  // stays as the base so labels/roads remain visible under it.
  satelliteLayer =
    L.tileLayer(
      "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
      {
        attribution:
          "Tiles &copy; Esri — Source: Esri, Maxar, Earthstar Geographics",

        maxZoom: 19,
      }
    );


  heatLayer =
    L.heatLayer(
      [],
      {
        radius: 18,
        blur: 22,
        maxZoom: 10,

        gradient: {
          0.2: "#20e889",
          0.5: "#ffae42",
          0.75: "#ff6b1a",
          1.0: "#ff382f",
        },
      }
    );


  clusterLayer =
    L.markerClusterGroup(
      {
        chunkedLoading: true,

        maxClusterRadius: 55,

        disableClusteringAtZoom: 12,

        spiderfyOnMaxZoom: true,

        showCoverageOnHover: false,
      }
    );


  fireSiteLayer =
    L.markerClusterGroup(
      {
        chunkedLoading: true,

        maxClusterRadius: 40,

        disableClusteringAtZoom: 13,

        spiderfyOnMaxZoom: true,

        showCoverageOnHover: false,
      }
    );


  heatLayer.addTo(map);

  clusterLayer.addTo(map);
}


// ============================================================
// RISK FILTER
// ============================================================

function activeRiskLevels() {

  return [
    ...document.querySelectorAll(
      ".risk-toggle:checked"
    ),
  ]
  .map(
    checkbox =>
      String(
        checkbox.value
      )
      .trim()
      .toUpperCase()
  );
}


// ============================================================
// FIRE TYPE FILTER
// ============================================================

function activeFireTypes() {

  return [
    ...document.querySelectorAll(
      ".type-toggle:checked"
    ),
  ]
  .map(
    checkbox =>
      normalizeFireType(
        checkbox.value
      )
  );
}


// ============================================================
// ONLY-REAL-SITES TOGGLE
// ============================================================

function onlyRealSitesEnabled() {

  const el =
    document.getElementById(
      "onlyRealSites"
    );

  // Default to true if the control isn't in the page yet.
  return el ? el.checked : true;
}


// ============================================================
// COLOR MODE
// ============================================================

function colorMode() {

  const selected =
    document.querySelector(
      'input[name="colorMode"]:checked'
    );


  return selected
    ? selected.value
    : "risk";
}


// ============================================================
// COLOR
// ============================================================

function colorFor(
  row,
  mode
) {

  if (
    mode === "fireType"
  ) {

    return (
      FIRE_TYPE_COLORS[
        normalizeFireType(
          row.fire_type
        )
      ] ||
      FIRE_TYPE_COLORS.UNCLASSIFIED
    );
  }


  return (
    RISK_COLORS[
      String(
        row.risk_level
      )
      .trim()
      .toUpperCase()
    ] ||
    "#7890a8"
  );
}


// ============================================================
// FIRE SITE LAYER (verified_fire_sites.csv — the real,
// land-cover-checked, merged sites)
// ============================================================

function activeSiteTypes() {

  return [
    ...document.querySelectorAll(
      ".type-toggle:checked"
    ),
  ]
  .map(
    checkbox =>
      String(checkbox.value)
        .trim()
        .toUpperCase()
  );
}


function renderFireSiteLayer() {

  if (!fireSiteLayer) {
    return;
  }

  fireSiteLayer.clearLayers();

  const types =
    new Set(
      activeSiteTypes()
    );

  const filtered =
    fireSiteData.filter(
      row => types.has(row.fire_type)
    );


  const label =
    document.getElementById(
      "gridCountLabel"
    );

  if (label) {

    const totalMergedGrids =
      filtered.reduce(
        (s, r) => s + (r.n_grids_merged || 1),
        0
      );

    label.textContent =
      `SHOWING ${filtered.length.toLocaleString("en-IN")} VERIFIED SITES ` +
      `(from ${totalMergedGrids.toLocaleString("en-IN")} raw grid cells) · COLOR: FIRE TYPE`;
  }


  filtered.forEach(
    row => {

      const lat = Number(row.latitude);
      const lon = Number(row.longitude);

      if (!Number.isFinite(lat) || !Number.isFinite(lon)) {
        return;
      }

      const color =
        SITE_TYPE_COLORS[row.fire_type] || "#7890a8";

      const label =
        SITE_TYPE_LABELS[row.fire_type] || row.fire_type;

      const radius =
        6 + Math.min(10, Math.log1p(row.total_detections));

      const marker =
        L.circleMarker(
          [lat, lon],
          {
            radius,
            color,
            weight: 2,
            fillColor: color,
            fillOpacity: 0.55,
          }
        );

      const title =
        row.site_name && row.site_name.trim()
          ? row.site_name
          : "Unnamed facility";

      const mergedNote =
        row.n_grids_merged > 1
          ? `<br><span style="color:#94a6b8;">Merged from ${row.n_grids_merged} nearby grid cells</span>`
          : "";

      const nameNote =
        row.site_name && row.site_name.trim()
          ? (
              row.named_facility_distance_km > 0.5
                ? `<br><span style="color:#94a6b8;">Nearest named facility on record, ~${row.named_facility_distance_km.toFixed(1)}km away</span>`
                : ""
            )
          : `<br><span style="color:#94a6b8;">No named facility on record nearby — verified by land cover + industrial context only</span>`;

      marker.bindPopup(`
        <div style="min-width:230px; font-family:Arial,sans-serif; line-height:1.5;">
          <b>${title}</b>
          <br><span style="color:${color};">${label}</span>
          ${mergedNote}
          ${nameNote}
          <hr>
          <b>Historical Detections:</b> ${row.total_detections.toLocaleString("en-IN")}<br>
          <b>Land Cover:</b> ${row.landcover_class.replace(/_/g, " ")}<br>
          <b>Coordinate:</b> ${lat.toFixed(4)}, ${lon.toFixed(4)}
        </div>
      `);

      marker.on("click", () => showSiteIntel(row));

      fireSiteLayer.addLayer(marker);
    }
  );

  if (!map.hasLayer(fireSiteLayer)) {
    fireSiteLayer.addTo(map);
  }
}


function showSiteIntel(row) {

  const element =
    document.getElementById("selectedGrid");

  if (!element) {
    return;
  }

  const color =
    SITE_TYPE_COLORS[row.fire_type] || "#7890a8";

  const label =
    SITE_TYPE_LABELS[row.fire_type] || row.fire_type;

  const title =
    row.site_name && row.site_name.trim()
      ? row.site_name
      : "Unnamed facility";

  const nameNote =
    row.site_name && row.site_name.trim()
      ? (
          row.named_facility_distance_km > 0.5
            ? `Nearest named facility on record — ~${row.named_facility_distance_km.toFixed(1)}km away. This is the closest known name, not necessarily the exact source.`
            : "Name matched directly to this location."
        )
      : "No named facility on record within 25km — verified by land cover + industrial context signals only, not a name match.";

  element.innerHTML = `
    <div class="grid-id">${title}</div>

    <div style="color:#3cff9a; font-size:10.5px; margin-bottom:8px;">
      ✓ Land-cover verified${row.n_grids_merged > 1 ? ` · merged from ${row.n_grids_merged} grid cells` : ""}
    </div>

    <div class="type-label" style="border:1px solid ${color}; color:${color};">
      ${label}
    </div>

    <div class="intel-row"><span>Total Detections</span><strong>${row.total_detections.toLocaleString("en-IN")}</strong></div>
    <div class="intel-row"><span>Latitude</span><strong>${Number(row.latitude).toFixed(6)}</strong></div>
    <div class="intel-row"><span>Longitude</span><strong>${Number(row.longitude).toFixed(6)}</strong></div>
    <div class="intel-row"><span>Land Cover</span><strong>${row.landcover_class.replace(/_/g, " ")}</strong></div>
    <div class="intel-row"><span>Grid Cells Merged</span><strong>${row.n_grids_merged}</strong></div>
    ${row.risk_score ? `<div class="intel-row"><span>Risk Score</span><strong>${Number(row.risk_score).toFixed(1)}</strong></div>` : ""}

    <div class="intel-reason">${row.verification_reason || ""}</div>
    <div class="intel-reason">${nameNote}</div>
  `;
}


// ============================================================
// VISIBLE CELLS
// ============================================================

function getVisibleCells() {

  const levels =
    new Set(
      activeRiskLevels()
    );


  // Fire-type filtering now happens on the separate, verified
  // fireSiteData/renderFireSiteLayer() path — the risk layer only
  // needs the risk-level filter.

  return gridData.filter(
    row => {

      const risk =
        String(
          row.risk_level
        )
        .trim()
        .toUpperCase();


      return levels.has(risk);
    }
  );
}


// ============================================================
// REBUILD MAP
// ============================================================

function rebuildLayers() {

  if (!map) {
    return;
  }


  const mode =
    colorMode();


  // ============================================================
  // FIRE TYPE MODE — verified, merged real sites only
  // (verified_fire_sites.csv). Completely separate data source
  // and layer from the risk heatmap/markers below.
  // ============================================================

  if (mode === "fireType") {

    if (clusterLayer && map.hasLayer(clusterLayer)) {
      map.removeLayer(clusterLayer);
    }

    if (heatLayer && map.hasLayer(heatLayer)) {
      map.removeLayer(heatLayer);
    }

    renderFireSiteLayer();

    return;
  }


  // ============================================================
  // RISK MODE
  // ============================================================

  if (fireSiteLayer && map.hasLayer(fireSiteLayer)) {
    map.removeLayer(fireSiteLayer);
  }

  const heatOn =
    document.getElementById("lyrHeat");

  const markersOn =
    document.getElementById("lyrMarkers");

  if (heatLayer && (!heatOn || heatOn.checked) && !map.hasLayer(heatLayer)) {
    heatLayer.addTo(map);
  }

  if (clusterLayer && (!markersOn || markersOn.checked) && !map.hasLayer(clusterLayer)) {
    clusterLayer.addTo(map);
  }


  const filtered =
    getVisibleCells();


  console.log(
    "VISIBLE FIRMS GRID CELLS:",
    filtered.length
  );


  // ==========================================================
  // COUNT LABEL
  // ==========================================================

  const label =
    document.getElementById(
      "gridCountLabel"
    );


  if (label) {

    const zoneCount =
      riskZoneData.length
        ? riskZoneData.filter(
            z => new Set(activeRiskLevels()).has(z.risk_level)
          ).length
        : filtered.length;

    label.textContent =
      riskZoneData.length
        ? `SHOWING ${zoneCount.toLocaleString("en-IN")} REGIONAL RISK ZONES ` +
          `(from ${filtered.length.toLocaleString("en-IN")} raw grid cells) · COLOR: RISK LEVEL`
        : `SHOWING ${filtered.length.toLocaleString("en-IN")} GRID CELLS · COLOR: RISK LEVEL`;
  }


  // ==========================================================
  // HEATMAP
  // ==========================================================

  const heatPoints =
    filtered.map(
      row => {

        const risk =
          Math.max(
            0,
            Math.min(
              100,
              Number(
                row.risk_score
              ) || 0
            )
          );


        const intensity =
          Math.max(
            0.18,
            risk / 100
          );


        return [
          Number(row.map_latitude ?? row.latitude),
          Number(row.map_longitude ?? row.longitude),
          intensity,
        ];
      }
    );


  heatLayer.setLatLngs(
    heatPoints
  );


  // ==========================================================
  // MARKERS (regional risk zones — risk_zones.csv, NOT the raw
  // 26,891 grid cells; the heatmap above still uses those)
  // ==========================================================

  clusterLayer.clearLayers();

  markerByGrid = {};

  const levels =
    new Set(activeRiskLevels());

  const visibleZones =
    riskZoneData.length
      ? riskZoneData.filter(
          zone => levels.has(zone.risk_level)
        )
      : filtered;   // fallback: risk_zones.csv not generated yet


  visibleZones.forEach(
    zone => {

      const lat = Number(zone.latitude);
      const lon = Number(zone.longitude);

      if (!Number.isFinite(lat) || !Number.isFinite(lon)) {
        return;
      }

      const color =
        RISK_COLORS[zone.risk_level] || "#7890a8";

      let radius = 6;

      if (zone.risk_level === "CRITICAL") radius = 11;
      else if (zone.risk_level === "HIGH") radius = 9;
      else if (zone.risk_level === "MODERATE") radius = 7;
      else radius = 5;

      const marker =
        L.circleMarker(
          [lat, lon],
          {
            radius,
            color,
            weight: 2,
            fillColor: color,
            fillOpacity: 0.7,
          }
        );

      const mergedNote =
        zone.n_grids_merged > 1
          ? `<br><span style="color:#94a6b8;">Regional zone — ${zone.n_grids_merged} grid cells merged</span>`
          : "";

      marker.bindPopup(`
        <div style="min-width:220px; font-family:Arial,sans-serif; line-height:1.5;">
          <b>${zone.zone_id}</b>
          <br><span style="color:${color};">${zone.risk_level} RISK</span>
          ${mergedNote}
          <hr>
          <b>Worst Cell Risk Score:</b> ${Number(zone.risk_score).toFixed(1)}<br>
          <b>Regional Avg Risk Score:</b> ${Number(zone.avg_risk_score).toFixed(1)}<br>
          <b>Total Detections:</b> ${num(zone.total_detections)}<br>
          <b>Coordinate:</b> ${lat.toFixed(4)}, ${lon.toFixed(4)}
        </div>
      `);

      marker.bindTooltip(
        `${zone.zone_id} | ${zone.risk_level}`,
        { direction: "top" }
      );

      marker.on("click", () => showRiskZoneIntel(zone));

      markerByGrid[zone.zone_id] = marker;

      clusterLayer.addLayer(marker);
    }
  );
}


function showRiskZoneIntel(zone) {

  const element =
    document.getElementById("selectedGrid");

  if (!element) {
    return;
  }

  const color =
    RISK_COLORS[zone.risk_level] || "#7890a8";

  element.innerHTML = `
    <div class="grid-id">${zone.zone_id}</div>

    ${
      zone.n_grids_merged > 1
        ? `<div style="color:#94a6b8; font-size:10.5px; margin-bottom:8px;">Regional zone · ${zone.n_grids_merged} raw grid cells merged (~${zone.region_radius_km || 30}km)</div>`
        : ""
    }

    <div class="risk-label" style="border-color:${color}; color:${color};">
      ${zone.risk_level} RISK
    </div>

    <div class="intel-row"><span>Worst Cell Risk Score</span><strong>${Number(zone.risk_score).toFixed(1)}</strong></div>
    <div class="intel-row"><span>Regional Avg Risk Score</span><strong>${Number(zone.avg_risk_score).toFixed(1)}</strong></div>
    <div class="intel-row"><span>Latitude</span><strong>${Number(zone.latitude).toFixed(6)}</strong></div>
    <div class="intel-row"><span>Longitude</span><strong>${Number(zone.longitude).toFixed(6)}</strong></div>
    <div class="intel-row"><span>Total Detections</span><strong>${num(zone.total_detections)}</strong></div>
    <div class="intel-row"><span>Avg FRP</span><strong>${zone.avg_frp != null ? Number(zone.avg_frp).toFixed(2) + " MW" : "—"}</strong></div>
    <div class="intel-row"><span>Grid Cells Merged</span><strong>${zone.n_grids_merged}</strong></div>
  `;
}


// ============================================================
// FLY TO GRID
// ============================================================

function flyToGrid(
  gridId
) {

  const row =
    gridData.find(
      item =>
        String(
          item.grid_id
        ) === String(gridId)
    );


  if (!row) {
    return;
  }


  map.setView(
    [
      Number(row.map_latitude ?? row.latitude),
      Number(row.map_longitude ?? row.longitude),
    ],
    12,
    {
      animate: true,
    }
  );


  const marker =
    markerByGrid[
      row.grid_id
    ];


  if (marker) {

    marker.openPopup();
  }


  showGridIntel(row);
}


// ============================================================
// SELECTED GRID INTELLIGENCE
// ============================================================

function showGridIntel(
  row
) {

  const riskLevel =
    String(
      row.risk_level
    )
    .trim()
    .toUpperCase();


  const riskColor =
    RISK_COLORS[
      riskLevel
    ] ||
    "#7890a8";


  const type =
    normalizeFireType(
      row.fire_type
    );


  const typeColor =
    FIRE_TYPE_COLORS[
      type
    ] ||
    FIRE_TYPE_COLORS.UNCLASSIFIED;


  const typeLabel =
    FIRE_TYPE_LABELS[
      type
    ] ||
    "Unclassified";


  const confidence =
    confidencePercent(
      row.fire_type_confidence
    );


  const reason =
    row.fire_type_reason ||
    "No classification reason available.";


  const element =
    document.getElementById(
      "selectedGrid"
    );


  if (!element) {
    return;
  }


  element.innerHTML = `

    <div class="grid-id">
      ${row.display_site_name || row.grid_id}
    </div>

    ${
      row.is_gis_confirmed
        ? `<div style="color:#3cff9a; font-size:10.5px; margin-bottom:8px;">✓ GIS-confirmed real site${row.display_site_type ? ` · ${row.display_site_type}` : ""}</div>`
        : `<div style="color:#94a6b8; font-size:10.5px; margin-bottom:8px;">Pattern-based classification (no matched real-world site)</div>`
    }

    <div
      class="risk-label"
      style="
        border-color:${riskColor};
        color:${riskColor};
      "
    >
      ${riskLevel} RISK
    </div>

    <div
      class="type-label"
      style="
        border:1px solid ${typeColor};
        color:${typeColor};
      "
    >
      ${typeLabel}

      ${
        confidence !== null
          ? ` · ${confidence}% confidence`
          : ""
      }
    </div>


    <div class="intel-row">
      <span>Risk Score</span>
      <strong>
        ${Number(
          row.risk_score
        ).toFixed(1)}
      </strong>
    </div>


    <div class="intel-row">
      <span>Latitude</span>
      <strong>
        ${Number(
          row.map_latitude ?? row.latitude
        ).toFixed(6)}
      </strong>
    </div>


    <div class="intel-row">
      <span>Longitude</span>
      <strong>
        ${Number(
          row.map_longitude ?? row.longitude
        ).toFixed(6)}
      </strong>
    </div>


    <div class="intel-row">
      <span>Total Detections</span>
      <strong>
        ${num(
          row.total_detections
        )}
      </strong>
    </div>


    <div class="intel-row">
      <span>Active Days</span>
      <strong>
        ${num(
          row.active_days
        )}
      </strong>
    </div>


    <div class="intel-row">
      <span>Avg FRP</span>
      <strong>
        ${Number(
          row.avg_frp
        ).toFixed(2)}
        MW
      </strong>
    </div>


    <div class="intel-row">
      <span>Max FRP</span>
      <strong>
        ${Number(
          row.max_frp
        ).toFixed(2)}
        MW
      </strong>
    </div>


    <div class="intel-row">
      <span>Recurrence Ratio</span>
      <strong>
        ${
          (
            Number(
              row.recurrence_ratio
            ) * 100
          ).toFixed(0)
        }%
      </strong>
    </div>


    <div class="intel-row">
      <span>Persistent Months</span>
      <strong>
        ${num(
          row.persistent_months
        )}
      </strong>
    </div>


    <div class="intel-row">
      <span>Detections (30d)</span>
      <strong>
        ${num(
          row.detections_30d
        )}
      </strong>
    </div>


    <div class="intel-row">
      <span>Detections (90d)</span>
      <strong>
        ${num(
          row.detections_90d
        )}
      </strong>
    </div>


    <div class="intel-reason">
      ${reason}
    </div>

  `;
}


// ============================================================
// DATE RANGE
// ============================================================

function setDefaultDateRange() {

  if (!dailyData.length) {
    return;
  }


  const validDates =
    dailyData
      .map(row => row.date)
      .filter(Boolean)
      .sort();


  if (!validDates.length) {
    return;
  }


  const last =
    validDates[
      validDates.length - 1
    ];


  const lastDate =
    new Date(last);


  const from =
    new Date(lastDate);


  from.setDate(
    from.getDate() - 60
  );


  const dateFrom =
    document.getElementById(
      "dateFrom"
    );


  const dateTo =
    document.getElementById(
      "dateTo"
    );


  if (dateFrom) {

    dateFrom.value =
      from.toISOString()
        .slice(0, 10);
  }


  if (dateTo) {

    dateTo.value =
      last;
  }
}


// ============================================================
// CHART
// ============================================================

function renderChart() {

  if (!dailyData.length) {
    return;
  }


  const fromEl =
    document.getElementById(
      "dateFrom"
    );


  const toEl =
    document.getElementById(
      "dateTo"
    );


  const svg =
    document.getElementById(
      "chart"
    );


  if (
    !fromEl ||
    !toEl ||
    !svg
  ) {
    return;
  }


  const from =
    fromEl.value;


  const to =
    toEl.value;


  const rows =
    dailyData.filter(
      row =>
        row.date >= from &&
        row.date <= to
    );


  svg.innerHTML = "";


  if (!rows.length) {
    return;
  }


  const w = 900;
  const h = 200;

  const padL = 34;
  const padR = 10;
  const padT = 10;
  const padB = 24;


  const maxV =
    Math.max(
      ...rows.map(
        row =>
          Number(
            row.detections
          ) || 0
      ),
      1
    );


  const stepX =
    (w - padL - padR) /
    Math.max(
      1,
      rows.length - 1
    );


  const ns =
    "http://www.w3.org/2000/svg";


  const ticks = 4;


  for (
    let i = 0;
    i <= ticks;
    i++
  ) {

    const v =
      Math.round(
        (maxV / ticks) * i
      );


    const y =
      h -
      padB -
      (v / maxV) *
      (h - padT - padB);


    const line =
      document.createElementNS(
        ns,
        "line"
      );


    line.setAttribute(
      "x1",
      padL
    );

    line.setAttribute(
      "x2",
      w - padR
    );

    line.setAttribute(
      "y1",
      y
    );

    line.setAttribute(
      "y2",
      y
    );

    line.setAttribute(
      "stroke",
      "#1c2530"
    );

    line.setAttribute(
      "stroke-width",
      "1"
    );


    svg.appendChild(line);


    const text =
      document.createElementNS(
        ns,
        "text"
      );


    text.setAttribute(
      "x",
      4
    );

    text.setAttribute(
      "y",
      y + 4
    );

    text.setAttribute(
      "fill",
      "#4a5563"
    );

    text.setAttribute(
      "font-size",
      "9"
    );


    text.textContent =
      v;


    svg.appendChild(text);
  }


  const pts =
    rows.map(
      (row, i) => [

        padL +
        i * stepX,

        h -
        padB -
        (
          (Number(
            row.detections
          ) || 0) /
          maxV
        ) *
        (h - padT - padB),

      ]
    );


  const path =
    "M" +
    pts
      .map(
        point =>
          point.join(",")
      )
      .join(" L");


  const pathEl =
    document.createElementNS(
      ns,
      "path"
    );


  pathEl.setAttribute(
    "d",
    path
  );


  pathEl.setAttribute(
    "fill",
    "none"
  );


  pathEl.setAttribute(
    "stroke",
    "#ff493d"
  );


  pathEl.setAttribute(
    "stroke-width",
    "2"
  );


  svg.appendChild(
    pathEl
  );


  const labelEvery =
    Math.max(
      1,
      Math.round(
        rows.length / 8
      )
    );


  rows.forEach(
    (row, i) => {

      if (
        i % labelEvery === 0 ||
        i === rows.length - 1
      ) {

        const text =
          document.createElementNS(
            ns,
            "text"
          );


        text.setAttribute(
          "x",
          pts[i][0] - 12
        );


        text.setAttribute(
          "y",
          h - 6
        );


        text.setAttribute(
          "fill",
          "#7b8794"
        );


        text.setAttribute(
          "font-size",
          "9"
        );


        text.textContent =
          String(
            row.date
          ).slice(5);


        svg.appendChild(
          text
        );
      }
    }
  );
}


// ============================================================
// CONTROLS
// ============================================================

function bindControls() {

  const satelliteEl =
    document.getElementById(
      "lyrSatellite"
    );

  if (satelliteEl) {
    satelliteEl.addEventListener(
      "change",
      event => {

        if (!satelliteLayer) {
          return;
        }

        if (event.target.checked) {
          satelliteLayer.addTo(map);
        } else {
          map.removeLayer(satelliteLayer);
        }
      }
    );
  }


  document
    .querySelectorAll(
      ".risk-toggle"
    )
    .forEach(
      checkbox => {

        checkbox.addEventListener(
          "change",
          rebuildLayers
        );
      }
    );


  document
    .querySelectorAll(
      ".type-toggle"
    )
    .forEach(
      checkbox => {

        checkbox.addEventListener(
          "change",
          rebuildLayers
        );
      }
    );


  document
    .querySelectorAll(
      'input[name="colorMode"]'
    )
    .forEach(
      radio => {

        radio.addEventListener(
          "change",
          rebuildLayers
        );
      }
    );


  const lyrHeat =
    document.getElementById(
      "lyrHeat"
    );


  if (lyrHeat) {

    lyrHeat.addEventListener(
      "change",
      event => {

        if (
          event.target.checked
        ) {

          heatLayer.addTo(map);

        } else {

          map.removeLayer(
            heatLayer
          );
        }
      }
    );
  }


  const lyrMarkers =
    document.getElementById(
      "lyrMarkers"
    );


  if (lyrMarkers) {

    lyrMarkers.addEventListener(
      "change",
      event => {

        if (
          event.target.checked
        ) {

          clusterLayer.addTo(map);

        } else {

          map.removeLayer(
            clusterLayer
          );
        }
      }
    );
  }


  const dateFrom =
    document.getElementById(
      "dateFrom"
    );


  const dateTo =
    document.getElementById(
      "dateTo"
    );


  if (dateFrom) {

    dateFrom.addEventListener(
      "change",
      renderChart
    );
  }


  if (dateTo) {

    dateTo.addEventListener(
      "change",
      renderChart
    );
  }
}


// ============================================================
// START
// ============================================================

init();