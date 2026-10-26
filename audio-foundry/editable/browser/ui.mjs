import {readProject, applyEdit, revisionJSON, changedFields} from './editor.mjs';
const $ = id => document.getElementById(id);
let initial=null, current=null;
function notify(message,error=false){$('status').textContent=message;$('status').classList.toggle('error',error)}
function paint(){
  if (!current) return;
  $('bpm').value=current.bpm;
  $('motor_start').value=current.motor.start_hz;
  $('motor_end').value=current.motor.end_hz;
  $('motor_gain').value=current.motor.gain;
  const index=Number($('note_index').value || 0);
  const n=current.notes[index];
  $('note_pitch').value=n.pitch;$('note_velocity').value=n.velocity;
  $('note_start').value=n.start_tick;$('note_length').value=n.length_tick;
  $('changes').textContent=changedFields(initial,current).join(', ')||'None';
  $('export').disabled=false;$('reset').disabled=false;
}
$('source_file').addEventListener('change',async ev=>{
  try {
    const f=ev.target.files?.[0];if(!f)return;
    if(f.size>1048576)throw new Error('Project exceeds the 1 MB limit');
    const data=readProject(await f.text());
    current=data;initial=readProject(revisionJSON(data));
    const selector=$('note_index');selector.replaceChildren();
    for(let i=0;i<data.notes.length;i++){
      const o=document.createElement('option');o.value=String(i);o.textContent=`Note ${i+1} — MIDI ${data.notes[i].pitch}`;selector.appendChild(o);
    }
    selector.value='0';paint();notify(`${data.notes.length} notes loaded; project remains on this device`);
  }catch(err){notify(`Could not open project: ${err.message}`,true)}
});
$('note_index').addEventListener('change',paint);
$('edit_form').addEventListener('submit',ev=>{
  ev.preventDefault();if(!current)return notify('Load a project first',true);
  try{
    let next=current;
    const changes={bpm:$('bpm').value,'motor.start_hz':$('motor_start').value,'motor.end_hz':$('motor_end').value,'motor.gain':$('motor_gain').value};
    const i=Number($('note_index').value);
    for(const [property,input] of Object.entries({pitch:'note_pitch',velocity:'note_velocity',start_tick:'note_start',length_tick:'note_length'})) changes[`note[${i}].${property}`]=$(input).value;
    for(const [field,value] of Object.entries(changes))next=applyEdit(next,field,value);
    current=next;paint();notify(`Applied ${changedFields(initial,current).length} changed properties. Render with Audio Foundry to hear them.`);
  }catch(err){notify(`Edit rejected: ${err.message}`,true)}
});
$('reset').addEventListener('click',()=>{if(!initial)return;current=readProject(revisionJSON(initial));paint();notify('Restored original project in memory')});
$('export').addEventListener('click',()=>{
  if(!current)return;
  try{
    const raw=revisionJSON(current);
    const href=URL.createObjectURL(new Blob([raw],{type:'application/json'}));
    const link=document.createElement('a');link.href=href;link.download='audio-foundry-project-revision.json';link.hidden=true;document.body.appendChild(link);link.click();link.remove();
    // Preserve object URL only during the direct click. The browser owns download success.
    queueMicrotask(()=>URL.revokeObjectURL(href));
    notify('Browser download requested. File save and playback on your device are not verified.');
  }catch(err){notify(`Export failed: ${err.message}`,true)}
});