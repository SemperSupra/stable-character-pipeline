// Local-only stem audition controls. This module never fetches or transmits audio.
export const PUBLIC_CLASSIFICATION = 'PUBLIC_SYNTHETIC_CANDIDATE_NOT_FINAL';
export function validateAudioFiles(files) {
  if (files.length > 32) return 'Load at most 32 stems at once.';
  if (files.some(file => !file.type.startsWith('audio/') && !/\.(wav|m4a|mp3|ogg|flac)$/i.test(file.name))) return 'Choose audio stem files only.';
  return null;
}
export function createAuditionState(files = []) {
  const tracks = files.map((file, index) => ({
    id: String(index), name: file.name, file, url: null, muted: false, group: 'A'
  }));
  return { tracks, soloId: null, playing: false };
}
export function setSolo(state, id) {
  if (!state.tracks.some(track => track.id === id)) throw new Error('Unknown stem');
  return { ...state, soloId: state.soloId === id ? null : id };
}
export function setMuted(state, id, muted) {
  if (!state.tracks.some(track => track.id === id)) throw new Error('Unknown stem');
  return { ...state, tracks: state.tracks.map(track => track.id === id ? { ...track, muted: Boolean(muted) } : track) };
}
export function setGroup(state, id, group) {
  if (!['A','B'].includes(group) || !state.tracks.some(track => track.id === id)) throw new Error('Invalid stem group');
  return { ...state, tracks: state.tracks.map(track => track.id === id ? { ...track, group } : track) };
}
export function isAudible(state, track) {
  return !track.muted && (!state.soloId || state.soloId === track.id);
}
export function selectedGroup(state, group) {
  return state.tracks.filter(track => track.group === group && isAudible(state, track));
}
export function disposeAudition(state) {
  for (const track of state.tracks) if (track.url) URL.revokeObjectURL(track.url);
}
export function mountAudition(root = document.getElementById('audition')) {
  if (!root) return;
  const fileInput = root.querySelector('#stem_files');
  const list = root.querySelector('#stem_list');
  const status = root.querySelector('#audition_status');
  const playA = root.querySelector('#play_a');
  const playB = root.querySelector('#play_b');
  const stop = root.querySelector('#stop_compare');
  const players = new Map();
  let state = createAuditionState();
  let generation = 0;
  let activePreparation = null;
  const say = text => { status.textContent = text; };
  function invalidatePlayback() {
    generation += 1;
    activePreparation?.abort();
    activePreparation = null;
  }
  function stopAll(reset = true, invalidate = true) {
    if (invalidate) invalidatePlayback();
    for (const audio of players.values()) {
      audio.pause();
      if (reset && audio.readyState >= HTMLMediaElement.HAVE_METADATA) audio.currentTime = 0;
    }
    state = { ...state, playing: false };
  }
  function waitForEvent(audio, eventName, signal) {
    if (eventName === 'loadedmetadata' && audio.readyState >= HTMLMediaElement.HAVE_METADATA) return Promise.resolve();
    return new Promise((resolve, reject) => {
      const cleanup = () => {
        audio.removeEventListener(eventName, onReady);
        audio.removeEventListener('error', onError);
        signal.removeEventListener('abort', onAbort);
      };
      const onReady = () => { cleanup(); resolve(); };
      const onError = () => { cleanup(); reject(new Error('Audio source failed to load')); };
      const onAbort = () => { cleanup(); reject(new DOMException('Playback preparation cancelled', 'AbortError')); };
      audio.addEventListener(eventName, onReady, { once: true });
      audio.addEventListener('error', onError, { once: true });
      signal.addEventListener('abort', onAbort, { once: true });
    });
  }
  async function prepareFromZero(audio, signal) {
    await waitForEvent(audio, 'loadedmetadata', signal);
    if (audio.currentTime === 0) return;
    const seeking = waitForEvent(audio, 'seeked', signal);
    audio.currentTime = 0;
    await seeking;
  }
  async function playGroup(group) {
    const selected = selectedGroup(state, group);
    if (!selected.length) { say(`Assign at least one audible stem to Group ${group}.`); return; }
    stopAll(true);
    const thisGeneration = generation;
    const controller = new AbortController();
    activePreparation = controller;
    const entries = selected.map(track => players.get(track.id)).filter(Boolean);
    if (entries.length !== selected.length) {
      stopAll(true);
      say('A selected stem is unavailable. Load the local audio files again.');
      return;
    }
    try {
      await Promise.all(entries.map(audio => prepareFromZero(audio, controller.signal)));
      if (thisGeneration !== generation) return;
      activePreparation = null;
      // Start all ready players in one task after every source has sought to zero.
      const results = await Promise.allSettled(entries.map(audio => audio.play()));
      if (thisGeneration !== generation) return;
      const rejected = results.some(result => result.status === 'rejected');
      if (rejected) { stopAll(true); say('Playback was blocked. Use the audio player controls or check browser permission.'); return; }
      state = { ...state, playing: true };
      say(`Playing Group ${group} from time zero. Browser scheduling may vary; perception and device acceptance are not recorded.`);
    } catch (error) {
      controller.abort();
      if (activePreparation === controller) activePreparation = null;
      if (thisGeneration !== generation) return;
      stopAll(true);
      say(error?.name === 'AbortError' ? 'Playback preparation cancelled.' : 'A stem could not be loaded or positioned. Check the local audio files.');
    }
  }
  async function playTrack(id) {
    const track = state.tracks.find(item => item.id === id);
    const audio = players.get(id);
    if (!track || !audio) { say('The selected stem is unavailable.'); return; }
    stopAll(true);
    const thisGeneration = generation;
    const controller = new AbortController();
    activePreparation = controller;
    try {
      await prepareFromZero(audio, controller.signal);
      if (thisGeneration !== generation) return;
      activePreparation = null;
      await audio.play();
      if (thisGeneration !== generation) { audio.pause(); return; }
      state = { ...state, playing: true };
      say(`Playing ${track.name} from time zero. Perception and device acceptance are not recorded.`);
    } catch (error) {
      controller.abort();
      if (activePreparation === controller) activePreparation = null;
      if (thisGeneration !== generation) return;
      stopAll(true);
      say(error?.name === 'AbortError' ? 'Playback preparation cancelled.' : 'A stem could not be loaded or played.');
    }
  }
  function repaint() {
    for (const track of state.tracks) {
      const audio = players.get(track.id);
      if (!audio) continue;
      audio.muted = !isAudible(state, track);
      const row = list.querySelector(`[data-track-id="${CSS.escape(track.id)}"]`);
      if (!row) continue;
      row.querySelector('[data-action="solo"]').setAttribute('aria-pressed', String(state.soloId === track.id));
      row.querySelector('[data-action="mute"]').setAttribute('aria-pressed', String(track.muted));
      row.querySelector('[data-action="group"]').value = track.group;
    }
  }
  function render() {
    list.replaceChildren();
    for (const track of state.tracks) {
      if (!track.url) track.url = URL.createObjectURL(track.file);
      const audio = document.createElement('audio');
      audio.src = track.url; audio.preload = 'metadata';
      audio.setAttribute('aria-hidden', 'true');
      audio.addEventListener('ended', () => {
        if (![...players.values()].some(entry => !entry.paused)) state = { ...state, playing: false };
      });
      const row = document.createElement('div'); row.className = 'stem-row'; row.setAttribute('role', 'listitem'); row.dataset.trackId = track.id;
      const title = document.createElement('strong'); title.textContent = track.name;
      const preview = document.createElement('button'); preview.type = 'button'; preview.textContent = 'Preview'; preview.setAttribute('aria-label', `Preview stem: ${track.name}`); preview.dataset.action = 'preview';
      preview.addEventListener('click', () => playTrack(track.id));
      const solo = document.createElement('button'); solo.type = 'button'; solo.textContent = 'Solo'; solo.dataset.action = 'solo'; solo.setAttribute('aria-pressed', 'false');
      solo.addEventListener('click', () => { stopAll(false); state = setSolo(state, track.id); repaint(); say(state.soloId ? `Soloing ${track.name}` : 'Solo cleared'); });
      const mute = document.createElement('button'); mute.type = 'button'; mute.textContent = 'Mute'; mute.dataset.action = 'mute'; mute.setAttribute('aria-pressed', 'false');
      mute.addEventListener('click', () => { stopAll(false); state = setMuted(state, track.id, !track.muted); repaint(); say(`${track.name} ${track.muted ? 'muted' : 'unmuted'}`); });
      const group = document.createElement('select'); group.dataset.action = 'group'; group.setAttribute('aria-label', `A/B group for ${track.name}`);
      for (const value of ['A','B']) { const option=document.createElement('option'); option.value=value; option.textContent=`Group ${value}`; group.appendChild(option); }
      group.value = track.group;
      group.addEventListener('change', () => { stopAll(false); state = setGroup(state, track.id, group.value); repaint(); say(`${track.name} assigned to Group ${group.value}`); });
      row.append(title, preview, solo, mute, group, audio); list.appendChild(row);
      players.set(track.id, audio);
    }
    repaint();
  }
  fileInput.addEventListener('change', () => {
    const files = [...fileInput.files];
    const validationError = validateAudioFiles(files);
    if (validationError) {
      fileInput.value = '';
      say(validationError + ' Previous stems remain loaded.');
      return;
    }
    stopAll();
    for (const track of state.tracks) if (track.url) URL.revokeObjectURL(track.url);
    players.clear();
    state = createAuditionState(files);
    render();
    say(files.length ? `${files.length} local stems loaded. Set A/B groups, solo or mute. Files remain in this browser session.` : 'No stems selected.');
  });
  playA.addEventListener('click', () => playGroup('A'));
  playB.addEventListener('click', () => playGroup('B'));
  stop.addEventListener('click', () => { generation++; stopAll(); say('All stems paused and reset to time zero.'); });
  window.addEventListener('pagehide', () => { stopAll(); for (const track of state.tracks) if (track.url) URL.revokeObjectURL(track.url); });
}
