// Read-only shared Wokwi diagnosis. No account login or project save operation.
import {spawn} from 'node:child_process';
import fs from 'node:fs/promises';
import path from 'node:path';
const directory = path.resolve('instance/wokwi-debug-479554649720488961');
await fs.mkdir(directory, {recursive: true});
const profile = path.join(directory, 'browser-profile-' + Date.now());
const delay = ms => new Promise(resolve => setTimeout(resolve, ms));
const child = spawn('C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe', ['--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check', '--remote-debugging-port=0', `--user-data-dir=${profile}`, 'about:blank'], {windowsHide: true, stdio: 'ignore'});
let socket;
try {
  let port;
  for (let attempt = 0; attempt < 100; attempt++) {
    try {port = Number((await fs.readFile(path.join(profile, 'DevToolsActivePort'), 'utf8')).split('\n')[0]); break;} catch {}
    await delay(100);
  }
  if (!port) throw new Error('Browser startup failed.');
  const tabs = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
  const tab = tabs.find(t => t.type === 'page');
  socket = new WebSocket(tab.webSocketDebuggerUrl);
  await new Promise((resolve,reject) => {socket.onopen=resolve;socket.onerror=reject;});
  let id = 0;
  const pending = new Map(), consoleMessages = [], failures = [], networkFailures = [], buildResponses = [];
  socket.onmessage = event => {
    const message = JSON.parse(event.data);
    if (message.id && pending.has(message.id)) {
      const item = pending.get(message.id); pending.delete(message.id); clearTimeout(item.timer);
      message.error ? item.reject(new Error(message.error.message)) : item.resolve(message.result);
    }
    if (message.method === 'Runtime.consoleAPICalled') consoleMessages.push({type: message.params.type, text: message.params.args.map(a => a.value ?? a.description ?? '').join(' ')});
    if (message.method === 'Runtime.exceptionThrown') failures.push(message.params.exceptionDetails);
    if (message.method === 'Network.loadingFailed') networkFailures.push({error:message.params.errorText,type:message.params.type});
    if (message.method === 'Network.responseReceived' && /build|compil|firmware|\.elf|\.bin/.test(message.params.response.url)) buildResponses.push({requestId:message.params.requestId,url:message.params.response.url,status:message.params.response.status,mimeType:message.params.response.mimeType});
  };
  const command = (method, params={}) => new Promise((resolve,reject) => {
    const requestId = ++id;
    const timer = setTimeout(() => {pending.delete(requestId); reject(new Error(method + ' timed out'));},15000);
    pending.set(requestId,{resolve,reject,timer});socket.send(JSON.stringify({id:requestId,method,params}));
  });
  const evaluate = async expression => {
    const result = await command('Runtime.evaluate',{expression,awaitPromise:true,returnByValue:true});
    if(result.exceptionDetails) throw new Error(JSON.stringify(result.exceptionDetails));
    return result.result.value;
  };
  await command('Runtime.enable');await command('Page.enable');await command('Network.enable');
  await command('Emulation.setDeviceMetricsOverride',{width:1500,height:1050,deviceScaleFactor:1,mobile:false});
  await command('Page.navigate',{url:'https://wokwi.com/projects/479554649720488961'});
  let state;
  for(let attempt=0;attempt<60;attempt++) {
    await delay(500);
    state=await evaluate(`({title:document.title,ready:document.readyState,buttons:[...document.querySelectorAll('button')].map(b=>({text:b.textContent.trim().slice(0,80),title:b.title,aria:b.getAttribute('aria-label'),testid:b.getAttribute('data-testid')})),frames:[...document.querySelectorAll('iframe')].map(f=>f.src),body:document.body.innerText.slice(-5000)})`);
    if(await evaluate(`(()=>{const b=[...document.querySelectorAll('button')].find(b=>/start.*simul/i.test(b.title+' '+b.getAttribute('aria-label')+' '+b.textContent));if(!b)return false;const key=Object.keys(b).find(k=>k.startsWith('__reactProps'));return !!key && typeof b[key].onClick==='function';})()`)) break;
  }
  console.log('Page ready:',JSON.stringify({title:state.title,ready:state.ready,buttons:state.buttons,frames:state.frames}));
  if(process.argv.includes('--run')) {
    const clicked=await evaluate(`(()=>{const b=[...document.querySelectorAll('button')].find(b=>/start.*simul/i.test(b.title+' '+b.getAttribute('aria-label')+' '+b.textContent));if(!b)return false;b.click();return true;})()`);
    if(!clicked) throw new Error('Could not identify the Start Simulation button.');
    console.log('Simulation requested; observing build/startup.');
    let lastText='';
    for(let attempt=0;attempt<600;attempt++) {
      await delay(1000);
      const text=await evaluate(`(()=>{const body=document.body.cloneNode(true);body.querySelectorAll('script,style,pre,.monaco-editor,[class*="sourceCodePreview"]').forEach(n=>n.remove());return body.textContent.slice(-14000);})()`);
      if(attempt%15===0) console.log('Observation:',text.slice(-2500));
      lastText=text;
      if(/assert failed|Guru Meditation|\[MQTT\] SENT|Build failed!/i.test(text)) {console.log('Terminal condition:',text.slice(-6000));break;}
    }
    await fs.writeFile(path.join(directory,'observed-page.txt'),lastText);
  }
  await fs.writeFile(path.join(directory,'browser-diagnostics.json'),JSON.stringify({state,consoleMessages,failures,networkFailures,buildResponses},null,2));
  const screenshot=await command('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
  await fs.writeFile(path.join(directory,'browser.png'),Buffer.from(screenshot.data,'base64'));
  await command('Browser.close');
} finally {
  socket?.close();
  if(child.exitCode===null){await Promise.race([new Promise(resolve=>child.once('exit',resolve)),delay(3000)]);if(child.exitCode===null)child.kill();}
}
