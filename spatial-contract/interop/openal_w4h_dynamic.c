/* W4h-B native dynamic source/listener pose changes; source-pinned W4g prior.
 * Four exact loopback modes, original 48k PCM16 impulses, extra drain.
 * Onset/tail are measured observations, not fixed accepted codec latency.
 */
#include <AL/al.h>
#include <AL/alc.h>
#include <AL/alext.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum{ RATE=48000,SOURCE_FRAMES=16384,OUTPUT_FRAMES=32768,CHANNELS=2 };
static int16_t source[SOURCE_FRAMES];
typedef struct{const char*name;int hrtf;float x,y,z;int pose_mode;} Mode;
static const Mode modes[]={
 {"static_left",1,-10,0,-10,0},
 {"dynamic_source_lrl",1,-10,0,-10,1},
 {"dynamic_listener_yaw",1,-10,0,-10,2}
};
static int write_source(const char*root){
 source[0]=12000;source[4096]=15000;source[8192]=10000;
 char path[4096];
 if(snprintf(path,sizeof(path),"%s/original_impulses_s16le.raw",root)>=(int)sizeof(path))return 1;
 FILE *f=fopen(path,"wbx");if(!f)return 2;
 size_t n=fwrite(source,sizeof(int16_t),SOURCE_FRAMES,f);
 int status=fclose(f);
 return n==SOURCE_FRAMES&&status==0?0:3;
}
static int render_case(const char*root,const Mode*mode,
 LPALCLOOPBACKOPENDEVICESOFT openloop,
 LPALCISRENDERFORMATSUPPORTEDSOFT supported,
 LPALCRENDERSAMPLESSOFT render,FILE*state){
 ALCdevice*dev=openloop(NULL);
 if(!dev)return 2;
 if(!supported(dev,RATE,ALC_STEREO_SOFT,ALC_FLOAT_SOFT)||
    !alcIsExtensionPresent(dev,"ALC_SOFT_HRTF"))return 3;
 const ALCint attrs[]={
  ALC_FORMAT_CHANNELS_SOFT,ALC_STEREO_SOFT,
  ALC_FORMAT_TYPE_SOFT,ALC_FLOAT_SOFT,ALC_FREQUENCY,RATE,
  ALC_HRTF_SOFT,mode->hrtf?ALC_TRUE:ALC_FALSE,0};
 ALCcontext*ctx=alcCreateContext(dev,attrs);
 if(!ctx||!alcMakeContextCurrent(ctx))return 4;
 ALCint status=0;
 alcGetIntegerv(dev,ALC_HRTF_STATUS_SOFT,1,&status);
 if((mode->hrtf && status!=ALC_HRTF_ENABLED_SOFT)||
    (!mode->hrtf && status==ALC_HRTF_ENABLED_SOFT))return 5;
 ALuint b=0,voice=0;
 alGenBuffers(1,&b);
 alBufferData(b,AL_FORMAT_MONO16,source,sizeof(source),RATE);
 alGenSources(1,&voice);
 alSourcei(voice,AL_BUFFER,(ALint)b);
 alDistanceModel(AL_NONE);
 alListener3f(AL_POSITION,0,0,0);
 const ALfloat orient[]={0,0,-1,0,1,0};
 alListenerfv(AL_ORIENTATION,orient);
 alSource3f(voice,AL_POSITION,mode->x,mode->y,mode->z);
 alSourcePlay(voice);
 if(alGetError()!=AL_NO_ERROR)return 6;
 float*pcm=(float*)calloc((size_t)OUTPUT_FRAMES*CHANNELS,sizeof(float));
 if(!pcm)return 7;
 for(int f=0;f<OUTPUT_FRAMES;f+=256){
  if(f==4096){
   if(mode->pose_mode==1)alSource3f(voice,AL_POSITION,10,0,-10);
   if(mode->pose_mode==2){const ALfloat yaw[]={0,0,1,0,1,0};alListenerfv(AL_ORIENTATION,yaw);}
  }
  if(f==8192){
   if(mode->pose_mode==1)alSource3f(voice,AL_POSITION,-10,0,-10);
   if(mode->pose_mode==2)alListenerfv(AL_ORIENTATION,orient);
  }
  if(alGetError()!=AL_NO_ERROR)return 17;
  render(dev,pcm+(size_t)f*CHANNELS,256);
  if(alcGetError(dev)!=ALC_NO_ERROR)return 8;
 }
 double peak=0,energy=0,tailEnergy=0;
 int first=-1,last=-1;
 for(int f=0;f<OUTPUT_FRAMES;f++){
  double sum=0;
  for(int c=0;c<CHANNELS;c++){
   double val=(double)pcm[f*CHANNELS+c];
   if(!isfinite(val)||fabs(val)>1)return 9;
   if(fabs(val)>peak)peak=fabs(val);
   sum+=val*val;
   if(f>=SOURCE_FRAMES)tailEnergy+=val*val;
   if(fabs(val)>1e-7){if(first<0)first=f;last=f;}
  }
  energy+=sum;
 }
 if(first<0||peak<1e-7||energy<=1e-12)return 10;
 char path[4096];
 if(snprintf(path,sizeof(path),"%s/%s.f32",root,mode->name)>=(int)sizeof(path))return 11;
 FILE*out=fopen(path,"wbx");if(!out)return 12;
 size_t nw=fwrite(pcm,sizeof(float),(size_t)OUTPUT_FRAMES*CHANNELS,out);
 int closed=fclose(out);
 free(pcm);
 if(nw!=(size_t)OUTPUT_FRAMES*CHANNELS||closed)return 13;
 fprintf(state,"%s\t%d\t%d\t%d\t%.12g\t%.12g\t%.12g\n",
  mode->name,status,first,last,peak,energy,tailEnergy);
 printf("W4H_OPENAL_NATIVE_POSE_PASS case=%s hrtf=%d first=%d last=%d tail=%.9g\n",
   mode->name,status,first,last,tailEnergy);
 alSourceStop(voice);alDeleteSources(1,&voice);alDeleteBuffers(1,&b);
 alcMakeContextCurrent(NULL);alcDestroyContext(ctx);alcCloseDevice(dev);
 return 0;
}
int main(int argc,char**argv){
 if(argc!=2){fputs("usage: openal_w4g_onset NEW_DIR\n",stderr);return 2;}
 if(write_source(argv[1]))return 3;
 if(!alcIsExtensionPresent(NULL,"ALC_SOFT_loopback"))return 4;
 LPALCLOOPBACKOPENDEVICESOFT o=(LPALCLOOPBACKOPENDEVICESOFT)alcGetProcAddress(NULL,"alcLoopbackOpenDeviceSOFT");
 LPALCISRENDERFORMATSUPPORTEDSOFT s=(LPALCISRENDERFORMATSUPPORTEDSOFT)alcGetProcAddress(NULL,"alcIsRenderFormatSupportedSOFT");
 LPALCRENDERSAMPLESSOFT r=(LPALCRENDERSAMPLESSOFT)alcGetProcAddress(NULL,"alcRenderSamplesSOFT");
 if(!o||!s||!r)return 5;
 char meta[4096];
 if(snprintf(meta,sizeof(meta),"%s/actual_native_states.tsv",argv[1])>=(int)sizeof(meta))return 6;
 FILE*f=fopen(meta,"wx");if(!f)return 7;
 for(size_t i=0;i<sizeof(modes)/sizeof(modes[0]);i++){
  int code=render_case(argv[1],&modes[i],o,s,r,f);
  fflush(f);
  if(code){
   fprintf(stderr,"W4H_OPENAL_FIRST_FAILURE mode=%s code=%d\n",modes[i].name,code);
   fclose(f);return code;
  }
 }
 if(fclose(f))return 8;
 puts("W4H_OPENAL_NATIVE_THREE_POSE_TRAJECTORIES_COMPLETE");
 return 0;
}
