/* One actual pinned SAF source build; batch 3 hop sizes x 3 FIR lengths x
 * static/changed IR cases. All synthetic, mono, and license gated.
 * Timing and maxrss are observations, NEVER portable acceptance bounds.
 */
#define _POSIX_C_SOURCE 200809L
#include "saf.h"
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <sys/resource.h>
enum { RATE=48000, NIRS=3 };
static const int hops[]={128,256,512};
static const int lengths[]={256,512,1024};
static void generate(int16_t *out,int hop){
 for(int frame=0;frame<32*hop;frame++){
  double value=0;
  if(frame<24*hop){
   value=.08*sin(2*3.14159265358979323846*410*(double)frame/(double)RATE);
   if(frame==8*hop || frame==16*hop)value+=.1;
  }
  out[frame]=(int16_t)lrint(value*32767.0);
 }
}
static int write_source(const char *root,int hop,const int16_t *src){
 char p[4096];
 if(snprintf(p,sizeof(p),"%s/source_h%d.s16le",root,hop)>=(int)sizeof(p))return 1;
 FILE *f=fopen(p,"wbx");if(!f)return 2;
 size_t w=fwrite(src,2,32*(size_t)hop,f);
 int c=fclose(f);
 return w==32*(size_t)hop&&!c?0:3;
}
static double seconds(const struct timespec *a,const struct timespec *b){
 return (double)(b->tv_sec-a->tv_sec)+(double)(b->tv_nsec-a->tv_nsec)*1e-9;
}
static int render(const char *root,int hop,int len,int switched,const int16_t *source,FILE *meta){
 float *ir[NIRS]={NULL,NULL,NULL};
 for(int i=0;i<NIRS;i++) {
  ir[i]=(float*)calloc((size_t)len,sizeof(float));if(!ir[i])return 2;
  ir[i][0]=1.f;
 }
 ir[1][len/8]=.18f;
 ir[2][len/4]=.3f;
 void *handle=NULL;
 saf_TVConv_create(&handle,hop,ir,len,NIRS,1,0);
 if(!handle)return 3;
 int n=32*hop;
 float *pcm=(float*)calloc((size_t)n,sizeof(float));if(!pcm)return 4;
 struct timespec before,after;
 clock_gettime(CLOCK_MONOTONIC,&before);
 for(int block=0;block<32;block++){
  float input[512];
  for(int fi=0;fi<hop;fi++)input[fi]=(float)source[block*hop+fi]/32768.f;
  int index=(switched && block>=8)?(block<16?1:2):0;
  saf_TVConv_apply(handle,input,pcm+block*hop,index);
 }
 clock_gettime(CLOCK_MONOTONIC,&after);
 struct rusage usage;
 getrusage(RUSAGE_SELF,&usage);
 double energy=0,peak=0,tail=0;
 for(int fi=0;fi<n;fi++){
  double v=pcm[fi];
  if(!isfinite(v))return 5;
  if(fabs(v)>peak)peak=fabs(v);
  energy+=v*v;
  if(fi>=24*hop)tail+=v*v;
 }
 if(energy<1e-10||peak<=1e-7||peak>1)return 6;
 char path[4096];
 if(snprintf(path,sizeof(path),"%s/saf_h%d_ir%d_%s.f32",root,hop,len,
    switched?"switch":"static")>=(int)sizeof(path))return 7;
 FILE *f=fopen(path,"wbx");if(!f)return 8;
 size_t written=fwrite(pcm,sizeof(float),(size_t)n,f);
 int c=fclose(f);
 if(written!=(size_t)n||c)return 9;
 fprintf(meta,"%d\t%d\t%s\t%d\t%.12g\t%.12g\t%.12g\t%.12g\t%ld\n",
  hop,len,switched?"switch":"static",n,peak,energy,tail,seconds(&before,&after),
  usage.ru_maxrss);
 printf("SAF_W4D_NATIVE_PROFILE_PASS hop=%d ir=%d case=%s frames=%d energy=%.8g tail=%.8g secs=%.8g maxrss=%ld\n",
  hop,len,switched?"switch":"static",n,energy,tail,seconds(&before,&after),usage.ru_maxrss);
 saf_TVConv_destroy(&handle);
 free(pcm);
 for(int i=0;i<NIRS;i++)free(ir[i]);
 if(handle!=NULL)return 10;
 return 0;
}
int main(int argc,char**argv){
 if(argc!=2){fputs("usage: saf_w4d_resource OUT_DIR\n",stderr);return 2;}
 char path[4096];
 if(snprintf(path,sizeof(path),"%s/saf_resource.tsv",argv[1])>=(int)sizeof(path))return 3;
 FILE *meta=fopen(path,"wx");if(!meta)return 4;
 for(size_t hi=0;hi<sizeof(hops)/sizeof(hops[0]);hi++){
  int hop=hops[hi];
  int16_t *src=(int16_t*)calloc((size_t)32*hop,sizeof(int16_t));
  if(!src)return 5;
  generate(src,hop);
  if(write_source(argv[1],hop,src))return 6;
  for(size_t li=0;li<sizeof(lengths)/sizeof(lengths[0]);li++){
   for(int changed=0;changed<=1;changed++){
    int err=render(argv[1],hop,lengths[li],changed,src,meta);
    fflush(meta);
    if(err){
     fprintf(stderr,"SAF_W4D_FIRST_FAILURE hop=%d len=%d changed=%d code=%d\n",
      hop,lengths[li],changed,err);
     return err;
    }
   }
  }
  free(src);
 }
 if(fclose(meta))return 7;
 puts("SAF_W4D_18_NATIVE_OUTPUTS_COMPLETE");
 return 0;
}
