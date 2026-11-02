'use strict';
const $ = (id) => document.getElementById(id);
const meta = {moisture: ['Soil moisture', '%', 0, 100], temperature: ['Temperature', '°C', -10, 60], ph: ['Soil pH', 'pH', 0, 14], light: ['Light level', '%', 0, 100], alkalinity: ['Alkalinity', 'mg/L as CaCO₃', 0, 400]};
const sources = {local_demo: 'Local demo · synthetic', mqtt_demo: 'MQTT demo · synthetic', wokwi_simulation: 'Wokwi · simulated', physical_device: 'Device reported · unverified'};
let readings = [], latestOverview = null, lastSuccessAt = null, lastFailure = false, loading = false;
const currentPage = document.body.dataset.page || 'dashboard';
let historyExpanded = currentPage === 'history';
let searchTerm = (new URLSearchParams(location.search).get('q') || '').trim().toLowerCase();
const mqttMode = document.body.dataset.transport === 'mqtt';
const numeric = (value) => Number(value).toLocaleString(undefined, {maximumFractionDigits: 1});
const localTime = (value) => new Date(value).toLocaleTimeString([], {hour: '2-digit', minute: '2-digit', second: '2-digit'});
const fullTime = (value) => new Date(value).toLocaleString([], {year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit', timeZoneName: 'short'});
function element(tag, className, text) { const node = document.createElement(tag); if (className) node.className = className; if (text !== undefined) node.textContent = text; return node; }
function setText(id, text) { const node = $(id); if (node) node.textContent = text; }
function on(id, event, handler) { $(id)?.addEventListener(event, handler); }

function updateFreshness() {
  if (!latestOverview) return;
  const latest = latestOverview.latest;
  const elapsed = lastSuccessAt === null ? 0 : Math.max(0, (Date.now() - lastSuccessAt) / 1000);
  const age = latest ? Math.max(0, latestOverview.age_seconds + elapsed) : null;
  const stale = age !== null && age > latestOverview.stale_seconds;
  const state = lastFailure ? 'offline' : !latest ? 'waiting' : stale ? 'stale' : 'current';
  $('connection').className = `status-badge badge ${state}`;
  setText('connection', {offline: 'Disconnected', waiting: 'Waiting', stale: 'Stale data', current: 'Receiving data'}[state]);
  setText('sample-age', age === null ? 'No data yet' : age < 60 ? `${Math.floor(age)}s ago` : `${Math.floor(age / 60)}m ago`);
  const warningCount = latest ? latest.alerts.length : 0;
  setText('status-title', lastFailure ? 'Backend unreachable' : !latest ? 'Waiting for readings' : stale ? 'Updates have stopped' : warningCount ? 'Conditions need attention' : 'Within demo thresholds');
  setText('status-detail', lastFailure ? 'Check the local server. Last known readings remain visible.' : !latest ? (mqttMode ? 'Waiting for Wokwi or a test publisher through the MQTT subscriber.' : 'Start the local demo feeder to see conditions.') : stale ? 'This sample is over 20 seconds old. Check the feeder or device connection.' : warningCount ? `${warningCount} warning${warningCount === 1 ? '' : 's'} in the latest sample. Verify field conditions.` : 'Readings are current. No demonstration warnings in this sample.');
  setText('freshness-caption', {offline: 'Backend connection lost', waiting: 'Waiting for your device', stale: 'Sample is over 20 seconds old', current: 'Updates are arriving'}[state]);
}

function renderOverview(data) {
  latestOverview = data;
  lastSuccessAt = Date.now();
  const latest = data.latest;
  for (const key of Object.keys(meta)) setText(key + '-value', latest ? numeric(latest[key]) : '—');
  if ($('moisture-meter')) $('moisture-meter').style.width = `${latest ? latest.moisture : 0}%`;
  setText('updated-time', latest ? localTime(latest.timestamp) : '—');
  if ($('updated-time')) $('updated-time').title = latest ? fullTime(latest.timestamp) : '';
  setText('source-note', latest ? `${sources[latest.source]} · field accuracy not verified` : 'No source connected · no field measurements verified');
  setText('sample-count', `${data.count.toLocaleString()} samples stored`);
  setText('total-samples', data.count.toLocaleString());
  setText('source-summary', latest ? ({local_demo:'Synthetic demo', mqtt_demo:'MQTT demo', wokwi_simulation:'Wokwi simulation', physical_device:'Device · unverified'}[latest.source]) : 'Awaiting data');
  setText('field-source', latest ? ({local_demo:'Local demo', mqtt_demo:'MQTT demo', wokwi_simulation:'Wokwi simulation', physical_device:'Unverified device'}[latest.source]) : 'Not connected');
  setText('field-condition', !latest ? 'Waiting for data' : latest.alerts.length ? 'Needs attention' : 'Within demo limits');
  $('field-condition')?.classList.toggle('needs-attention', !!latest?.alerts.length);
  setText('nav-alert-count', latest ? latest.alerts.length : 0);
  $('notification-dot').hidden = !latest?.alerts.length;
  renderGauge(latest);
  setText('alert-count', latest ? latest.alerts.length : 0);
  const holder = $('alerts');
  if (holder) {
    holder.replaceChildren();
    if (!latest || !latest.alerts.length) {
      const card = element('div', 'empty-alert');
      const icon = element('span', 'empty-check'); icon.append(makeIcon(latest ? 'check' : 'leaf'));
      card.append(icon, element('h3', '', latest ? 'No demo warnings' : 'Waiting for a sample'), element('p', '', latest ? 'All values are within demonstration limits. Continue to verify conditions in the field.' : 'Warnings will appear when a demo threshold is crossed.'));
      holder.append(card);
    } else {
      for (const alert of latest.alerts) {
        const card = element('div', 'alert-item');
        const copy = element('div'); copy.append(element('h3', '', alert.title), element('p', '', alert.action));
        const symbol = element('span', 'alert-symbol'); symbol.append(makeIcon('warning'));
        card.append(symbol, copy);
        holder.append(card);
      }
    }
  }
  updateFreshness();
}

function svgNode(tag, attrs, text) {
  const node = document.createElementNS('http://www.w3.org/2000/svg', tag);
  for (const [key, value] of Object.entries(attrs)) node.setAttribute(key, value);
  if (text !== undefined) node.textContent = text;
  return node;
}
function renderChart() {
  if (!$('trend-chart')) return;
  const series = selectedReadings();
  const key = $('chart-metric').value, [label, unit, minimum, standardMax] = meta[key];
  const svg = $('trend-chart'); svg.replaceChildren();
  const min = Math.min(minimum, ...series.map(r => r[key]));
  const max = Math.max(standardMax, ...series.map(r => r[key]));
  const drawingWidth = Math.max(280, Math.min(680, svg.parentElement.clientWidth || 680));
  svg.setAttribute('viewBox', `0 0 ${drawingWidth} 230`);
  const left = 40, right = drawingWidth - 15, top = 28, bottom = 190;
  const defs = svgNode('defs', {}), gradient = svgNode('linearGradient', {id:'chart-fill',x1:0,y1:0,x2:0,y2:1});
  gradient.append(svgNode('stop', {offset:'0%','stop-color':'#9ce5b8','stop-opacity':'.65'}), svgNode('stop', {offset:'100%','stop-color':'#f2fcf5','stop-opacity':'.1'})); defs.append(gradient); svg.append(defs);
  setText('chart-legend', `${label} (${unit})`);
  $('chart-empty').hidden = series.length > 0;
  setText('trend-subtitle', `${series.length} recent sample${series.length === 1 ? '' : 's'} · sample time`);
  setText('sample-count', `${series.length} displayed · ${(latestOverview?.count || 0).toLocaleString()} stored`);
  svg.setAttribute('aria-label', `${label}: ${series.length} recent samples. Exact values appear in reading history and CSV export.`);
  for (let i = 0; i <= 4; i++) {
    const y = top + i * (bottom - top) / 4;
    svg.append(svgNode('line', {x1: left, y1: y, x2: right, y2: y, class: 'chart-grid'}));
    svg.append(svgNode('text', {x: left - 10, y: y + 3, 'text-anchor': 'end', class: 'chart-label'}, numeric(max - i * (max - min) / 4)));
  }
  if (!series.length) return;
  const times = series.map(r => Date.parse(r.timestamp)), first = times[0], span = times.at(-1) - first;
  const points = series.map((r, i) => [span ? left + ((times[i] - first) / span) * (right - left) : (left + right) / 2, bottom - ((r[key] - min) / (max - min)) * (bottom - top)]);
  const line = points.map(([x, y], i) => `${i ? 'L' : 'M'}${x.toFixed(1)},${y.toFixed(1)}`).join(' ');
  if (points.length > 1) {
    svg.append(svgNode('path', {d: `${line} L${points.at(-1)[0]},${bottom} L${points[0][0]},${bottom} Z`, class: 'chart-area'}));
    svg.append(svgNode('path', {d: line, class: 'chart-line'}));
  }
  points.forEach(([cx, cy], i) => {const dot = svgNode('circle', {cx, cy, r: points.length < 25 ? 3 : 2, class: 'chart-dot'}); dot.append(svgNode('title', {}, `${fullTime(series[i].timestamp)}: ${numeric(series[i][key])} ${unit}`)); svg.append(dot);});
  const [lastX,lastY] = points.at(-1), tipX = Math.min(right-30,Math.max(left+30,lastX)), tipY = Math.max(1,lastY-39);
  svg.append(svgNode('line',{x1:lastX,x2:lastX,y1:top,y2:bottom,class:'chart-latest-line'}));
  const tip = svgNode('g',{class:'chart-tooltip'}); tip.append(svgNode('rect',{x:tipX-27,y:tipY,width:54,height:25,rx:4}),svgNode('text',{x:tipX,y:tipY+17},`${numeric(series.at(-1)[key])}`)); svg.append(tip);
  const indices = [...new Set([0, Math.floor((series.length - 1) / 2), series.length - 1])];
  for (const i of indices) svg.append(svgNode('text', {x: points[i][0], y: 218, 'text-anchor': i === 0 ? 'start' : i === series.length - 1 ? 'end' : 'middle', class: 'chart-label'}, localTime(series[i].timestamp)));
}

function renderHistory() {
  const body = $('history-body');
  if (!body) return;
  body.replaceChildren();
  const matching = selectedReadings().slice().reverse().filter(r => `${r.id} ${fullTime(r.timestamp)} ${r.source} ${sources[r.source]} ${Object.keys(meta).map(key=>r[key]).join(' ')} ${r.alerts.map(a=>a.title).join(' ')}`.toLowerCase().includes(searchTerm));
  const visible = historyExpanded ? matching : matching.slice(0,6);
  setText('history-summary', `Showing ${visible.length} of ${matching.length} sample${matching.length===1?'':'s'}`);
  $('toggle-history').replaceChildren(document.createTextNode(historyExpanded ? 'Show less ' : 'View all '), makeIcon(historyExpanded ? 'chevron-up' : 'chevron'));
  if (!visible.length) {const row = element('tr'); const cell = element('td', 'empty-cell', searchTerm ? 'No readings match your search.' : 'No samples recorded yet.'); cell.colSpan = 8; row.append(cell); body.append(row); return;}
  for (const reading of visible) {
    const row = element('tr'), timeCell = element('td');
    timeCell.append(element('strong', '', `#${reading.id} · ${localTime(reading.timestamp)}`), element('span', 'cell-sub', fullTime(reading.timestamp)));
    row.append(timeCell);
    for (const key of ['moisture', 'temperature', 'ph', 'light', 'alkalinity']) row.append(element('td', '', `${numeric(reading[key])}${key === 'moisture' || key === 'light' ? '%' : key === 'temperature' ? '°C' : key === 'alkalinity' ? ' mg/L' : ''}`));
    const source = element('td'); source.append(element('span', 'source-tag', sources[reading.source])); row.append(source);
    row.append(element('td', reading.alerts.length ? 'warning-tag' : '', reading.alerts.length ? reading.alerts.map(a => a.title).join(', ') : 'None'));
    body.append(row);
  }
}

function selectedReadings() { return readings.slice(-Number($('history-window')?.value || 60)); }
function renderGauge(reading) {
  const svg = $('condition-gauge');
  if (!svg) return;
  svg.replaceChildren();
  const warnings = new Set(reading?.alerts.map(a=>a.code) || []);
  const checks = [!warnings.has('dry')&&!warnings.has('wet'), !warnings.has('heat'), !warnings.has('ph'), !warnings.has('alkalinity')];
  const good = reading ? checks.filter(Boolean).length : 0;
  const colors = ['#30a9df','#a170e8','#15ac58','#6bc57f'];
  for(let i=0;i<40;i++) {
    const angle = Math.PI - (i/39)*Math.PI;
    const category = Math.floor(i/10);
    const bar = svgNode('line',{x1:160+Math.cos(angle)*97,y1:151-Math.sin(angle)*97,x2:160+Math.cos(angle)*137,y2:151-Math.sin(angle)*137,stroke:reading&&checks[category]?colors[category]:'#edf2ef','stroke-width':5,'stroke-linecap':'round'});
    bar.append(svgNode('title',{},`${['Moisture','Temperature','pH','Alkalinity'][category]}: ${!reading?'no data':checks[category]?'within demo limits':'warning'}`));
    svg.append(bar);
  }
  const label = $('gauge-value'); label.replaceChildren(document.createTextNode(reading ? String(good) : '—'), element('small','','/4'));
  svg.setAttribute('aria-label', reading ? `${good} of 4 conditions within demonstration limits, based on the latest recorded sample.` : 'Waiting for sensor conditions.');
}

// Bootstrap Icons are served locally; labels stay in the surrounding text.
const iconNames = {
  leaf: 'leaf', grid: 'grid-1x2-fill', drop: 'moisture', chart: 'graph-up-arrow',
  bell: 'bell', clock: 'clock-history', settings: 'gear', search: 'search',
  download: 'download', refresh: 'arrow-clockwise', database: 'database',
  wave: 'water', ph: 'eyedropper', sun: 'brightness-high', moon: 'moon-stars',
  chevron: 'chevron-right', 'chevron-up': 'chevron-up', check: 'check2-circle',
  info: 'info-circle', warning: 'exclamation-triangle-fill',
  temperature: 'thermometer-half', external: 'box-arrow-up-right'
};
function makeIcon(name) {
  const icon = element('i', `bi bi-${iconNames[name] || iconNames.leaf} icon`);
  icon.setAttribute('aria-hidden', 'true');
  return icon;
}
function updateDate() {
  const now = new Date(), hour=Number(new Intl.DateTimeFormat('en-GB',{hour:'numeric',hourCycle:'h23',timeZone:'Asia/Colombo'}).format(now));
  if ($('greeting')) $('greeting').replaceChildren(document.createTextNode(hour<12?'Good morning ':hour<18?'Good afternoon ':'Good evening '),makeIcon(hour<18?'sun':'moon'));
  setText('today-weekday', now.toLocaleDateString('en-GB',{weekday:'long',timeZone:'Asia/Colombo'}));
  setText('today-date', now.toLocaleDateString('en-GB',{day:'numeric',month:'long',year:'numeric',timeZone:'Asia/Colombo'}));
}

async function getJSON(path) {
  const response = await fetch(path, {cache: 'no-store', signal: AbortSignal.timeout(5000)});
  if (!response.ok) throw new Error('API unavailable');
  return response.json();
}
async function refresh() {
  if (loading) return;
  loading = true; if ($('refresh')) $('refresh').disabled = true;
  try {
    const [overview, history] = await Promise.all([getJSON('/api/overview'), getJSON('/api/readings?limit=60')]);
    lastFailure = false; readings = history.readings;
    renderOverview(overview); renderChart(); renderHistory();
  } catch (_error) {
    lastFailure = true;
    if (!latestOverview) latestOverview = {latest: null, stale_seconds: 20};
    updateFreshness();
  } finally {loading = false; if ($('refresh')) $('refresh').disabled = false;}
}
on('chart-metric', 'change', renderChart);
on('refresh', 'click', refresh);
on('history-window', 'change', () => { renderChart(); renderHistory(); });
on('toggle-history', 'click', () => { historyExpanded = !historyExpanded; renderHistory(); });
function setSearch(value) {
  searchTerm = value.trim().toLowerCase();
  for (const id of ['header-search', 'history-filter']) if ($(id)) $(id).value = value;
  renderHistory();
}
if ($('history-body')) {
  for (const id of ['header-search', 'history-filter']) on(id, 'input', event => setSearch(event.target.value));
}
let chartResizeFrame;
window.addEventListener('resize', () => { cancelAnimationFrame(chartResizeFrame); chartResizeFrame = requestAnimationFrame(renderChart); });
document.addEventListener('keydown', event => {
  if (event.key === '/' && !['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement.tagName)) {
    event.preventDefault();
    const input = $('header-search')?.offsetParent ? $('header-search') : $('history-filter');
    if (input) { input.focus(); input.scrollIntoView({block: 'center', behavior: 'smooth'}); }
    else location.assign(document.body.dataset.historyUrl);
  }
});
document.querySelectorAll('[data-icon]').forEach(node => node.append(makeIcon(node.dataset.icon)));
// Page links use normal browser navigation; Flask renders the active item.
updateDate(); renderGauge(null); renderChart(); refresh();
setInterval(refresh, 4000); setInterval(updateFreshness, 1000); setInterval(updateDate, 60000);
