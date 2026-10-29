/* Full native linked SDL3 + SDL3_mixer CPU-only MIX_Generate regression.
 * No SDL_mixer source modifications. All input PCM is self-authored and public.
 */
#include <SDL3/SDL.h>
#include <SDL3_mixer/SDL_mixer.h>
#include <stdio.h>
#include <stdlib.h>
#include <math.h>

enum { RATE=48000, FRAMES=4096, CHANNELS=2 };
typedef struct {
    const char *name;
    MIX_Point3D initial;
    MIX_Point3D updated;
    bool update;
    MIX_Point3D expected;
} Case;
static int die(const char *where) {
    fprintf(stderr,"SDL3_NATIVE_FIRST_FAILURE %s: %s\n",where,SDL_GetError());
    return 1;
}
static int render(const char *wav,const char *dir,const Case *test) {
    const SDL_AudioSpec spec={SDL_AUDIO_F32, CHANNELS, RATE};
    MIX_Mixer *mixer=MIX_CreateMixer(&spec);
    if(!mixer)return die("create mixer");
    MIX_Track *track=MIX_CreateTrack(mixer);
    if(!track)return die("create track");
    MIX_Audio *audio=MIX_LoadAudio(mixer,wav,true);
    if(!audio)return die("load source WAV");
    if(!MIX_SetTrackAudio(track,audio))return die("assign source");
    if(!MIX_SetTrack3DPosition(track,&test->initial))return die("initial position");
    if(test->update && !MIX_SetTrack3DPosition(track,&test->updated))return die("updated position");
    MIX_Point3D actual;
    if(!MIX_GetTrack3DPosition(track,&actual))return die("get current position");
    if(actual.x!=test->expected.x || actual.y!=test->expected.y || actual.z!=test->expected.z) {
        fprintf(stderr,"SDL3_NATIVE_FIRST_FAILURE unexpected actual position %s: %.5f,%.5f,%.5f\n",
               test->name,actual.x,actual.y,actual.z);
        return 2;
    }
    if(!MIX_PlayTrack(track,0))return die("play original source");
    float *out=(float*)calloc((size_t)FRAMES*CHANNELS,sizeof(float));
    if(!out)return 3;
    const int bytes=MIX_Generate(mixer,out,(int)((size_t)FRAMES*CHANNELS*sizeof(float)));
    if(bytes!=(int)((size_t)FRAMES*CHANNELS*sizeof(float))) {
        fprintf(stderr,"SDL3_NATIVE_FIRST_FAILURE incomplete mixed bytes %d\n",bytes);
        free(out);return 4;
    }
    char pathname[4096];
    if(snprintf(pathname,sizeof(pathname),"%s/%s.f32",dir,test->name)>= (int)sizeof(pathname))return 5;
    FILE *file=fopen(pathname,"wbx");
    if(!file)return 6;
    size_t written=fwrite(out,sizeof(float),(size_t)FRAMES*CHANNELS,file);
    int cls=fclose(file);
    double energy=0,peak=0;
    for(size_t i=0;i<(size_t)FRAMES*CHANNELS;i++) {
        double sample=(double)out[i];
        if(!isfinite(sample))return 7;
        energy+=sample*sample;
        if(fabs(sample)>peak)peak=fabs(sample);
    }
    free(out);
    MIX_DestroyTrack(track);
    MIX_DestroyAudio(audio);
    MIX_DestroyMixer(mixer);
    if(written!=(size_t)FRAMES*CHANNELS || cls || energy<1e-9 || peak>1) {
        fprintf(stderr,"SDL3_NATIVE_FIRST_FAILURE output invalid %s peak=%.8g energy=%.8g\n",
               test->name,peak,energy);
        return 8;
    }
    printf("SDL3_REAL_PCM_PASS case=%s actual_xyz=%.2f,%.2f,%.2f frames=%d peak=%.8g energy=%.8g\n",
           test->name,actual.x,actual.y,actual.z,FRAMES,peak,energy);
    return 0;
}
int main(int argc,char **argv) {
    if(argc!=3) {
        fputs("usage: sdl3_full_native SOURCE.wav OUTPUT_DIR\n",stderr);
        return 1;
    }
    if(!SDL_Init(SDL_INIT_AUDIO))return die("SDL init");
    if(!MIX_Init())return die("MIX init");
    const Case tests[]={
        {"fresh_y1",{0,1,5},{0,0,0},false,{0,1,5}},
        {"stale_y_update",{0,1,5},{0,5,5},true,{0,1,5}},
        {"fresh_y5",{0,5,5},{0,0,0},false,{0,5,5}},
        {"positive_x_update",{0,1,5},{1,5,5},true,{1,5,5}}
    };
    int status=0;
    for(size_t i=0;i<sizeof(tests)/sizeof(tests[0]);i++) {
        status=render(argv[1],argv[2],&tests[i]);
        if(status)break;
    }
    MIX_Quit();
    SDL_Quit();
    return status;
}
