/* Source-pinned OpenAL Soft 48k HRTF stage-change native loopback fixture.
 * Synthetic mono PCM16; source and listener changes exactly at 1024-frame
 * callback boundaries. Quantifies *block-control response*, not continuous
 * six-degree-of-freedom motion or physical sound propagation.
 */
#include <AL/al.h>
#include <AL/alc.h>
#include <AL/alext.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <math.h>
#include <string.h>

enum { RATE=48000, FRAMES=8192, HOP=1024, CHANNELS=2 };
typedef struct { const char *name; int mode; } Mode;
static const Mode modes[]={
    {"static_left",0},{"static_right",1},{"source_switch",2},{"listener_switch",3}
};
static int16_t source[FRAMES];
static void synth(void) {
    for(int i=0;i<FRAMES;i++) {
        const double value=.12*sin(2.0*3.14159265358979323846*410.0*(double)i/(double)RATE);
        source[i]=(int16_t)lrint(value*32767.0);
    }
}
static int write_source(const char *root) {
    char path[4096];
    if(snprintf(path,sizeof(path),"%s/original_mono_410_s16le.raw",root)>=(int)sizeof(path))return 1;
    FILE *f=fopen(path,"wbx");
    if(!f)return 2;
    size_t n=fwrite(source,sizeof(int16_t),FRAMES,f);
    int status=fclose(f);
    return (n==FRAMES && status==0)?0:3;
}
static int run(const char *root, const Mode *mode,
   LPALCLOOPBACKOPENDEVICESOFT openloop,
   LPALCISRENDERFORMATSUPPORTEDSOFT supports,
   LPALCRENDERSAMPLESSOFT render, FILE *states) {
    ALCdevice *dev=openloop(NULL);
    if(!dev)return 2;
    if(!supports(dev,RATE,ALC_STEREO_SOFT,ALC_FLOAT_SOFT) ||
        !alcIsExtensionPresent(dev,"ALC_SOFT_HRTF"))return 3;
    const ALCint attrs[]={ALC_FORMAT_CHANNELS_SOFT,ALC_STEREO_SOFT,
        ALC_FORMAT_TYPE_SOFT,ALC_FLOAT_SOFT,ALC_FREQUENCY,RATE,
        ALC_HRTF_SOFT,ALC_TRUE,0};
    ALCcontext *ctx=alcCreateContext(dev,attrs);
    if(!ctx || !alcMakeContextCurrent(ctx))return 4;
    ALCint hrtf_status=0;
    alcGetIntegerv(dev,ALC_HRTF_STATUS_SOFT,1,&hrtf_status);
    if(hrtf_status!=ALC_HRTF_ENABLED_SOFT)return 5;
    ALuint buf=0,voice=0;
    alGenBuffers(1,&buf);
    alBufferData(buf,AL_FORMAT_MONO16,source,sizeof(source),RATE);
    alGenSources(1,&voice);
    alSourcei(voice,AL_BUFFER,(ALint)buf);
    alDistanceModel(AL_NONE);
    alListener3f(AL_POSITION,0,0,0);
    const ALfloat forward_base[6]={0,0,-1,0,1,0};
    const ALfloat forward_right[6]={1,0,0,0,1,0};
    const ALfloat forward_left[6]={-1,0,0,0,1,0};
    alListenerfv(AL_ORIENTATION,forward_base);
    alSource3f(voice,AL_POSITION,mode->mode==1 ? 10:-10,0,-10);
    alSourcePlay(voice);
    if(alGetError()!=AL_NO_ERROR)return 6;
    float *pcm=(float *)calloc((size_t)FRAMES*CHANNELS,sizeof(float));
    if(!pcm)return 7;
    for(int block=0;block<FRAMES/HOP;block++) {
        if(mode->mode==2 && (block==2 || block==4 || block==6)) {
            alSource3f(voice,AL_POSITION,(block==4)?-10:10,0,-10);
        }
        if(mode->mode==3 && (block==2 || block==4 || block==6)) {
            alListenerfv(AL_ORIENTATION,(block==4)?forward_left:forward_right);
        }
        if(alGetError()!=AL_NO_ERROR)return 8;
        render(dev,pcm+(size_t)block*HOP*CHANNELS,HOP);
        if(alcGetError(dev)!=ALC_NO_ERROR)return 9;
    }
    double energy=0,peak=0;
    for(size_t i=0;i<(size_t)FRAMES*CHANNELS;i++) {
        double v=(double)pcm[i];
        if(!isfinite(v))return 10;
        energy+=v*v;
        if(fabs(v)>peak)peak=fabs(v);
    }
    if(peak<=1e-7 || peak>1 || energy<=1e-8)return 11;
    char path[4096];
    if(snprintf(path,sizeof(path),"%s/%s.f32",root,mode->name)>=(int)sizeof(path))return 12;
    FILE *f=fopen(path,"wbx");
    if(!f)return 13;
    size_t nw=fwrite(pcm,sizeof(float),(size_t)FRAMES*CHANNELS,f);
    int close=fclose(f);
    free(pcm);
    if(nw!=(size_t)FRAMES*CHANNELS || close)return 14;
    fprintf(states,"%s\t%d\t%d\t%.12g\t%.12g\n",mode->name,hrtf_status,FRAMES,peak,energy);
    printf("OPENAL_HRTF_MOVEMENT_NATIVE_PASS name=%s hrtf=%d frames=%d peak=%.9g energy=%.9g\n",
        mode->name,hrtf_status,FRAMES,peak,energy);
    alSourceStop(voice);
    alDeleteSources(1,&voice);
    alDeleteBuffers(1,&buf);
    alcMakeContextCurrent(NULL);
    alcDestroyContext(ctx);
    alcCloseDevice(dev);
    return 0;
}
int main(int argc,char**argv) {
    if(argc!=2){fputs("usage: openal_hrtf_motion OUT_DIR\n",stderr);return 2;}
    synth();
    if(write_source(argv[1])){fputs("OPENAL_ORIGINAL_SOURCE_CREATION_FAILED\n",stderr);return 3;}
    if(!alcIsExtensionPresent(NULL,"ALC_SOFT_loopback"))return 4;
    LPALCLOOPBACKOPENDEVICESOFT openloop=
      (LPALCLOOPBACKOPENDEVICESOFT)alcGetProcAddress(NULL,"alcLoopbackOpenDeviceSOFT");
    LPALCISRENDERFORMATSUPPORTEDSOFT supports=
      (LPALCISRENDERFORMATSUPPORTEDSOFT)alcGetProcAddress(NULL,"alcIsRenderFormatSupportedSOFT");
    LPALCRENDERSAMPLESSOFT render=
      (LPALCRENDERSAMPLESSOFT)alcGetProcAddress(NULL,"alcRenderSamplesSOFT");
    if(!openloop||!supports||!render)return 5;
    char path[4096];
    if(snprintf(path,sizeof(path),"%s/hrtf_motion_states.tsv",argv[1])>=(int)sizeof(path))return 6;
    FILE *states=fopen(path,"wx");
    if(!states)return 7;
    for(size_t i=0;i<sizeof(modes)/sizeof(modes[0]);i++) {
        int code=run(argv[1],&modes[i],openloop,supports,render,states);
        fflush(states);
        if(code){
            fprintf(stderr,"OPENAL_HRTF_MOTION_FIRST_FAILURE name=%s code=%d\n",modes[i].name,code);
            fclose(states);
            return code;
        }
    }
    if(fclose(states))return 8;
    puts("OPENAL_HRTF_MOTION_FOUR_PCM_COMPLETE");
    return 0;
}
