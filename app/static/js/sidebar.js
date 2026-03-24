/**
 * sidebar.js — LSOA detail panel
 */

const SOCIO_INDICATORS = [
  { key: 'ind_Health Deprivation and Disability Score', label: 'Health Deprivation & Disability', isScore: true },
  { key: 'ind_Income Score (rate)', label: 'Income Deprivation', isScore: false },
  { key: 'ind_Employment Score (rate)', label: 'Employment Deprivation', isScore: false },
  { key: 'ind_Barriers to Housing and Services Score', label: 'Barriers to Housing & Services', isScore: true },
  { key: 'ind_Crime Score', label: 'Crime', isScore: true },
];

const DEMO_INDICATORS = [
  { key: 'ind_long_term_sick', label: 'Long-term Sick Rate', isScore: false },
  { key: 'ind_econ_inactive', label: 'Economic Inactivity Rate', isScore: false },
  { key: 'ind_unemployed', label: 'Unemployment Rate', isScore: false },
];

function tierBadgeStyle(tier, color) {
  const bg = {
    Critical: 'rgba(211,47,47,0.1)',
    High: 'rgba(245,124,0,0.1)',
    Moderate: 'rgba(253,216,53,0.15)',
    Low: 'rgba(56,142,60,0.1)',
  };
  return `background:${bg[tier] || '#eee'}; color:${color};`;
}

function formatValue(val, isScore) {
  if (val == null || isNaN(val)) return '—';
  // Rates (0-1 range) show as percentage; scores show as-is
  if (!isScore && val < 1.5) return (val * 100).toFixed(1) + '%';
  return val.toFixed(2);
}

window.showLSOADetail = function (props) {
  const sidebar = document.getElementById('sidebar');
  const content = document.getElementById('sidebar-content');

  // Find borough average LRI
  const boroughName = props['Local Authority District name (2019)'];
  let boroughAvg = null;
  if (window.APP.boroughStats) {
    const b = window.APP.boroughStats.find(s => s.borough === boroughName);
    if (b) boroughAvg = b.mean_lri;
  }

  function barHTML(ind, val) {
    let pct = 0;
    if (val != null && !isNaN(val)) {
      if (ind.isScore) {
        // IMD scores: health ~-3 to 2, crime ~-3 to 3, barriers ~10 to 50
        pct = Math.min(100, Math.max(0, ((val + 3) / 6) * 100));
      } else {
        pct = Math.min(100, val * 100);
      }
    }
    return `
      <div class="indicator-bar-group">
        <div class="indicator-bar-label">
          <span>${ind.label}</span>
          <span class="value">${formatValue(val, ind.isScore)}</span>
        </div>
        <div class="indicator-bar-track">
          <div class="indicator-bar-fill" style="width:${Math.max(2, pct)}%"></div>
        </div>
      </div>`;
  }

  const html = `
    <div class="lsoa-header">
      <h2>${props.lsoa_name || props.lsoa_code}</h2>
      <div class="borough">${boroughName || ''}</div>
    </div>

    <div class="lri-badge" style="${tierBadgeStyle(props.risk_tier, props.risk_color)}">
      <span class="score">${props.lri_score}</span>
      <div>
        <div class="tier-label" style="color:${props.risk_color}">${props.risk_tier} Risk</div>
        <div style="font-size:0.7rem;color:#636e72">out of 10</div>
      </div>
    </div>

    ${boroughAvg != null ? `
      <div style="font-size:0.8rem;color:#636e72;margin-bottom:8px;">
        Borough average: <strong>${boroughAvg.toFixed(2)}</strong>
        (${props.lri_score > boroughAvg ? '+' : ''}${(props.lri_score - boroughAvg).toFixed(2)})
      </div>` : ''}

    <div class="section-title">Socioeconomic Deprivation</div>
    ${SOCIO_INDICATORS.map(ind => barHTML(ind, props[ind.key])).join('')}

    <div class="section-title">Demographic Vulnerability</div>
    ${DEMO_INDICATORS.map(ind => barHTML(ind, props[ind.key])).join('')}

    <div class="section-title">Context</div>
    <table class="stats-table">
      <tr><td>Overall IMD Score</td><td>${props.imd_score ?? '—'}</td></tr>
      <tr><td>SAMHI Index (2022)</td><td>${props.samhi_index_2022 ?? '—'}</td></tr>
      <tr><td>Bad/Very Bad Health %</td><td>${props.health_bad_or_very_bad_pct != null ? props.health_bad_or_very_bad_pct.toFixed(1) + '%' : '—'}</td></tr>
      <tr><td>Disability Rate %</td><td>${props.disability_rate_pct != null ? props.disability_rate_pct.toFixed(1) + '%' : '—'}</td></tr>
      <tr><td>Unpaid Care Rate %</td><td>${props.unpaid_care_rate_pct != null ? props.unpaid_care_rate_pct.toFixed(1) + '%' : '—'}</td></tr>
      <tr><td>Population (16+)</td><td>${props.total_16plus ? props.total_16plus.toLocaleString() : '—'}</td></tr>
      <tr><td>Pop. Density (2021)</td><td>${props.pop_density_2021 ? Math.round(props.pop_density_2021).toLocaleString() : '—'}</td></tr>
    </table>
  `;

  content.innerHTML = html;
  sidebar.classList.add('sidebar-open');
  sidebar.classList.remove('sidebar-closed');
};

// Close sidebar
document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('sidebar-close').addEventListener('click', () => {
    const sidebar = document.getElementById('sidebar');
    sidebar.classList.remove('sidebar-open');
    sidebar.classList.add('sidebar-closed');
    if (window.APP.selectedLayer) {
      window.APP.geojsonLayer.resetStyle(window.APP.selectedLayer);
      window.APP.selectedLayer = null;
      window.APP.selectedFeature = null;
    }
  });
});
