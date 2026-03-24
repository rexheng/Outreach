/**
 * map.js — Leaflet choropleth map for Loneliness Risk Index
 */

// Global state
window.APP = {
  map: null,
  geojsonLayer: null,
  geojsonData: null,
  selectedFeature: null,
  selectedLayer: null,
  currentField: 'lri_score',
  activeTiers: new Set(['Critical', 'High', 'Moderate', 'Low']),
  currentBorough: '',
  boroughStats: null,
};

// Risk tier colour scale for LRI
const TIER_COLORS = {
  Critical: '#d32f2f',
  High: '#f57c00',
  Moderate: '#fdd835',
  Low: '#388e3c',
};

// Continuous colour scale for non-LRI layers (teal gradient)
function continuousColor(value, min, max) {
  if (value == null || isNaN(value)) return '#ccc';
  const t = Math.max(0, Math.min(1, (value - min) / (max - min || 1)));
  // Interpolate from light (#e0f4f4) to dark teal (#065a64)
  const r = Math.round(224 + (6 - 224) * t);
  const g = Math.round(244 + (90 - 244) * t);
  const b = Math.round(244 + (100 - 244) * t);
  return `rgb(${r},${g},${b})`;
}

function tierColor(score) {
  if (score >= 8) return TIER_COLORS.Critical;
  if (score >= 6) return TIER_COLORS.High;
  if (score >= 3) return TIER_COLORS.Moderate;
  return TIER_COLORS.Low;
}

function getFieldRange(data, field) {
  let min = Infinity, max = -Infinity;
  for (const f of data.features) {
    const v = f.properties[field];
    if (v != null && !isNaN(v)) {
      if (v < min) min = v;
      if (v > max) max = v;
    }
  }
  return { min, max };
}

function featureStyle(feature) {
  const props = feature.properties;
  const field = window.APP.currentField;
  const value = props[field];

  let fillColor;
  if (field === 'lri_score') {
    fillColor = tierColor(value);
  } else {
    const range = window.APP._fieldRange || { min: 0, max: 1 };
    fillColor = continuousColor(value, range.min, range.max);
  }

  return {
    fillColor,
    fillOpacity: 0.7,
    weight: 0.5,
    color: '#fff',
    opacity: 0.8,
  };
}

function shouldShow(feature) {
  if (!window.APP.activeTiers.has(feature.properties.risk_tier)) return false;
  if (window.APP.currentBorough &&
      feature.properties['Local Authority District name (2019)'] !== window.APP.currentBorough) {
    return false;
  }
  return true;
}

function highlightStyle() {
  return { weight: 3, color: '#065a64', fillOpacity: 0.85 };
}

function resetStyle(layer) {
  window.APP.geojsonLayer.resetStyle(layer);
}

function onEachFeature(feature, layer) {
  const p = feature.properties;

  // Tooltip
  const ttContent = `
    <div class="lsoa-tooltip">
      <div class="tt-name">${p.lsoa_name}</div>
      <div class="tt-score">LRI: ${p.lri_score} — ${p.risk_tier}</div>
    </div>`;
  layer.bindTooltip(ttContent, { sticky: true, className: 'lsoa-tooltip-wrapper' });

  // Hover
  layer.on('mouseover', () => {
    if (layer !== window.APP.selectedLayer) {
      layer.setStyle({ weight: 2, color: '#0a7e8c', fillOpacity: 0.85 });
      layer.bringToFront();
    }
  });
  layer.on('mouseout', () => {
    if (layer !== window.APP.selectedLayer) {
      resetStyle(layer);
    }
  });

  // Click
  layer.on('click', () => {
    // Deselect previous
    if (window.APP.selectedLayer) {
      resetStyle(window.APP.selectedLayer);
    }
    window.APP.selectedLayer = layer;
    window.APP.selectedFeature = feature;
    layer.setStyle(highlightStyle());
    layer.bringToFront();

    // Open sidebar with detail
    window.showLSOADetail(feature.properties);
  });
}

function renderGeoJSON() {
  if (window.APP.geojsonLayer) {
    window.APP.map.removeLayer(window.APP.geojsonLayer);
  }

  // Pre-compute field range for continuous layers
  if (window.APP.currentField !== 'lri_score') {
    window.APP._fieldRange = getFieldRange(window.APP.geojsonData, window.APP.currentField);
  }

  window.APP.geojsonLayer = L.geoJSON(window.APP.geojsonData, {
    style: featureStyle,
    onEachFeature,
    filter: shouldShow,
  }).addTo(window.APP.map);

  // Update legend
  window.updateLegend();
}

async function initMap() {
  // Show loading
  const loading = document.createElement('div');
  loading.id = 'loading';
  loading.innerHTML = '<div class="spinner"></div><span>Loading London data…</span>';
  document.getElementById('app').appendChild(loading);

  // Init Leaflet
  const map = L.map('map', {
    center: [51.509, -0.118],
    zoom: 10,
    zoomControl: true,
    preferCanvas: true,
  });

  L.tileLayer('https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', {
    attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OSM</a> &copy; <a href="https://carto.com/">CARTO</a>',
    maxZoom: 18,
  }).addTo(map);

  window.APP.map = map;

  // Fetch data
  try {
    const [geojsonRes, boroughRes] = await Promise.all([
      fetch('/api/geojson'),
      fetch('/api/boroughs'),
    ]);
    window.APP.geojsonData = await geojsonRes.json();
    window.APP.boroughStats = await boroughRes.json();

    // Populate borough dropdown
    window.populateBoroughs(window.APP.boroughStats);

    // Render
    renderGeoJSON();
  } catch (err) {
    console.error('Failed to load data:', err);
    loading.innerHTML = '<span style="color:#d32f2f">Failed to load data. Is the server running?</span>';
    return;
  }

  // Remove loading
  loading.remove();
}

// Start
document.addEventListener('DOMContentLoaded', initMap);
