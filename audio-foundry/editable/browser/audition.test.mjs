import test from 'node:test';
import assert from 'node:assert/strict';
import {createAuditionState,setSolo,setMuted,setGroup,isAudible,selectedGroup,PUBLIC_CLASSIFICATION,validateAudioFiles} from './audition.mjs';
const files=[{name:'rain.wav'},{name:'birds.wav'},{name:'music.m4a'}];
test('public synthetic label is explicit',()=>assert.equal(PUBLIC_CLASSIFICATION,'PUBLIC_SYNTHETIC_CANDIDATE_NOT_FINAL'));
test('solo and mute isolate the selected local stem',()=>{
 let state=createAuditionState(files);
 assert.equal(selectedGroup(state,'A').length,3);
 state=setSolo(state,'1');
 assert.deepEqual(selectedGroup(state,'A').map(track=>track.name),['birds.wav']);
 state=setMuted(state,'1',true);
 assert.deepEqual(selectedGroup(state,'A'),[]);
 state=setSolo(state,'1');
 assert.equal(selectedGroup(state,'A').length,2);
});
test('A/B assignments remain separate and reject unknown groups',()=>{
 let state=createAuditionState(files);
 state=setGroup(state,'2','B');
 assert.deepEqual(selectedGroup(state,'A').map(track=>track.name),['rain.wav','birds.wav']);
 assert.deepEqual(selectedGroup(state,'B').map(track=>track.name),['music.m4a']);
 assert.throws(()=>setGroup(state,'2','C'),/Invalid/);
});
test('mute and solo compose without mutating the prior state',()=>{
 const original=createAuditionState(files);
 const next=setMuted(setSolo(original,'0'),'1',true);
 assert.equal(original.soloId,null);
 assert.equal(isAudible(next,next.tracks[0]),true);
 assert.equal(isAudible(next,next.tracks[1]),false);
});

test('invalid and oversized replacement selections are rejected',()=>{
 assert.match(validateAudioFiles([{name:'private.txt',type:'text/plain'}]),/audio stem files only/);
 assert.match(validateAudioFiles(Array.from({length:33},(_,i)=>({name:String(i)+'.wav',type:'audio/wav'}))),/32 stems/);
 assert.equal(validateAudioFiles([{name:'motor.wav',type:'audio/wav'}]),null);
});
