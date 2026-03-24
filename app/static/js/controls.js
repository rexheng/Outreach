/**
 * controls.js — Borough filter, need level toggles, layer switcher, legend
 * Outreach: The Geography of Wellbeing
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
    title.textContent = 'Composite Need Index';
    items.innerHTML = [
      { color: '#6B4A3A', label: 'Critical Need (8\u201310)' },
      { color: '#B5725A', label: 'High Need (6\u20138)' },
      { color: '#D4A574', label: 'Elevated (3\u20136)' },
      { color: '#E5D5C5', label: 'Lower Need (0\u20133)' },
    ].map(i => `
      <div class="legend-item">
        <div class="legend-swatch" style="background:${i.color}"></div>
        <span>${i.label}</span>
      </div>
    `).join('');
  } else {
    // Determine label from the selected radio card
    const selectedRadio = document.querySelector('#layer-selector input[type="radio"]:checked');
    let label = field;
    if (selectedRadio) {
      const card = selectedRadio.closest('.radio-card');
      const titleEl = card ? card.querySelector('.radio-card-title') : null;
      if (titleEl) label = titleEl.textContent;
    }
    title.textContent = label;

    const range = window.APP._fieldRange || { min: 0, max: 1 };
    items.innerHTML = `
      <div style="display:flex;align-items:center;gap:8px;font-size:0.78rem;color:var(--text-body)">
        <span>${range.min.toFixed(2)}</span>
        <div style="flex:1;height:12px;border-radius:4px;
          background:linear-gradient(to right, #F5F0EB, #D4A574, #B5725A, #6B4A3A)"></div>
        <span>${range.max.toFixed(2)}</span>
      </div>
    `;
  }
};

// Handle ?borough= query param from overview page
window.applyBoroughFromURL = function () {
  const params = new URLSearchParams(window.location.search);
  const borough = params.get('borough');
  if (borough) {
    const select = document.getElementById('borough-select');
    select.value = borough;
    select.dispatchEvent(new Event('change'));
  }
};

// Sync briefing button state with current borough selection
window.syncBriefingButton = function () {
  const select = document.getElementById('borough-select');
  const btn = document.getElementById('download-briefing');
  if (select && btn && select.value) {
    btn.href = '/api/briefing/' + encodeURIComponent(select.value);
    btn.style.display = 'block';
  }
};

document.addEventListener('DOMContentLoaded', () => {
  // Borough filter
  const briefingBtn = document.getElementById('download-briefing');
  document.getElementById('borough-select').addEventListener('change', (e) => {
    window.APP.currentBorough = e.target.value;
    renderGeoJSON();

    // Show/hide briefing download button
    if (briefingBtn) {
      if (e.target.value) {
        briefingBtn.href = '/api/briefing/' + encodeURIComponent(e.target.value);
        briefingBtn.style.display = 'block';
      } else {
        briefingBtn.style.display = 'none';
      }
    }

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

  // Need level filters
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

  // Layer switcher — radio cards
  const radioCards = document.querySelectorAll('#layer-selector .radio-card');
  radioCards.forEach(card => {
    const radio = card.querySelector('input[type="radio"]');
    card.addEventListener('click', () => {
      // Update selected state
      radioCards.forEach(c => c.classList.remove('selected'));
      card.classList.add('selected');
      radio.checked = true;

      // Update map layer
      window.APP.currentField = radio.value;
      renderGeoJSON();
    });
  });
});
