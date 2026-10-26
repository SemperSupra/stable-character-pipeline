import test from 'node:test';
import assert from 'node:assert/strict';
import {readProject,applyEdit,revisionJSON,changedFields} from './editor.mjs';
const project={schema:'editable_audio.v1',id:'synthetic_audio_reauthoring',classification:'PUBLIC_SYNTHETIC_CANDIDATE_NOT_FINAL',bpm:120,beats:8,sample_rate_hz:48000,motor:{start_hz:78,end_hz:215,gain:.06},notes:[{pitch:60,start_tick:0,length_tick:480,velocity:82},{pitch:64,start_tick:480,length_tick:480,velocity:80}]};
test('creator edit -> serializable operator/agent project, original unchanged',()=>{
 const src=readProject(JSON.stringify(project));
 let next=applyEdit(src,'note[0].pitch','62');next=applyEdit(next,'motor.end_hz','350');
 assert.deepEqual(changedFields(src,next),['motor.end_hz','note[0].pitch']);
 assert.equal(src.notes[0].pitch,60);
 assert.equal(readProject(revisionJSON(next)).notes[0].pitch,62);
 next=applyEdit(next,'note[0].pitch','60');next=applyEdit(next,'motor.end_hz','215');
 assert.deepEqual(next,src);
});
test('invalid changes blocked before export',()=>{
 for(const [field,value] of [['motor.end_hz','-1'],['note[0].pitch','99'],['note[0].start_tick','300'],['note[0].length_tick','1920'],['nonsense','21'],['bpm','20000'],['note[0].pitch','NaN']]) {
   assert.throws(()=>applyEdit(project,field,value),Error,field);
 }
 const restricted={...project,classification:'PRIVATE_FINAL_CHARACTER_VOICE'};
 assert.throws(()=>readProject(JSON.stringify(restricted)),/private asset class/);
});
test('file parser rejects unknown format and oversized source',()=>{
 assert.throws(()=>readProject('{}'));
 assert.throws(()=>readProject('x'.repeat(1048577)));
});