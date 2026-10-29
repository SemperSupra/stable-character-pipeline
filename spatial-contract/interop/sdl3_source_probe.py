"""Compile verbatim pinned SDL3_mixer position setter under a bounded C probe.

This is a *source-derived unit reproduction*, not a full linked SDL3 runtime
or actual PCM result. Harness collaborators are intentionally explicit stubs.
"""
import hashlib
import json
import pathlib
import subprocess
import sys

EXPECTED_BLOB = "b1ef3f5822df11556733fe916adc896596dbb3f6"
SYMBOL = "bool MIX_SetTrack3DPosition(MIX_Track *track, const MIX_Point3D *position)"
FAULT = "tposition3d[2] != position->y"
REPAIR = "tposition3d[1] != position->y"
C_PREFIX = r"""
#include <stdbool.h>
#include <stddef.h>
#include <stdio.h>
typedef struct { float x, y, z; } MIX_Point3D;
typedef enum { MIX_SPATIALIZATION_NONE = 0, MIX_SPATIALIZATION_3D = 1 } MIX_SpatializationMode;
typedef struct { int vbap2d; } MIX_Mixer;
typedef struct MIX_Track {
    MIX_Mixer *mixer;
    MIX_SpatializationMode spatialization_mode;
    float position3d[3];
    float spatialization_panning[2];
    int spatialization_speakers[2];
} MIX_Track;
static int spatialize_calls;
static bool CheckTrackParam(MIX_Track *track) { return track != NULL; }
static void LockTrack(MIX_Track *track) { (void) track; }
static void UnlockTrack(MIX_Track *track) { (void) track; }
static void SetTrackOutputStreamFormat(MIX_Track *track, void *ptr) {
    (void)track; (void)ptr;
}
static void MIX_Spatialize(const int *vbap, const float *position, float *panning, int *speakers) {
    (void)vbap; (void)position; (void)panning; (void)speakers;
    spatialize_calls++;
}
"""
C_POSTFIX = r"""
int main(void) {
    MIX_Mixer mixer = {0};
    MIX_Track track = {0};
    track.mixer = &mixer;
    track.spatialization_mode = MIX_SPATIALIZATION_3D;
    track.position3d[0] = 0.0f;
    track.position3d[1] = 1.0f;
    track.position3d[2] = 5.0f;
    const MIX_Point3D moved_y = {0.0f, 5.0f, 5.0f};
    if (!MIX_SetTrack3DPosition(&track, &moved_y)) return 2;
#if EXPECT_FIXED
    if (track.position3d[1] != 5.0f || spatialize_calls != 1) return 3;
    puts("CORRECTED_CONTROL_RECOMPUTED");
#else
    if (track.position3d[1] != 1.0f || spatialize_calls != 0) return 4;
    puts("PINNED_UPSTREAM_CONTROL_SKIPPED_Y_UPDATE");
#endif
    /* Positive independent x-change control: the original code must still respond. */
    const MIX_Point3D moved_x = {1.0f, 5.0f, 5.0f};
    if (!MIX_SetTrack3DPosition(&track, &moved_x)) return 5;
#if EXPECT_FIXED
    if (track.position3d[0] != 1.0f || spatialize_calls != 2) return 6;
#else
    if (track.position3d[0] != 1.0f || track.position3d[1] != 5.0f || spatialize_calls != 1) return 7;
#endif
    puts("INDEPENDENT_X_CHANGE_CONTROL_PASS");
    return 0;
}
"""
def exact_function(source):
    if source.count(SYMBOL) != 1:
        raise ValueError("original function not uniquely located")
    a = source.index(SYMBOL)
    b = source.index("{", a)
    depth = 0
    for pos in range(b, len(source)):
        if source[pos] == "{":
            depth += 1
        elif source[pos] == "}":
            depth -= 1
            if depth == 0:
                function = source[a:pos+1]
                if function.count(FAULT)!=1 or function.count(REPAIR)!=0:
                    raise ValueError("upstream source changed; fixed or ambiguous")
                return function
    raise ValueError("function truncated")
def git_blob_sha(payload):
    return hashlib.sha1(b"blob "+str(len(payload)).encode()+b"\\0".replace(b"\\0", b"\x00")+payload).hexdigest()
def main():
    if len(sys.argv)!=3:
        raise SystemExit("usage: sdl3_source_probe.py SDL_MIXER_SOURCE.cpp OUT_DIR")
    src = pathlib.Path(sys.argv[1])
    out = pathlib.Path(sys.argv[2])
    out.mkdir(parents=True, exist_ok=True)
    payload = src.read_bytes()
    sha = git_blob_sha(payload)
    if sha != EXPECTED_BLOB:
        raise ValueError("upstream Git blob SHA source-custody drift: "+sha)
    fn = exact_function(payload.decode("utf-8"))
    rows = []
    for fixed in (False, True):
        basename = "corrected_control" if fixed else "pinned_upstream_control"
        body = fn.replace(FAULT,REPAIR) if fixed else fn
        source = out/(basename+".c")
        source.write_text(C_PREFIX+"\n"+body+"\n"+C_POSTFIX)
        executable = out/basename
        compile = subprocess.run(["cc","-std=c11","-O2","-Wall","-Wextra","-Werror",
                                  "-DEXPECT_FIXED="+("1" if fixed else "0"),
                                  str(source),"-o",str(executable)],
                                  capture_output=True,text=True,timeout=50)
        if compile.returncode!=0:
            raise RuntimeError("first compiler failure "+basename+": "+compile.stderr)
        proc = subprocess.run([str(executable)],capture_output=True,text=True,timeout=20)
        if proc.returncode!=0:
            raise RuntimeError("source-derived harness unexpected "+basename+": "+proc.stdout+" "+proc.stderr)
        rows.append(dict(case=basename,source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                         exit_code=proc.returncode,stdout=proc.stdout.strip()))
    receipt = dict(schema="spatial_audio/sdl3_source_control_probe/1",
                   upstream_repo="libsdl-org/SDL_mixer",
                   upstream_commit="d9478014cddcf00f035c950637917d2280a67ab2",
                   upstream_file="src/SDL_mixer.c",
                   upstream_blob_sha=sha,
                   classification="SOURCE_EXTRACTED_C_HARNESS_NOT_FULL_SDL_RUNTIME",
                   finding="ORIGINAL_SOURCE_Y_UPDATE_SKIPPED_FIX_CONTROL_RECOMPUTES",
                   changed=("old=(0,1,5)","new=(0,5,5)"),
                   test_results=rows, status="PASS_EXPECTED_DEFECT_REPRODUCED")
    (out/"receipt.json").write_text(json.dumps(receipt,sort_keys=True,indent=2)+"\n")
    print("SDL3_SOURCE_DERIVED_REPRO_PASS",json.dumps(receipt,sort_keys=True))
if __name__=="__main__":
    main()
