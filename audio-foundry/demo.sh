#!/usr/bin/env bash
# Public-safe, original synthetic audio fixture. NOT a production audio engine.
set -Eeuo pipefail
if (( $# != 1 )); then echo "Usage: $0 NEW_OUTPUT_DIRECTORY" >&2; exit 2; fi
OUT="$1"
[[ ! -e "$OUT" ]] || { echo 'Refusing to overwrite existing output directory' >&2; exit 2; }
command -v ffmpeg >/dev/null || { echo 'ffmpeg is required' >&2; exit 2; }
command -v ffprobe >/dev/null || { echo 'ffprobe is required' >&2; exit 2; }
if command -v espeak-ng >/dev/null; then TTS=espeak-ng
elif command -v espeak >/dev/null; then TTS=espeak
else echo 'espeak-ng or espeak is required' >&2; exit 2; fi
mkdir -p "$OUT"
trap 'echo "First failure at line $LINENO" >&2' ERR

"$TTS" -v en-us+f3 -s 148 -p 52 -w "$OUT/human_raw.wav"   'The wind moves through the trees, and birds call in the distance.'
"$TTS" -v en-us+f3 -s 145 -p 39 -w "$OUT/robot_raw.wav"   'Systems nominal. Environmental recording complete.'

# Sound stems are exactly 12 seconds of 48kHz stereo PCM, aligned by scene clock.
ffmpeg -hide_banner -loglevel error -nostdin -y -f lavfi -i 'anoisesrc=c=pink:r=48000:d=12:seed=41'   -af 'lowpass=f=900,volume=0.07,afade=t=in:st=0:d=1,afade=t=out:st=10.5:d=1.5'   -ar 48000 -ac 2 -c:a pcm_s16le "$OUT/ambience_wind.wav"
ffmpeg -hide_banner -loglevel error -nostdin -y -f lavfi -i   'aevalsrc=0.011*sin(2*PI*130.81*t)+0.007*sin(2*PI*196*t)+0.005*sin(2*PI*261.63*t)+0.008*sin(2*PI*329.63*t)*cos(2*PI*0.25*t):s=48000:d=12'   -af 'lowpass=f=1800,afade=t=in:st=0:d=1.2,afade=t=out:st=10:d=2'   -ar 48000 -ac 2 -c:a pcm_s16le "$OUT/music_pad.wav"
# Bird-like synthetic chirps. No species identity claims.
ffmpeg -hide_banner -loglevel error -nostdin -y -f lavfi -i   'aevalsrc=0.042*sin(2*PI*(1800*t+1200*t*t))*if(lt(mod(t\,1.7)\,0.19)\,1\,0):s=48000:d=12'   -af 'highpass=f=900,volume=0.8,afade=t=in:st=0:d=0.4,afade=t=out:st=11:d=1'   -ar 48000 -ac 2 -c:a pcm_s16le "$OUT/fauna_chirps.wav"
# Periodic synthetic contact pulses. Not biomechanically modeled footfalls.
ffmpeg -hide_banner -loglevel error -nostdin -y -f lavfi -i   'aevalsrc=0.06*sin(2*PI*85*t)*if(lt(mod(t\,0.68)\,0.12)\,pow(sin(PI*mod(t\,0.68)/0.12)\,2)\,0):s=48000:d=12'   -af 'lowpass=f=400,volume=0.5'   -ar 48000 -ac 2 -c:a pcm_s16le "$OUT/foley_texture.wav"

ffmpeg -hide_banner -loglevel error -nostdin -y -i "$OUT/human_raw.wav"   -af 'aresample=48000,volume=0.52,adelay=1800:all=1,apad,atrim=0:12'   -ar 48000 -ac 2 -c:a pcm_s16le "$OUT/human_voice.wav"
ffmpeg -hide_banner -loglevel error -nostdin -y -i "$OUT/robot_raw.wav"   -af 'aresample=48000,highpass=f=220,lowpass=f=2900,acrusher=bits=8:mode=lin:mix=0.35,volume=0.48,adelay=7600:all=1,apad,atrim=0:12'   -ar 48000 -ac 2 -c:a pcm_s16le "$OUT/robot_voice.wav"
ffmpeg -hide_banner -loglevel error -nostdin -y   -i "$OUT/ambience_wind.wav" -i "$OUT/music_pad.wav" -i "$OUT/fauna_chirps.wav"   -i "$OUT/foley_texture.wav" -i "$OUT/human_voice.wav" -i "$OUT/robot_voice.wav"   -filter_complex '[0:a][1:a][2:a][3:a][4:a][5:a]amix=inputs=6:duration=longest:normalize=0,alimiter=limit=0.92[a]'   -map '[a]' -ar 48000 -ac 2 -c:a pcm_s16le "$OUT/full_mix.wav"

SCRIPT_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
(cd "$SCRIPT_DIR" && go run ./cmd/verify "$OUT" "$TTS")
