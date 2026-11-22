import assert from 'node:assert/strict';
import { createServer } from 'node:http';
import { readFile } from 'node:fs/promises';
import { resolve, extname, sep } from 'node:path';
import { chromium } from 'playwright';

const root = process.cwd();
const localRoot = resolve(root);
const mime = { '.html':'text/html', '.mjs':'text/javascript', '.css':'text/css' };
const server = createServer(async (request,response) => {
  try {
    const pathname = decodeURIComponent(new URL(request.url,'http://127.0.0.1').pathname);
    const target = resolve(localRoot, '.' + pathname);
    if (target !== localRoot && !target.startsWith(localRoot + sep)) {
      response.writeHead(403).end();
      return;
    }
    const body = await readFile(target);
    response.writeHead(200, { 'content-type': mime[extname(target)] || 'application/octet-stream' });
    response.end(body);
  } catch {
    response.writeHead(404).end();
  }
});
await new Promise(resolveListen => server.listen(0,'127.0.0.1',resolveListen));
const address = server.address();
const origin = 'http://127.0.0.1:' + address.port;
const browser = await chromium.launch({ headless:true, args:['--autoplay-policy=no-user-gesture-required'] });
const page = await browser.newPage();
const outsideRequests = [];
const pageErrors = [];
page.on('request',request => { if (!request.url().startsWith(origin + '/')) outsideRequests.push(request.url()); });
page.on('pageerror',error => pageErrors.push(error.message));

function syntheticWav(seconds=3) {
  const rate=48000, channels=1, bits=16, frames=rate*seconds, dataSize=frames*channels*bits/8;
  const bytes=Buffer.alloc(44+dataSize);
  bytes.write('RIFF',0); bytes.writeUInt32LE(36+dataSize,4); bytes.write('WAVE',8);
  bytes.write('fmt ',12); bytes.writeUInt32LE(16,16); bytes.writeUInt16LE(1,20);
  bytes.writeUInt16LE(channels,22); bytes.writeUInt32LE(rate,24);
  bytes.writeUInt32LE(rate*channels*bits/8,28); bytes.writeUInt16LE(channels*bits/8,32);
  bytes.writeUInt16LE(bits,34); bytes.write('data',36); bytes.writeUInt32LE(dataSize,40);
  for (let i=0;i<frames;i++) bytes.writeInt16LE(Math.round(12000*Math.sin(2*Math.PI*440*i/rate)),44+i*2);
  return bytes;
}

try {
  await page.goto(origin + '/browser/index.html');
  await page.locator('#stem_files').setInputFiles([
    {name:'synthetic_motor.wav',mimeType:'audio/wav',buffer:syntheticWav()},
    {name:'synthetic_ticks.wav',mimeType:'audio/wav',buffer:syntheticWav()}
  ]);
  await page.waitForFunction(() => [...document.querySelectorAll('#stem_list audio')].length===2 &&
    [...document.querySelectorAll('#stem_list audio')].every(audio => audio.readyState>=1));
  assert.equal(await page.getByRole('list',{name:'Loaded audio stems'}).count(),1);
  assert.equal(await page.getByRole('listitem').count(),2);
  assert.equal(await page.getByRole('button',{name:'Play Group A from start'}).count(),1);
  assert.equal(await page.getByRole('button',{name:'Pause and reset all'}).count(),1);

  await page.addScriptTag({path:resolve(root,'node_modules/axe-core/axe.min.js')});
  const a11y=await page.evaluate(async () => await axe.run(document.querySelector('#audition')));
  assert.deepEqual(a11y.violations.map(v => ({id:v.id,impact:v.impact,help:v.help,nodes:v.nodes.map(n=>n.target)})),[],
    'axe-core found accessibility violations in the loaded audition controls');

  const players=page.locator('#stem_list audio');
  await page.evaluate(async () => {
    const audio=[...document.querySelectorAll('#stem_list audio')];
    await Promise.all(audio.map(player => new Promise(resolveSeek => {
      player.addEventListener('seeked',resolveSeek,{once:true});
      player.currentTime=0.75;
    })));
  });
  await page.locator('#play_a').focus();
  await page.keyboard.press('Enter');
  await page.getByText(/Playing Group A from time zero/).waitFor();
  assert.deepEqual(await players.evaluateAll(list => list.map(player => !player.paused)),[true,true],
    'keyboard group playback did not start both local stems');
  assert.deepEqual(await players.evaluateAll(list => list.map(player => player.currentTime<0.5)),[true,true],
    'group playback did not reset both stem playheads near time zero');

  const firstSolo=page.locator('.stem-row').first().getByRole('button',{name:'Solo'});
  await firstSolo.focus();
  await page.keyboard.press('Space');
  assert.equal(await firstSolo.getAttribute('aria-pressed'),'true');

  const before=await players.evaluateAll(list => list.map(player => player.src));
  await page.locator('#stem_files').setInputFiles({name:'not-audio.txt',mimeType:'text/plain',buffer:Buffer.from('not audio')});
  await page.getByText(/Previous stems remain loaded/).waitFor();
  assert.equal(await page.locator('.stem-row').count(),2);
  assert.deepEqual(await players.evaluateAll(list => list.map(player => player.src)),before,
    'invalid replacement selection discarded or revoked the previous stems');

  assert.deepEqual(outsideRequests,[],'the browser attempted an external request');
  assert.deepEqual(pageErrors,[],'the page raised an uncaught browser error');
  console.log('audition_browser_keyboard_local_media_a11y_PASS chromium=' + browser.version());
} finally {
  await browser.close();
  await new Promise(resolveClose => server.close(resolveClose));
}
