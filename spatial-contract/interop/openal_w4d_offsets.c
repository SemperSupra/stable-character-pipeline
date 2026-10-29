/* Public original-source HRTF exact render-call-boundary switch study.
 * Updates occur between native alcRenderSamplesSOFT calls, including
 * 1-sample and 255-sample boundaries. They are NOT modifications inside an
 * OpenAL callback, nor proof of sample-continuous interpolation.
 */
#include <AL/al.h>
#include <AL/alc.h>
#include <AL/alext.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
enum { RATE=48000, FRAMES=8192, CHANNELS=2, CALLBACK=256 };
static const int offsets[]={0,1,255,256,1023,1024,1025};
static int16_t source[FRAMES];
typedef struct {char name[64];int initialRight;int switchAt;} Mode;
static int write_source(const char *root){
 for(int i=0;i<FRAMES;i++)
   source[i]=(int16_t)lrint(.12*32767*sin(2*3.14159265358979323846*410*i/(double)RATE));
 char path[4096];
 if(snprintf(path,sizeof(path),"%s/original_410_mono_s16le.raw",root)>=(int)sizeof(path))return 1;
 FILE *f=fopen(path,"wbx");
 if(!f)return 2;
 size_t n=fwrite(source,sizeof(int16_t),FRAMES,f);
 int c=fclose(f);
 return n==FRAMES&&!c?0:3;
}
static int render_case(const char*root,const Mode*m,
  LPALCLOOPBACKOPENDEVICESOFT openloop,
  LPALCISRENDERFORMATSUPPORTEDSOFT supported,
  LPALCRENDERSAMPLESSOFT render,FILE *meta){
 ALCdevice *dev=openloop(NULL);
 if(!dev)return 2;
 if(!supported(dev,RATE,ALC_STEREO_SOFT,ALC_FLOAT_SOFT) ||
    !alcIsExtensionPresent(dev,"ALC_SOFT_HRTF"))return 3;
 const ALCint attrs[]={ALC_FORMAT_CHANNELS_SOFT,ALC_STEREO_SOFT,ALC_FORMAT_TYPE_SOFT,ALC_FLOAT_SOFT,
    ALC_FREQUENCY,RATE,ALC_HRTF_SOFT,ALC_TRUE,0};
 ALCcontext *ctx=alcCreateContext(dev,attrs);
 if(!ctx||!alcMakeContextCurrent(ctx))return 4;
 ALCint hrtf=0;
 alcGetIntegerv(dev,ALC_HRTF_STATUS_SOFT,1,&hrtf);
 if(hrtf!=ALC_HRTF_ENABLED_SOFT)return 5;
 ALuint buffer=0,voice=0;
 alGenBuffers(1,&buffer);alBufferData(buffer,AL_FORMAT_MONO16,source,sizeof(source),RATE);
 alGenSources(1,&voice);alSourcei(voice,AL_BUFFER,(ALint)buffer);
 alDistanceModel(AL_NONE);
 alListener3f(AL_POSITION,0,0,0);
 const ALfloat orient[6]={0,0,-1,0,1,0};
 alListenerfv(AL_ORIENTATION,orient);
 alSource3f(voice,AL_POSITION,m->initialRight?10:-10,0,-10);
 alSourcePlay(voice);
 if(alGetError()!=AL_NO_ERROR)return 6;
 float *pcm=(float*)calloc((size_t)FRAMES*CHANNELS,sizeof(float));
 if(!pcm)return 7;
 int switched=0;
 for(int pos=0;pos<FRAMES;){
  if(m->switchAt>=0 && !switched && pos==m->switchAt){
   alSource3f(voice,AL_POSITION,10,0,-10);
   switched=1;
  }
  if(alGetError()!=AL_NO_ERROR)return 8;
  int count=FRAMES-pos;
  if(count>CALLBACK)count=CALLBACK;
  if(m->switchAt>=0 && !switched && pos+count>m->switchAt)
    count=m->switchAt-pos;
  if(count<=0)return 9;
  render(dev,pcm+(size_t)pos*CHANNELS,count);
  if(alcGetError(dev)!=ALC_NO_ERROR)return 10;
  pos+=count;
 }
 double peak=0,energy=0;
 for(int i=0;i<FRAMES*CHANNELS;i++){
  double v=pcm[i];
  if(!isfinite(v))return 11;
  if(fabs(v)>peak)peak=fabs(v);
  energy+=v*v;
 }
 if(peak<1e-7||peak>1||energy<1e-8)return 12;
 char path[4096];
 if(snprintf(path,sizeof(path),"%s/%s.f32",root,m->name)>=(int)sizeof(path))return 13;
 FILE *f=fopen(path,"wbx");if(!f)return 14;
 size_t w=fwrite(pcm,sizeof(float),(size_t)FRAMES*CHANNELS,f);
 int c=fclose(f);
 free(pcm);
 if(w!=(size_t)FRAMES*CHANNELS||c)return 15;
 fprintf(meta,"%s\t%d\t%d\t%.12g\t%.12g\n",m->name,m->switchAt,hrtf,peak,energy);
 printf("OPENAL_HRTF_OFFSET_NATIVE_PASS mode=%s switch=%d hrtf=%d energy=%.9g\n",
   m->name,m->switchAt,hrtf,energy);
 alSourceStop(voice);
 alDeleteSources(1,&voice);alDeleteBuffers(1,&buffer);
 alcMakeContextCurrent(NULL);
 alcDestroyContext(ctx);alcCloseDevice(dev);
 return 0;
}
int main(int argc,char**argv){
 if(argc!=2){fputs("usage: openal_w4d_offsets DIR\n",stderr);return 2;}
 if(write_source(argv[1]))return 3;
 if(!alcIsExtensionPresent(NULL,"ALC_SOFT_loopback"))return 4;
 LPALCLOOPBACKOPENDEVICESOFT openloop=(LPALCLOOPBACKOPENDEVICESOFT)alcGetProcAddress(NULL,"alcLoopbackOpenDeviceSOFT");
 LPALCISRENDERFORMATSUPPORTEDSOFT supported=(LPALCISRENDERFORMATSUPPORTEDSOFT)alcGetProcAddress(NULL,"alcIsRenderFormatSupportedSOFT");
 LPALCRENDERSAMPLESSOFT render=(LPALCRENDERSAMPLESSOFT)alcGetProcAddress(NULL,"alcRenderSamplesSOFT");
 if(!openloop||!supported||!render)return 5;
 char path[4096];
 if(snprintf(path,sizeof(path),"%s/offsets.tsv",argv[1])>=(int)sizeof(path))return 6;
 FILE *meta=fopen(path,"wx");if(!meta)return 7;
 Mode m={.name="static_left",.initialRight=0,.switchAt=-1};
 for(int c=0;c<9;c++){
  if(c==1){strcpy(m.name,"static_right");m.initialRight=1;m.switchAt=-1;}
  else if(c>=2){
   snprintf(m.name,sizeof(m.name),"switch_%04d",offsets[c-2]);
   m.initialRight=0;m.switchAt=offsets[c-2];
  }
  int err=render_case(argv[1],&m,openloop,supported,render,meta);
  fflush(meta);
  if(err){
   fprintf(stderr,"OPENAL_HRTF_OFFSET_FIRST_FAILURE mode=%s code=%d\n",m.name,err);
   fclose(meta);return err;
  }
 }
 if(fclose(meta))return 8;
 puts("OPENAL_HRTF_W4D_NINE_PCM_OUTPUTS_READY");
 return 0;
}
