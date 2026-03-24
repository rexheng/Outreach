/**
 * controls.js — Borough filter, risk tier toggles, layer switcher, legend
 */

// Populate borough dropdown from stats
window.populateBoroughs = function (boroughStats) {
  const select = document.getElementById('borough-select');
  boroughStats
    .map(b => b.borough)
    .sort()
    .forEach(name => {
      const opt = document.createElement('option');
      opt.value = name;
      opt.textContent = name;
      select.appendChild(opt);
    });
};

// Update legend
window.updateLegend = function () {
  const title = document.getElementById('legend-title');
  const items = document.getElementById('legend-items');
  const field = window.APP.currentField;

  if (field === 'lri_score') {
    title.textContent = 'Loneliness Risk Index';
    items.innerHTML = [
      { color: '#d32f2f', label: 'Critical (8–10)' },
      { color: '#f57c00', label: 'High (6–8)' },
      { color: '#fdd835', label: 'Moderate (3–6)' },
      { color: '#388e3c', label: 'Low (0–3)' },
    ].map(i => `
      <div class="legend-item">
        <div class="legend-swatch" style="background:${i.color}"></div>
        <span>${i.label}</span>
      </div>
    `).join('');
  } else {
    // Continuous scale legend
    const label = document.getElementById('layer-select')
      .selectedOptions[0]?.textContent || field;
    title.textContent = label;

    const range = window.APP._fieldRange || { min: 0, max: 1 };
    items.innerHTML = `
      <div style="display:flex;align-items:center;gap:8px;font-size:0.8rem">
        <span>${range.min.toFixed(2)}</span>
        <div style="flex:1;height:12px;border-radius:3px;
          background:linear-gradient(to right, #e0f4f4, #065a64)"></div>
        <span>${range.max.toFixed(2)}</span>
      </div>
    `;
  }
};

document.addEventListener('DOMContentLoaded', () => {
  // Borough filter
  document.getElementById('borough-select').addEventListener('change', (e) => {
    window.APP.currentBorough = e.target.value;
    renderGeoJSON();

    // Fit bounds to borough
    if (e.target.value && window.APP.geojsonLayer) {
      const bounds = window.APP.geojsonLayer.getBounds();
      if (bounds.isValid()) {
        window.APP.map.fitBounds(bounds, { padding: [30, 30] });
      }
    } else {
      window.APP.map.setView([51.509, -0.118], 10);
    }
  });

  // Risk tier filters
  document.querySelectorAll('#tier-filters input[type="checkbox"]').forEach(cb => {
    cb.addEventListener('change', () => {
      if (cb.checked) {
        window.APP.activeTiers.add(cb.value);
      } else {
        window.APP.activeTiers.delete(cb.value);
      }
      renderGeoJSON();
    });
  });

  // Layer switcher
  document.getElementById('layer-select').addEventListener('change', (e) => {
    window.APP.currentField = e.target.value;
    renderGeoJSON();
  });
});
