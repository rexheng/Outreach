/**
 * sidebar.js — LSOA detail panel for Outreach
 * Editorial-style neighbourhood profile
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

/** Inner London boroughs for badge classification */
const INNER_LONDON = new Set([
  'Camden', 'City of London', 'Greenwich', 'Hackney', 'Hammersmith and Fulham',
  'Islington', 'Kensington and Chelsea', 'Lambeth', 'Lewisham', 'Newham',
  'Southwark', 'Tower Hamlets', 'Wandsworth', 'Westminster',
]);

function tierBadgeClass(tier) {
  return {
    Critical: 'tier-critical',
    High:     'tier-high',
    Moderate: 'tier-moderate',
    Low:      'tier-low',
  }[tier] || '';
}

function tierDisplayName(tier) {
  return {
    Critical: 'Critical Need',
    High:     'High Need',
    Moderate: 'Elevated',
    Low:      'Lower Need',
  }[tier] || tier;
}

function formatValue(val, isScore) {
  if (val == null || isNaN(val)) return '\u2014';
  if (!isScore && val < 1.5) return (val * 100).toFixed(1) + '%';
  return val.toFixed(2);
}

/**
 * Generate an editorial description of the neighbourhood from data.
 */
function generateEditorial(props, boroughName, boroughAvg) {
  const score = props.lri_score;
  const tier = props.risk_tier;
  const name = props.lsoa_name || props.lsoa_code;

  let severity, context;

  if (tier === 'Critical') {
    severity = 'faces some of the most acute wellbeing challenges in the capital';
    context = 'Residents here experience compounding pressures across health, employment and housing that demand urgent, coordinated intervention.';
  } else if (tier === 'High') {
    severity = 'shows significantly elevated need across multiple wellbeing dimensions';
    context = 'The convergence of health deprivation and economic vulnerability here suggests sustained support could make a meaningful difference.';
  } else if (tier === 'Moderate') {
    severity = 'presents a mixed picture of wellbeing, with pockets of resilience alongside emerging need';
    context = 'Early intervention and community strengthening could help prevent these moderate pressures from deepening.';
  } else {
    severity = 'demonstrates relatively strong wellbeing outcomes compared to London averages';
    context = 'While aggregate indicators are favourable, individual experiences of isolation may still exist beneath the data.';
  }

  let comparison = '';
  if (boroughAvg != null) {
    const diff = score - boroughAvg;
    if (Math.abs(diff) < 0.3) {
      comparison = ` Its need index is close to the ${boroughName} average.`;
    } else if (diff > 0) {
      comparison = ` Its need index sits ${diff.toFixed(1)} points above the ${boroughName} average.`;
    } else {
      comparison = ` Its need index sits ${Math.abs(diff).toFixed(1)} points below the ${boroughName} average.`;
    }
  }

  return `${name} ${severity}.${comparison} ${context}`;
}

