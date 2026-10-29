/* First-party bounded OpenAL Soft loopback C probe: no physical audio device.
 * Input: original 48kHz 8192-frame PCM16 mono impulse, no identity/media assets.
 * Output: raw interleaved IEEE float32, format and channel layout in observer.
 * This is an independent DSP engine, not an EBU waveform comparator. */
#include <AL/al.h>
#include <AL/alc.h>
#include <AL/alext.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>

enum { RATE=48000, FRAMES=8192 };
typedef struct {
    const char *name;
    ALCenum layout;
    int channels;
} Profile;
typedef struct { const char *name; float x,z; } Pose;

static int run_one(const Profile *p,const Pose *pose,const char *root,
                   LPALCLOOPBACKOPENDEVICESOFT openloop,
                   LPALCISRENDERFORMATSUPPORTEDSOFT supported,
                   LPALCRENDERSAMPLESSOFT render) {
    ALCdevice *dev=openloop(NULL);
    if(!dev) { fputs("OPENAL_NO_LOOPBACK_DEVICE\n",stderr);return 3; }
    if(!supported(dev,RATE,p->layout,ALC_FLOAT_SOFT)) {
        fprintf(stderr,"OPENAL_UNSUPPORTED_FORMAT %s\n",p->name);
        alcCloseDevice(dev);
        return 2;
    }
    ALCint attrs[]={ ALC_FORMAT_CHANNELS_SOFT,p->layout,
                     ALC_FORMAT_TYPE_SOFT,ALC_FLOAT_SOFT,
                     ALC_FREQUENCY,RATE,0 };
    ALCcontext *ctx=alcCreateContext(dev,attrs);
    if(!ctx || !alcMakeContextCurrent(ctx)) {
        fputs("OPENAL_CREATE_CONTEXT_FAILED\n",stderr);
        if(ctx) alcDestroyContext(ctx);
        alcCloseDevice(dev);
        return 4;
    }
    ALuint buf=0,source=0;
    int16_t impulse[FRAMES]={0};
    impulse[0]=14745;
    alGenBuffers(1,&buf);
    alBufferData(buf,AL_FORMAT_MONO16,impulse,sizeof(impulse),RATE);
    alGenSources(1,&source);
    alSourcei(source,AL_BUFFER,(ALint)buf);
    alDistanceModel(AL_NONE);
    alListener3f(AL_POSITION,0,0,0);
    const ALfloat orientation[6]={0,0,-1,0,1,0};
    alListenerfv(AL_ORIENTATION,orientation);
    alSource3f(source,AL_POSITION,pose->x,0,pose->z);
    alSourcePlay(source);
    if(alGetError()!=AL_NO_ERROR) {
        fputs("OPENAL_SOURCE_SETUP_FAILURE\n",stderr);
        return 5;
    }
    const size_t count=(size_t)FRAMES*(size_t)p->channels;
    float *samples=(float*)calloc(count,sizeof(float));
    if(!samples) return 6;
    render(dev,samples,FRAMES);
    if(alcGetError(dev)!=ALC_NO_ERROR) {
        fputs("OPENAL_RENDER_FAILURE\n",stderr);
        free(samples);return 7;
    }
    char path[4096];
    if(snprintf(path,sizeof(path),"%s/%s_%s.f32",root,p->name,pose->name) >= (int)sizeof(path))
        return 8;
    FILE *out=fopen(path,"wbx");
    if(!out) { fputs("OPENAL_OUTPUT_EXISTS_OR_UNWRITABLE\n",stderr);free(samples);return 9; }
    const size_t written=fwrite(samples,sizeof(float),count,out);
    const int close_status=fclose(out);
    if(written!=count || close_status!=0) {free(samples);return 10;}
    double peak=0,energy=0;
    for(size_t i=0;i<count;i++) {
        if(!isfinite(samples[i])) {free(samples);return 11;}
        const double v=fabs((double)samples[i]);
        if(v>peak)peak=v;
        energy+=(double)samples[i]*samples[i];
    }
    free(samples);
    alSourceStop(source);
    alDeleteSources(1,&source);
    alDeleteBuffers(1,&buf);
    alcMakeContextCurrent(NULL);
    alcDestroyContext(ctx);
    alcCloseDevice(dev);
    if(peak<1e-7 || peak>1.0 || energy<1e-10) {
        fprintf(stderr,"OPENAL_SILENT_OR_CLIPPING %s %s %.8g %.8g\n",p->name,pose->name,peak,energy);
        return 12;
    }
    printf("OPENAL_NATIVE_LOOPBACK_PASS profile=%s pose=%s frames=%d channels=%d peak=%.9g energy=%.9g\n",
           p->name,pose->name,FRAMES,p->channels,peak,energy);
    return 0;
}
int main(int argc,char **argv) {
    if(argc!=2){fputs("usage: openal_loopback_probe OUTPUT_DIR\n",stderr);return 2;}
    if(!alcIsExtensionPresent(NULL,"ALC_SOFT_loopback")) {
        fputs("OPENAL_SOFT_LOOPBACK_EXTENSION_MISSING\n",stderr);
        return 3;
    }
    LPALCLOOPBACKOPENDEVICESOFT openloop =
        (LPALCLOOPBACKOPENDEVICESOFT)alcGetProcAddress(NULL,"alcLoopbackOpenDeviceSOFT");
    LPALCISRENDERFORMATSUPPORTEDSOFT supported =
        (LPALCISRENDERFORMATSUPPORTEDSOFT)alcGetProcAddress(NULL,"alcIsRenderFormatSupportedSOFT");
    LPALCRENDERSAMPLESSOFT render =
        (LPALCRENDERSAMPLESSOFT)alcGetProcAddress(NULL,"alcRenderSamplesSOFT");
    if(!openloop || !supported || !render) {
        fputs("OPENAL_LOOPBACK_ENTRYPOINT_MISSING\n",stderr);return 4;
    }
    const Profile profiles[]={
        {"stereo",ALC_STEREO_SOFT,2},
        {"surround_5_1",ALC_5POINT1_SOFT,6},
        {"surround_7_1",ALC_7POINT1_SOFT,8}
    };
    const Pose poses[]={
        {"left",-10.0f,-10.0f},
        {"right",10.0f,-10.0f},
        {"front",0.0f,-10.0f}
    };
    int16_t impulse[FRAMES]={0};
    impulse[0]=14745;
    char sourcepath[4096];
    if(snprintf(sourcepath,sizeof(sourcepath),"%s/input_48000_s16le.raw",argv[1]) >= (int)sizeof(sourcepath))
        return 5;
    FILE *src=fopen(sourcepath,"wbx");
    if(!src) return 6;
    if(fwrite(impulse,sizeof(int16_t),FRAMES,src)!=(size_t)FRAMES || fclose(src)!=0) return 7;
    for(size_t p=0;p<sizeof(profiles)/sizeof(profiles[0]);p++)
        for(size_t i=0;i<sizeof(poses)/sizeof(poses[0]);i++) {
            const int status=run_one(&profiles[p],&poses[i],argv[1],openloop,supported,render);
            if(status) return status;
        }
    return 0;
}
