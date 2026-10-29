/* OpenAL Soft actual HRTF on/off 5-pose loopback batch. Original audio only. */
#include <AL/al.h>
#include <AL/alc.h>
#include <AL/alext.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <math.h>

enum { RATE=48000, FRAMES=8192 };
typedef struct {const char*name;float x,y,z;} Pose;
static const Pose poses[]={
    {"left",-10,0,-10},{"right",10,0,-10},{"front",0,0,-10},
    {"back",0,0,10},{"elevated",0,10,-10}
};
static int render(const char *dir,const Pose *pose,int enable,
                  LPALCLOOPBACKOPENDEVICESOFT openloop,
                  LPALCISRENDERFORMATSUPPORTEDSOFT supports,
                  LPALCRENDERSAMPLESSOFT renderfn,
                  FILE *receipt) {
    ALCdevice *dev=openloop(NULL);
    if(!dev)return 2;
    if(!supports(dev,RATE,ALC_STEREO_SOFT,ALC_FLOAT_SOFT))return 3;
    if(!alcIsExtensionPresent(dev,"ALC_SOFT_HRTF"))return 4;
    ALCint attrs[]={ALC_FORMAT_CHANNELS_SOFT,ALC_STEREO_SOFT,
        ALC_FORMAT_TYPE_SOFT,ALC_FLOAT_SOFT,ALC_FREQUENCY,RATE,
        ALC_HRTF_SOFT,enable?ALC_TRUE:ALC_FALSE,0};
    ALCcontext *ctx=alcCreateContext(dev,attrs);
    if(!ctx || !alcMakeContextCurrent(ctx))return 5;
    ALCint status=0;
    alcGetIntegerv(dev,ALC_HRTF_STATUS_SOFT,1,&status);
    if(alcGetError(dev)!=ALC_NO_ERROR)return 6;
    if(status!=(enable?ALC_HRTF_ENABLED_SOFT:ALC_HRTF_DISABLED_SOFT)){
        fprintf(stderr,"OPENAL_HRTF_NOT_ACTUALLY_ENABLED desired=%d actual=%d pose=%s\n",
                enable,status,pose->name);
        return 7;
    }
    int16_t impulse[FRAMES]={0};
    impulse[0]=14745;
    ALuint buf=0,src=0;
    alGenBuffers(1,&buf);
    alBufferData(buf,AL_FORMAT_MONO16,impulse,sizeof(impulse),RATE);
    alGenSources(1,&src);
    alSourcei(src,AL_BUFFER,(ALint)buf);
    alDistanceModel(AL_NONE);
    alListener3f(AL_POSITION,0,0,0);
    const ALfloat orientation[6]={0,0,-1,0,1,0};
    alListenerfv(AL_ORIENTATION,orientation);
    alSource3f(src,AL_POSITION,pose->x,pose->y,pose->z);
    alSourcePlay(src);
    if(alGetError()!=AL_NO_ERROR)return 8;
    float *samples=(float*)calloc((size_t)FRAMES*2,sizeof(float));
    if(!samples)return 9;
    renderfn(dev,samples,FRAMES);
    if(alcGetError(dev)!=ALC_NO_ERROR)return 10;
    double peak=0,energy=0;
    for(size_t i=0;i<(size_t)FRAMES*2;i++){
        const float s=samples[i];
        if(!isfinite(s))return 11;
        energy+=(double)s*s;
        if(fabs(s)>peak)peak=fabs(s);
    }
    if(energy<1e-9 || peak>1.0)return 12;
    char path[4096];
    if(snprintf(path,sizeof(path),"%s/hrtf_%s_%s.f32",dir,enable?"on":"off",pose->name)>=(int)sizeof(path))return 13;
    FILE *fp=fopen(path,"wbx");
    if(!fp)return 14;
    const size_t written=fwrite(samples,sizeof(float),FRAMES*2,fp);
    const int closed=fclose(fp);
    free(samples);
    if(written!=(size_t)FRAMES*2 || closed)return 15;
    fprintf(receipt,"%s\t%s\t%d\t%.9f\t%.9f\n",enable?"on":"off",pose->name,status,peak,energy);
    printf("OPENAL_HRTF_REAL_PCM_PASS mode=%s pose=%s state=%d peak=%.8g energy=%.8g\n",
           enable?"on":"off",pose->name,status,peak,energy);
    alSourceStop(src);
    alDeleteSources(1,&src);
    alDeleteBuffers(1,&buf);
    alcMakeContextCurrent(NULL);
    alcDestroyContext(ctx);
    alcCloseDevice(dev);
    return 0;
}
int main(int argc,char **argv){
    if(argc!=2){fputs("usage: openal_hrtf_batch OUT_DIR\n",stderr);return 2;}
    if(!alcIsExtensionPresent(NULL,"ALC_SOFT_loopback"))return 3;
    LPALCLOOPBACKOPENDEVICESOFT openloop=
        (LPALCLOOPBACKOPENDEVICESOFT)alcGetProcAddress(NULL,"alcLoopbackOpenDeviceSOFT");
    LPALCISRENDERFORMATSUPPORTEDSOFT supports=
        (LPALCISRENDERFORMATSUPPORTEDSOFT)alcGetProcAddress(NULL,"alcIsRenderFormatSupportedSOFT");
    LPALCRENDERSAMPLESSOFT renderfn=
        (LPALCRENDERSAMPLESSOFT)alcGetProcAddress(NULL,"alcRenderSamplesSOFT");
    if(!openloop || !supports || !renderfn)return 4;
    char path[4096];
    if(snprintf(path,sizeof(path),"%s/hrtf_states.tsv",argv[1])>=(int)sizeof(path))return 5;
    FILE *receipt=fopen(path,"wx");
    if(!receipt)return 6;
    for(int enabled=0;enabled<=1;enabled++){
        for(size_t i=0;i<sizeof(poses)/sizeof(poses[0]);i++){
            int result=render(argv[1],&poses[i],enabled,openloop,supports,renderfn,receipt);
            fflush(receipt);
            if(result){
                fprintf(stderr,"OPENAL_HRTF_FIRST_FAILURE mode=%d pose=%s code=%d\n",
                        enabled,poses[i].name,result);
                fclose(receipt);
                return result;
            }
        }
    }
    fclose(receipt);
    puts("OPENAL_HRTF_TEN_NATIVE_PCM_FILES_READY");
    return 0;
}
