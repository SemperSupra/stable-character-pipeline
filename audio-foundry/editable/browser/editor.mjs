// Offline, dependency-free creator editor for a restricted source project.
// This is not a MIDI/DAW replacement, and it never sends project data over a network.
export const CLASSIFICATION = 'PUBLIC_SYNTHETIC_CANDIDATE_NOT_FINAL';
export const SCHEMA = 'editable_audio.v1';
const MIDI_TICKS = 480;
const clone = value => JSON.parse(JSON.stringify(value));
const allowed = new Set(['motor.start_hz','motor.end_hz','motor.gain','bpm']);
function requireKeys(obj, expected) {
  const actual = Object.keys(obj).sort();
  if (actual.length !== expected.length || actual.some((key,i) => key !== [...expected].sort()[i])) throw new Error('Unknown or missing project field');
}
export function validateProject(p) {
  if (!p || typeof p !== 'object' || Array.isArray(p)) throw new Error('Expected a project object');
  requireKeys(p,['schema','id','classification','bpm','beats','sample_rate_hz','motor','notes']);
  if (p.schema !== SCHEMA || p.classification !== CLASSIFICATION || p.id !== 'synthetic_audio_reauthoring') throw new Error('Unsupported project or private asset class');
  if (!Number.isInteger(p.bpm) || p.bpm < 40 || p.bpm > 240 || !Number.isInteger(p.beats) || p.beats < 4 || p.beats > 64 || p.beats % 4 !== 0 || p.sample_rate_hz !== 48000) throw new Error('Unsupported tempo, timebase or sample rate');
  if (!p.motor || typeof p.motor !== 'object') throw new Error('Missing procedural sound source');
  requireKeys(p.motor,['start_hz','end_hz','gain']);
  for (const key of ['start_hz','end_hz']) if (!Number.isFinite(p.motor[key]) || p.motor[key] < 35 || p.motor[key] > 2500) throw new Error('Motor frequency out of range');
  if (!Number.isFinite(p.motor.gain) || p.motor.gain < 0.001 || p.motor.gain > 0.25) throw new Error('Motor gain out of range');
  if (!Array.isArray(p.notes) || p.notes.length < 1 || p.notes.length > 256) throw new Error('Invalid note count');
  let end = 0;
  for (const n of p.notes) {
    requireKeys(n,['pitch','velocity','start_tick','length_tick']);
    if (!Number.isInteger(n.pitch) || n.pitch < 36 || n.pitch > 96 || !Number.isInteger(n.velocity) || n.velocity < 1 || n.velocity > 127 || !Number.isInteger(n.start_tick) || !Number.isInteger(n.length_tick) || n.start_tick < end || n.start_tick % 120 !== 0 || n.length_tick < 120 || n.length_tick % 120 !== 0 || n.start_tick + n.length_tick > p.beats * MIDI_TICKS || Math.floor(n.start_tick/1920) !== Math.floor((n.start_tick+n.length_tick-1)/1920)) throw new Error('Invalid note; overlapping, nonquantized or crosses measure');
    end = n.start_tick + n.length_tick;
  }
  return true;
}
export function readProject(source) {
  if (typeof source !== 'string' || source.length > 1048576) throw new Error('JSON input must be text under 1 MB');
  const value = JSON.parse(source);
  validateProject(value);
  return clone(value);
}
export function applyEdit(current, field, raw) {
  validateProject(current);
  if (typeof field !== 'string' || typeof raw !== 'string' || !/^(?:-?(?:\d+\.?\d*|\.\d+))$/.test(raw)) throw new Error('Invalid edit field or number');
  const n = Number(raw);
  if (!Number.isFinite(n)) throw new Error('Nonfinite edit value');
  const next = clone(current);
  if (allowed.has(field)) {
    if (field === 'bpm') next.bpm = n;
    else next.motor[field.split('.')[1]] = n;
  } else {
    const m = /^note\[(\d+)\]\.(pitch|velocity|start_tick|length_tick)$/.exec(field);
    if (!m) throw new Error('Unknown field');
    const index = Number(m[1]);
    if (index < 0 || index >= next.notes.length || !Number.isInteger(n)) throw new Error('Invalid note index or value');
    next.notes[index][m[2]] = n;
  }
  validateProject(next);
  return next;
}
export function revisionJSON(project) {
  validateProject(project);
  return JSON.stringify(project, null, 2) + '\n';
}
export function changedFields(before, after) {
  validateProject(before);validateProject(after);
  const changed=[];
  if (before.bpm!==after.bpm) changed.push('bpm');
  for (const prop of ['start_hz','end_hz','gain']) if (before.motor[prop]!==after.motor[prop]) changed.push('motor.'+prop);
  const fields=['pitch','velocity','start_tick','length_tick'];
  for(let i=0;i<before.notes.length;i++)for(const prop of fields)if(before.notes[i][prop]!==after.notes[i]?.[prop])changed.push(`note[${i}].${prop}`);
  return changed;
}