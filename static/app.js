'use strict';
const $ = (id) => document.getElementById(id);
const meta = {moisture: ['Soil moisture', '%', 0, 100], temperature: ['Temperature', '°C', -10, 60], ph: ['Soil pH', 'pH', 0, 14], light: ['Light level', '%', 0, 100], alkalinity: ['Alkalinity', 'mg/L as CaCO₃', 0, 400]};
const sources = {local_demo: 'Local demo · synthetic', mqtt_demo: 'MQTT demo · synthetic', wokwi_simulation: 'Wokwi · simulated', physical_device: 'Device reported · unverified'};
let readings = [], latestOverview = null, lastSuccessAt = null, lastFailure = false, loading = false;
let historyExpanded = false, searchTerm = '';
const mqttMode = document.body.dataset.transport === 'mqtt';
const numeric = (value) => Number(value).toLocaleString(undefined, {maximumFractionDigits: 1});
const localTime = (value) => new Date(value).toLocaleTimeString([], {hour: '2-digit', minute: '2-digit', second: '2-digit'});
const fullTime = (value) => new Date(value).toLocaleString([], {year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit', timeZoneName: 'short'});
function element(tag, className, text) { const node = document.createElement(tag); if (className) node.className = className; if (text !== undefined) node.textContent = text; return node; }

function updateFreshness() {
  if (!latestOverview) return;
  const latest = latestOverview.latest;
  const elapsed = lastSuccessAt === null ? 0 : Math.max(0, (Date.now() - lastSuccessAt) / 1000);
  const age = latest ? Math.max(0, latestOverview.age_seconds + elapsed) : null;
  const stale = age !== null && age > latestOverview.stale_seconds;
  const state = lastFailure ? 'offline' : !latest ? 'waiting' : stale ? 'stale' : 'current';
  $('connection').className = `status-badge ${state}`;
  $('connection').textContent = {offline: 'Disconnected', waiting: 'Waiting', stale: 'Stale data', current: 'Receiving data'}[state];
  $('sample-age').textContent = age === null ? 'No data yet' : age < 60 ? `${Math.floor(age)}s ago` : `${Math.floor(age / 60)}m ago`;
  const warningCount = latest ? latest.alerts.length : 0;
  $('status-title').textContent = lastFailure ? 'Backend unreachable' : !latest ? 'Waiting for readings' : stale ? 'Updates have stopped' : warningCount ? 'Conditions need attention' : 'Within demo thresholds';
  $('status-detail').textContent = lastFailure ? 'Check the local server. Last known readings remain visible.' : !latest ? (mqttMode ? 'Waiting for Wokwi or a test publisher through the MQTT subscriber.' : 'Start the local demo feeder to see conditions.') : stale ? 'This sample is over 20 seconds old. Check the feeder or device connection.' : warningCount ? `${warningCount} warning${warningCount === 1 ? '' : 's'} in the latest sample. Verify field conditions.` : 'Readings are current. No demonstration warnings in this sample.';
  $('freshness-caption').textContent = {offline: 'Backend connection lost', waiting: 'Waiting for your device', stale: 'Sample is over 20 seconds old', current: 'Updates are arriving'}[state];
}

function renderOverview(data) {
  latestOverview = data;
  lastSuccessAt = Date.now();
  const latest = data.latest;
  for (const key of Object.keys(meta)) $(key + '-value').textContent = latest ? numeric(latest[key]) : '—';
  $('moisture-meter').style.width = `${latest ? latest.moisture : 0}%`;
  $('updated-time').textContent = latest ? localTime(latest.timestamp) : '—';
  $('updated-time').title = latest ? fullTime(latest.timestamp) : '';
  $('source-note').textContent = latest ? `${sources[latest.source]} · field accuracy not verified` : 'No source connected · no field measurements verified';
  $('sample-count').textContent = `${data.count.toLocaleString()} samples stored`;
  $('total-samples').textContent = data.count.toLocaleString();
  $('source-summary').textContent = latest ? ({local_demo:'Synthetic demo', mqtt_demo:'MQTT demo', wokwi_simulation:'Wokwi simulation', physical_device:'Device · unverified'}[latest.source]) : 'Awaiting data';
  $('field-source').textContent = latest ? ({local_demo:'Local demo', mqtt_demo:'MQTT demo', wokwi_simulation:'Wokwi simulation', physical_device:'Unverified device'}[latest.source]) : 'Not connected';
  $('field-condition').textContent = !latest ? 'Waiting for data' : latest.alerts.length ? 'Needs attention' : 'Within demo limits';
  $('field-condition').classList.toggle('needs-attention', !!latest?.alerts.length);
  $('nav-alert-count').textContent = latest ? latest.alerts.length : 0;
  $('notification-dot').hidden = !latest?.alerts.length;
  renderGauge(latest);
  $('alert-count').textContent = latest ? latest.alerts.length : 0;
  const holder = $('alerts'); holder.replaceChildren();
  if (!latest || !latest.alerts.length) {
    const card = element('div', 'empty-alert');
    const icon = element('span', 'empty-check'); icon.append(makeIcon(latest ? 'check' : 'leaf'));
    card.append(icon, element('h3', '', latest ? 'No demo warnings' : 'Waiting for a sample'), element('p', '', latest ? 'All values are within demonstration limits. Continue to verify conditions in the field.' : 'Warnings will appear when a demo threshold is crossed.'));
    holder.append(card);
  } else {
    for (const alert of latest.alerts) {
      const card = element('div', 'alert-item');
      const copy = element('div'); copy.append(element('h3', '', alert.title), element('p', '', alert.action));
      card.append(element('span', 'alert-symbol', '!'), copy);
      holder.append(card);
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
  $('chart-legend').textContent = `${label} (${unit})`;
  $('chart-empty').hidden = series.length > 0;
  $('trend-subtitle').textContent = `${series.length} recent sample${series.length === 1 ? '' : 's'} · sample time`;
  $('sample-count').textContent = `${series.length} displayed · ${(latestOverview?.count || 0).toLocaleString()} stored`;
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
  const body = $('history-body'); body.replaceChildren();
  const matching = selectedReadings().slice().reverse().filter(r => `${r.id} ${fullTime(r.timestamp)} ${r.source} ${sources[r.source]} ${Object.keys(meta).map(key=>r[key]).join(' ')} ${r.alerts.map(a=>a.title).join(' ')}`.toLowerCase().includes(searchTerm));
  const visible = historyExpanded ? matching : matching.slice(0,6);
  $('history-summary').textContent = `Showing ${visible.length} of ${matching.length} sample${matching.length===1?'':'s'}`;
  $('toggle-history').textContent = historyExpanded ? 'Show less ‹' : 'View all ›';
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

function selectedReadings() { return readings.slice(-Number($('history-window').value)); }
function renderGauge(reading) {
  const svg = $('condition-gauge'); svg.replaceChildren();
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

const iconPaths = {
  leaf:'M20 3C9 2 3 7 5 14c1 5 8 6 11 2 3-3 4-8 4-13ZM4 21 15 9M9 16v-5m0 5h5',
  grid:'M3 3h7v7H3ZM14 3h7v7h-7ZM3 14h7v7H3ZM14 14h7v7h-7Z',
  drop:'M12 3C9 7 5 11 5 15a7 7 0 0 0 14 0c0-4-4-8-7-12ZM8 15a4 4 0 0 0 4 4',
  chart:'M3 4v17h18M6 14l5-5 4 3 6-7', bell:'M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9ZM10 21h4',
  clock:'M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0ZM12 7v5l3 2',
  settings:'m9 3-1 3-3 1-2 4 2 2v3l4 3 3-1 3 1 4-3v-3l2-2-2-4-3-1-1-3ZM15 11a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z',
  search:'M17 10.5a6.5 6.5 0 1 1-13 0 6.5 6.5 0 0 1 13 0ZM16 16l5 5',
  download:'M12 3v12m-5-5 5 5 5-5M4 16v5h16v-5',refresh:'M20 11a8 8 0 1 0-2 7M20 4v7h-7',
  database:'M20 5c0 4-16 4-16 0s16-4 16 0ZM4 5v7c0 4 16 4 16 0V5M4 12v7c0 4 16 4 16 0v-7',
  wave:'M2 7c4-6 6 6 10 0s6 6 10 0M2 13c4-6 6 6 10 0s6 6 10 0M2 19c4-6 6 6 10 0s6 6 10 0',
  sun:'M16 12a4 4 0 1 1-8 0 4 4 0 0 1 8 0ZM12 1v3m0 16v3M1 12h3m16 0h3M4 4l2 2m12 12 2 2M4 20l2-2M18 6l2-2',
  chevron:'m9 5 7 7-7 7',check:'m5 12 4 4L19 6',info:'M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0ZM12 11v6m0-11v1'
};
function makeIcon(name) {const svg=svgNode('svg',{viewBox:'0 0 24 24',class:'icon','aria-hidden':'true'}); svg.append(svgNode('path',{d:iconPaths[name]||iconPaths.leaf})); return svg;}
function updateDate() {
  const now = new Date(), hour=Number(new Intl.DateTimeFormat('en-GB',{hour:'numeric',hourCycle:'h23',timeZone:'Asia/Colombo'}).format(now));
  $('greeting').replaceChildren(document.createTextNode(hour<12?'Good morning ':hour<18?'Good afternoon ':'Good evening '),element('span','',hour<18?'☀':'☾'));
  $('today-weekday').textContent = now.toLocaleDateString('en-GB',{weekday:'long',timeZone:'Asia/Colombo'});
  $('today-date').textContent = now.toLocaleDateString('en-GB',{day:'numeric',month:'long',year:'numeric',timeZone:'Asia/Colombo'});
}

async function getJSON(path) {
  const response = await fetch(path, {cache: 'no-store', signal: AbortSignal.timeout(5000)});
  if (!response.ok) throw new Error('API unavailable');
  return response.json();
}
async function refresh() {
  if (loading) return;
  loading = true; $('refresh').disabled = true;
  try {
    const [overview, history] = await Promise.all([getJSON('/api/overview'), getJSON('/api/readings?limit=60')]);
    lastFailure = false; readings = history.readings;
    renderOverview(overview); renderChart(); renderHistory();
  } catch (_error) {
    lastFailure = true;
    if (!latestOverview) latestOverview = {latest: null, stale_seconds: 20};
    updateFreshness();
  } finally {loading = false; $('refresh').disabled = false;}
}
$('chart-metric').addEventListener('change', renderChart);
$('refresh').addEventListener('click', refresh);
$('history-window').addEventListener('change',()=>{renderChart();renderHistory();});
$('toggle-history').addEventListener('click',()=>{historyExpanded=!historyExpanded;renderHistory();});
function setSearch(value) {searchTerm=value.trim().toLowerCase();$('header-search').value=value;$('history-filter').value=value;renderHistory();}
for(const id of ['header-search','history-filter']) $(id).addEventListener('input',e=>setSearch(e.target.value));
$('header-search').addEventListener('keydown',e=>{if(e.key==='Enter'){$('history').scrollIntoView({block:'start',behavior:'smooth'});}});
let chartResizeFrame;
window.addEventListener('resize',()=>{cancelAnimationFrame(chartResizeFrame);chartResizeFrame=requestAnimationFrame(renderChart);});
document.addEventListener('keydown',e=>{if(e.key==='/'&&!['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)){e.preventDefault();const input=$('header-search').offsetParent?$('header-search'):$('history-filter');input.focus();input.scrollIntoView({block:'center',behavior:'smooth'});}});
document.querySelectorAll('[data-icon]').forEach(node=>node.append(makeIcon(node.dataset.icon)));
document.querySelectorAll('.nav-link,.mobile-nav a').forEach(link=>link.addEventListener('click',()=>{document.querySelectorAll('.nav-link,.mobile-nav a').forEach(item=>item.classList.toggle('active',item.hash===link.hash));if(link.hash==='#system')$('system').open=true;}));
updateDate();renderGauge(null);renderChart(); refresh(); setInterval(refresh, 4000); setInterval(updateFreshness, 1000);setInterval(updateDate,60000);