window.showLSOADetail = function (props) {
  const sidebar = document.getElementById('sidebar');
  const content = document.getElementById('sidebar-content');

  const boroughName = props['Local Authority District name (2019)'];
  const isInner = INNER_LONDON.has(boroughName);
  let boroughAvg = null;
  if (window.APP.boroughStats) {
    const b = window.APP.boroughStats.find(s => s.borough === boroughName);
    if (b) boroughAvg = b.mean_lri;
  }

  function barHTML(ind, val) {
    let pct = 0;
    if (val != null && !isNaN(val)) {
      if (ind.isScore) {
        pct = Math.min(100, Math.max(0, ((val + 3) / 6) * 100));
      } else {
        pct = Math.min(100, val * 100);
      }
    }
    return `
      <div class="indicator-bar-group">
        <div class="indicator-bar-label">
          <span class="name">${ind.label}</span>
          <span class="value">${formatValue(val, ind.isScore)}</span>
        </div>
        <div class="indicator-bar-track">
          <div class="indicator-bar-fill" style="width:${Math.max(2, pct)}%"></div>
        </div>
      </div>`;
  }

  const editorial = generateEditorial(props, boroughName, boroughAvg);
  const firstLetter = editorial.charAt(0);
  const restOfText = editorial.slice(1);

  const html = `
    <!-- Header strip -->
    <div class="sidebar-header-strip">
      <h2>${props.lsoa_name || props.lsoa_code}</h2>
      <div class="sidebar-location">
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
          <path d="M7 1C4.79 1 3 2.79 3 5C3 8 7 13 7 13C7 13 11 8 11 5C11 2.79 9.21 1 7 1Z" stroke="currentColor" stroke-width="1.2" fill="none"/>
          <circle cx="7" cy="5" r="1.5" fill="currentColor"/>
        </svg>
        <span>${boroughName || ''}</span>
      </div>
      <div class="sidebar-badges">
        <span class="badge badge-location">${isInner ? 'Inner London' : 'Outer London'}</span>
        <span class="badge badge-tier ${tierBadgeClass(props.risk_tier)}">${tierDisplayName(props.risk_tier)}</span>
      </div>
    </div>

    <!-- KPI Row -->
    <div class="kpi-row">
      <div class="kpi-card">
        <span class="kpi-value">${props.lri_score}</span>
        <span class="kpi-label">Need Index</span>
        <span class="kpi-sub">out of 10</span>
      </div>
      <div class="kpi-card">
        <span class="kpi-value">${props.imd_score != null ? Math.round(props.imd_score) : '\u2014'}</span>
        <span class="kpi-label">IMD Score</span>
        <span class="kpi-sub">deprivation rank</span>
      </div>
    </div>

    <!-- Editorial paragraph -->
    <div class="sidebar-editorial">
      <p><span class="drop-cap-sm">${firstLetter}</span>${restOfText}</p>
    </div>

    <!-- Socioeconomic Indicators -->
    <div class="sidebar-section">
      <div class="section-title">Socioeconomic Deprivation</div>
      ${SOCIO_INDICATORS.map(ind => barHTML(ind, props[ind.key])).join('')}
    </div>

    <!-- Demographic Vulnerability -->
    <div class="sidebar-section">
      <div class="section-title">Demographic Vulnerability</div>
      ${DEMO_INDICATORS.map(ind => barHTML(ind, props[ind.key])).join('')}
    </div>

    <!-- Context Table -->
    <div class="sidebar-section">
      <div class="section-title">Context</div>
      <table class="stats-table">
        <tr><td>SAMHI Index (2022)</td><td>${props.samhi_index_2022 ?? '\u2014'}</td></tr>
        <tr><td>Bad/Very Bad Health</td><td>${props.health_bad_or_very_bad_pct != null ? props.health_bad_or_very_bad_pct.toFixed(1) + '%' : '\u2014'}</td></tr>
        <tr><td>Disability Rate</td><td>${props.disability_rate_pct != null ? props.disability_rate_pct.toFixed(1) + '%' : '\u2014'}</td></tr>
        <tr><td>Unpaid Care Rate</td><td>${props.unpaid_care_rate_pct != null ? props.unpaid_care_rate_pct.toFixed(1) + '%' : '\u2014'}</td></tr>
        <tr><td>Population (16+)</td><td>${props.total_16plus ? props.total_16plus.toLocaleString() : '\u2014'}</td></tr>
        <tr><td>Population Density</td><td>${props.pop_density_2021 ? Math.round(props.pop_density_2021).toLocaleString() + '/km\u00B2' : '\u2014'}</td></tr>
      </table>
    </div>

    <!-- London Comparison -->
    ${boroughAvg != null ? `
    <div class="sidebar-comparison">
      <div class="section-title" style="border:none;margin-top:0;padding-top:0">London Comparison</div>
      <div class="comparison-row">
        <span class="comparison-label">This neighbourhood</span>
        <span class="comparison-value">${props.lri_score}</span>
      </div>
      <div class="comparison-row">
        <span class="comparison-label">${boroughName} average</span>
        <span class="comparison-value">
          ${boroughAvg.toFixed(2)}
          <span class="comparison-diff ${props.lri_score > boroughAvg ? 'above' : 'below'}">
            (${props.lri_score > boroughAvg ? '+' : ''}${(props.lri_score - boroughAvg).toFixed(2)})
          </span>
        </span>
      </div>
    </div>` : ''}
  `;

  content.innerHTML = html;
  sidebar.classList.add('sidebar-open');
  sidebar.classList.remove('sidebar-closed');

  // Scroll to top of sidebar content
  sidebar.scrollTop = 0;
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
