import test from 'node:test';
import assert from 'node:assert/strict';
import { mountAudition } from './audition.mjs';

// Deterministic media settlement scheduler; no microphone, device or network.
class Element extends EventTarget {
  constructor(tag='div') {
    super(); this.tag=tag; this.children=[]; this.dataset={}; this.files=[];
    this.value=''; this.textContent=''; this.attributes={};
  }
  append(...entries) { this.children.push(...entries); }
  appendChild(entry) { this.append(entry); return entry; }
  replaceChildren(...entries) { this.children=entries; }
  setAttribute(k,v) { this.attributes[k]=v; }
  querySelector(selector) {
    const match=selector.match(/^\[data-(track-id|action)="([^"]+)"\]$/);
    if (!match) return null;
    const key=match[1]==='track-id'?'trackId':'action';
    return this.children.find(e=>e.dataset[key]===match[2])??null;
  }
  click() { this.dispatchEvent(new Event('click')); }
}
class Media extends Element {
  constructor() { super('audio'); this.readyState=1; this.currentTime=0; this.paused=true; this.pending=[]; }
  pause() { this.paused=true; }
  play() {
    return new Promise((resolve,reject)=>this.pending.push({
      resolve:()=>{this.paused=false;resolve();},
      reject:()=>reject(new Error('controlled play rejection'))
    }));
  }
}
const tick=()=>new Promise(resolve=>setImmediate(resolve));
async function fixture() {
  const controls=new Map(['#stem_files','#stem_list','#audition_status','#play_a','#play_b','#stop_compare'].map(k=>[k,new Element()]));
  const root={querySelector:k=>controls.get(k)};
  globalThis.document={createElement:tag=>tag==='audio'?new Media():new Element(tag)};
  globalThis.window=new EventTarget();
  globalThis.HTMLMediaElement={HAVE_METADATA:1};
  globalThis.CSS={escape:String};
  mountAudition(root);
  const file=new Blob([new Uint8Array(8)],{type:'audio/wav'});Object.defineProperty(file,'name',{value:'original.wav'});
  controls.get('#stem_files').files=[file];
  controls.get('#stem_files').dispatchEvent(new Event('change'));
  const row=controls.get('#stem_list').children[0];
  const media=row.children.find(e=>e.tag==='audio');
  const preview=row.children.find(e=>e.dataset.action==='preview');
  return {media,preview,start:()=>controls.get('#play_a').click(),stop:()=>controls.get('#stop_compare').click(),
    status:()=>controls.get('#audition_status').textContent,
    cleanup:()=>globalThis.window.dispatchEvent(new Event('pagehide'))};
}
async function newerWins(first,second,between=false) {
  const f=await fixture();
  try {
    (first==='group'?f.start:f.preview.click.bind(f.preview))(); await tick();
    assert.equal(f.media.pending.length,1);
    if(between)f.stop();
    (second==='group'?f.start:f.preview.click.bind(f.preview))(); await tick();
    assert.equal(f.media.pending.length,2);
    f.media.pending[1].resolve(); await tick();
    const latest=f.status();
    assert.match(latest,/^Playing /);
    f.media.pending[0].resolve(); await tick();
    assert.equal(f.media.paused,false,'STALE_COMPLETION_PAUSED_NEW_OWNER');
    assert.equal(f.status(),latest,'STALE_STATUS_OVERWRITE');
  } finally { f.cleanup(); }
}
test('older A completion cannot pause newer A',async()=>newerWins('group','group'));
test('older A completion cannot pause A after STOP/restart',async()=>newerWins('group','group',true));
test('older preview completion cannot pause newer group',async()=>newerWins('preview','group'));
test('older group completion cannot pause newer preview',async()=>newerWins('group','preview'));
test('late completion after STOP without successor is quiesced',async()=>{
  const f=await fixture();
  try {
    f.start(); await tick(); f.stop();
    f.media.pending[0].resolve(); await tick();
    assert.equal(f.media.paused,true,'UNOWNED_LATE_PLAY_NOT_QUIESCED');
    assert.match(f.status(),/paused and reset/);
  } finally { f.cleanup(); }
});
test('stale rejection cannot alter current generation',async()=>{
  const f=await fixture();
  try {
    f.preview.click(); await tick(); f.start(); await tick();
    f.media.pending[1].resolve(); await tick(); const latest=f.status();
    f.media.pending[0].reject(); await tick();
    assert.equal(f.media.paused,false);
    assert.equal(f.status(),latest);
  } finally { f.cleanup(); }
});
