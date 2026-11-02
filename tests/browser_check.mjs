// Dependency-free local Edge QA, invoked by smoke_http.py.
import {spawn} from 'node:child_process';
import fs from 'node:fs/promises';
import path from 'node:path';

const [baseURL, profile, outputDirectory, imagePrefix = 'P09_local_demo'] = process.argv.slice(2);
const edge = 'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe';
const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));
const processHandle = spawn(edge, ['--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check', '--remote-debugging-port=0', `--user-data-dir=${profile}`, 'about:blank'], {windowsHide: true, stdio: 'ignore'});
let socket;
try {
  let port;
  for (let attempt = 0; attempt < 100; attempt++) {
    try {port = Number((await fs.readFile(path.join(profile, 'DevToolsActivePort'), 'utf8')).split('\n')[0]); break;} catch { /* wait for Edge startup */ }
    await delay(100);
  }
  if (!port) throw new Error('Edge did not expose its debugging port.');
  const tabs = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
  const tab = tabs.find(tab => tab.type === 'page');
  if (!tab) throw new Error('No browser page target.');
  socket = new WebSocket(tab.webSocketDebuggerUrl);
  await new Promise((resolve, reject) => {socket.onopen = resolve; socket.onerror = reject;});
  let sequence = 0;
  const pending = new Map(), errors = [];
  socket.onmessage = (event) => {
    const message = JSON.parse(event.data);
    if (message.id) {
      const waiter = pending.get(message.id);
      if (waiter) {pending.delete(message.id); clearTimeout(waiter.timer); message.error ? waiter.reject(new Error(message.error.message)) : waiter.resolve(message.result);}
    }
    if (message.method === 'Runtime.exceptionThrown') errors.push(message.params.exceptionDetails.text);
    if (message.method === 'Log.entryAdded' && message.params.entry.level === 'error' && !message.params.entry.text.includes('favicon')) errors.push(message.params.entry.text);
  };
  const command = (method, params = {}) => new Promise((resolve, reject) => {
    const id = ++sequence;
    const timer = setTimeout(() => {pending.delete(id); reject(new Error(`Timed out: ${method}`));}, 15000);
    pending.set(id, {resolve, reject, timer}); socket.send(JSON.stringify({id, method, params}));
  });
  const evaluate = async (expression) => {
    const result = await command('Runtime.evaluate', {expression, awaitPromise: true, returnByValue: true});
    if (result.exceptionDetails) throw new Error(result.exceptionDetails.text);
    return result.result.value;
  };
  const assert = (condition, message) => {if (!condition) throw new Error(message);};
  await command('Runtime.enable'); await command('Log.enable'); await command('Page.enable');
  await command('Emulation.setDeviceMetricsOverride', {width: 1440, height: 1100, deviceScaleFactor: 1, mobile: false});
  await command('Page.navigate', {url: baseURL});
  for (let attempt = 0; attempt < 100; attempt++) {
    if (await evaluate("document.getElementById('moisture-value')?.textContent === '18'")) break;
    await delay(100);
  }
  const desktop = await evaluate(`({moisture: document.getElementById('moisture-value').textContent, state: document.getElementById('connection').textContent, alerts: document.getElementById('alerts').textContent, source: document.getElementById('source-note').textContent, rows: document.querySelectorAll('#history-body tr').length, overflow: document.documentElement.scrollWidth > innerWidth})`);
  assert(desktop.moisture === '18', 'Stored moisture did not reach the rendered card.');
  assert(desktop.alerts.includes('Dry soil') && desktop.alerts.includes('High temperature'), 'Concurrent browser warning text missing.');
  assert(desktop.source.includes('synthetic'), 'Simulation provenance not visible.');
  assert(!desktop.overflow, 'Desktop page overflows the viewport.');
  const redesign = await evaluate(`({gauge:document.getElementById('gauge-value').textContent, samples:Number(document.getElementById('total-samples').textContent.replaceAll(',','')), title:document.title})`);
  assert(redesign.gauge === '2/4', 'Condition overview did not reflect dry and heat warnings.');
  await evaluate("document.getElementById('toggle-history').click()");
  const expandedRows = await evaluate("document.querySelectorAll('#history-body tr').length");
  assert(expandedRows === Math.min(redesign.samples,60), 'View all did not expand reading history.');
  await evaluate("document.getElementById('history-filter').value='High temperature';document.getElementById('history-filter').dispatchEvent(new Event('input'))");
  assert((await evaluate("document.querySelectorAll('#history-body tr').length")) === 1, 'History warning filter did not find the latest heat sample.');
  await evaluate("document.getElementById('history-filter').value='';document.getElementById('history-filter').dispatchEvent(new Event('input'));document.getElementById('toggle-history').click();document.getElementById('history-window').value='10';document.getElementById('history-window').dispatchEvent(new Event('change'))");
  assert((await evaluate("document.getElementById('trend-chart').getAttribute('aria-label')")).includes(`${Math.min(redesign.samples,10)} recent samples`), 'Sample range selector did not change the chart.');
  await evaluate("document.getElementById('history-window').value='60';document.getElementById('history-window').dispatchEvent(new Event('change'))");
  await evaluate("document.getElementById('chart-metric').value = 'ph'; document.getElementById('chart-metric').dispatchEvent(new Event('change'))");
  assert((await evaluate("document.getElementById('chart-legend').textContent")).includes('Soil pH'), 'Chart selector did not update.');
  await evaluate("document.getElementById('chart-metric').value='moisture';document.getElementById('chart-metric').dispatchEvent(new Event('change'))");
  const screenshot = await command('Page.captureScreenshot', {format: 'png', captureBeyondViewport: true});
  await fs.writeFile(path.join(outputDirectory, `${imagePrefix}_dashboard_desktop.png`), Buffer.from(screenshot.data, 'base64'));
  await command('Emulation.setDeviceMetricsOverride', {width: 390, height: 844, deviceScaleFactor: 1, mobile: true});
  await delay(250);
  const mobile = await evaluate('({width: innerWidth, scrollWidth: document.documentElement.scrollWidth})');
  assert(mobile.scrollWidth <= mobile.width, 'Mobile page overflows the viewport.');
  const mobileShot = await command('Page.captureScreenshot', {format: 'png', captureBeyondViewport: true});
  await fs.writeFile(path.join(outputDirectory, `${imagePrefix}_dashboard_mobile.png`), Buffer.from(mobileShot.data, 'base64'));
  // Use the actual API-derived timestamp. Moving the browser clock tests elapsed-age UI without a long sleep.
  await evaluate('window.originalDateNow = Date.now; Date.now = () => window.originalDateNow() + 30000; updateFreshness()');
  assert((await evaluate("document.getElementById('connection').textContent")) === 'Stale data', 'Age indicator did not become stale.');
  await evaluate('Date.now = window.originalDateNow');
  // Take the browser network offline and invoke the real fetch failure handler.
  await command('Network.enable');
  await command('Network.emulateNetworkConditions', {offline: true, latency: 0, downloadThroughput: 0, uploadThroughput: 0});
  await evaluate('refresh()');
  const offline = await evaluate("({state: document.getElementById('connection').textContent, moisture: document.getElementById('moisture-value').textContent})");
  assert(offline.state === 'Disconnected' && offline.moisture === '18', 'Disconnected state did not preserve previous values.');
  await command('Network.emulateNetworkConditions', {offline: false, latency: 0, downloadThroughput: -1, uploadThroughput: -1});
  // Follow real links, rather than changing classes or scrolling to sections.
  const pages = [
    {page: 'dashboard', path: '/'}, {page: 'sensors', path: '/sensors'},
    {page: 'trends', path: '/trends'}, {page: 'warnings', path: '/warnings'},
    {page: 'history', path: '/history'}, {page: 'system', path: '/system'}
  ];
  const waitForPage = async (page, previousOrigin = null) => {
    for (let attempt = 0; attempt < 100; attempt++) {
      try {
        if (await evaluate(`document.body?.dataset.page === ${JSON.stringify(page)} && performance.timeOrigin !== ${JSON.stringify(previousOrigin)} && typeof latestOverview !== 'undefined' && latestOverview?.latest !== null && latestOverview?.latest !== undefined`)) return;
      } catch { /* navigation replaces the JavaScript execution context */ }
      await delay(100);
    }
    throw new Error(`Page did not render its live sample: ${page}`);
  };
  const navigation = {};
  for (const viewport of [{name: 'desktop', width: 1440, height: 1100, mobile: false}, {name: 'mobile', width: 390, height: 844, mobile: true}]) {
    await command('Emulation.setDeviceMetricsOverride', {width: viewport.width, height: viewport.height, mobile: viewport.mobile, deviceScaleFactor: 1});
    navigation[viewport.name] = [];
    for (const page of pages) {
      const selector = viewport.mobile ? '.mobile-nav' : '.sidebar';
      const previousOrigin = await evaluate('performance.timeOrigin');
      await evaluate(`document.querySelector(${JSON.stringify(selector + ' a[href="' + page.path + '"]')}).click()`);
      await waitForPage(page.page, previousOrigin);
      const state = await evaluate(`({path: location.pathname, active: document.querySelector(${JSON.stringify(selector + ' a[aria-current="page"]')})?.pathname, heading: document.querySelector('h1')?.textContent, overflow: document.documentElement.scrollWidth > innerWidth, source: document.getElementById('source-note').textContent})`);
      assert(state.path === page.path && state.active === page.path, `Navigation did not open the correct ${viewport.name} page: ${page.path}`);
      assert(!state.overflow, `${page.path} overflows the ${viewport.name} viewport.`);
      assert(state.source.includes('synthetic'), `${page.path} lost the data-source label.`);
      if (page.page === 'sensors') assert((await evaluate("document.getElementById('temperature-value').textContent")) === '42', 'Sensor page lost the temperature value.');
      if (page.page === 'warnings') assert((await evaluate("document.getElementById('alerts').textContent")).includes('High temperature'), 'Warnings page lost the current alerts.');
      if (page.page === 'history') assert((await evaluate("document.querySelectorAll('#history-body tr').length")) === Math.min(redesign.samples, 60), 'History page did not show the fetched sample window.');
      if (!viewport.mobile && page.page !== 'dashboard') {
        const shot = await command('Page.captureScreenshot', {format: 'png', captureBeyondViewport: true});
        await fs.writeFile(path.join(outputDirectory, `${imagePrefix}_${page.page}_desktop.png`), Buffer.from(shot.data, 'base64'));
      }
      navigation[viewport.name].push({page: page.page, path: state.path, result: 'passed'});
    }
  }
  const reloadOrigin = await evaluate('performance.timeOrigin');
  await command('Page.reload');
  await waitForPage('system', reloadOrigin);
  const entries = await command('Page.getNavigationHistory');
  await command('Page.navigateToHistoryEntry', {entryId: entries.entries[entries.currentIndex - 1].id});
  await waitForPage('history');
  assert((await evaluate('location.pathname')) === '/history', 'Browser Back did not restore the previous page.');
  const searchOrigin = await evaluate('performance.timeOrigin');
  await command('Page.navigate', {url: `${baseURL}/history?q=High%20temperature`});
  await waitForPage('history', searchOrigin);
  assert((await evaluate("document.querySelectorAll('#history-body tr').length")) === 1, 'History search URL did not filter the results.');
  // Network errors are expected for this explicit offline experiment.
  const unexpected = errors.filter(error => !/ERR_INTERNET_DISCONNECTED|Failed to load resource|net::ERR/.test(error));
  assert(unexpected.length === 0, `Browser exceptions: ${unexpected.join('; ')}`);
  console.log(JSON.stringify({desktop, mobile, redesign, history_filter: 'passed', history_expand: 'passed', sample_range: 'passed', chart_selector: 'passed', stale_clock_advance: 'passed (browser clock advanced 30s)', offline_network: offline, navigation, direct_reload: 'passed', browser_back: 'passed', search_url: 'passed', unexpected_browser_errors: unexpected}, null, 2));
  await command('Browser.close');
} finally {
  socket?.close();
  if (processHandle.exitCode === null) {
    await Promise.race([new Promise(resolve => processHandle.once('exit', resolve)), delay(3000)]);
    if (processHandle.exitCode === null) processHandle.kill();
  }
}
