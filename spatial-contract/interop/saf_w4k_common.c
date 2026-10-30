/* Native pinned SAF TVConv with same original PCM16 impulses as W4h OpenAL.
 * No common filter topology or universal output latency claimed.
 */
#define _POSIX_C_SOURCE 200809L
#include "saf.h"
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
enum { RATE=48000, SOURCE_FRAMES=16384, OUTPUT_FRAMES=32768, HOP=256, IRLEN=512, NIRS=2 };
static int16_t source[OUTPUT_FRAMES];
static int write_input(const char *root){
 source[0]=12000;source[4096]=15000;source[8192]=10000;
 char path[4096];
 if(snprintf(path,sizeof(path),"%s/source_s16le.raw",root)>=(int)sizeof(path))return 1;
 FILE *f=fopen(path,"wbx");if(!f)return 2;
 size_t written=fwrite(source,sizeof(source[0]),SOURCE_FRAMES,f);
 int c=fclose(f);return written==SOURCE_FRAMES&&c==0?0:3;
}
static int run(const char *root,int changed,FILE *meta){
 float *ir[NIRS]={NULL,NULL};
 for(int i=0;i<NIRS;i++){
  ir[i]=(float*)calloc(IRLEN,sizeof(float));if(!ir[i])return 2;
  ir[i][0]=1.f;
 }
 ir[1][IRLEN/8]=.18f;
 void *handle=NULL;
 saf_TVConv_create(&handle,HOP,ir,IRLEN,NIRS,1,0);
 if(!handle)return 3;
 float *pcm=(float*)calloc(OUTPUT_FRAMES,sizeof(float));if(!pcm)return 4;
 for(int block=0;block<OUTPUT_FRAMES/HOP;block++){
  float input[HOP];
  for(int k=0;k<HOP;k++)input[k]=(float)source[block*HOP+k]/32768.f;
  int frame=block*HOP;
  int ir_index=changed && frame>=4096 && frame<8192 ? 1:0;
  saf_TVConv_apply(handle,input,pcm+frame,ir_index);
 }
 double energy=0,peak=0,tail=0;int first=-1,last=-1;
 for(int f=0;f<OUTPUT_FRAMES;f++){
  double v=pcm[f];
  if(!isfinite(v)||fabs(v)>1)return 5;
  if(fabs(v)>peak)peak=fabs(v);
  energy+=v*v;
  if(f>=SOURCE_FRAMES)tail+=v*v;
  if(fabs(v)>1e-7){if(first<0)first=f;last=f;}
 }
 if(first<0||energy<=1e-10||peak<1e-7)return 6;
 char name[4096];
 if(snprintf(name,sizeof(name),"%s/%s.f32",root,changed?"saf_dynamic_ir":"saf_static")>=(int)sizeof(name))return 7;
 FILE *f=fopen(name,"wbx");if(!f)return 8;
 size_t n=fwrite(pcm,sizeof(float),OUTPUT_FRAMES,f);
 int closed=fclose(f);if(n!=OUTPUT_FRAMES||closed)return 9;
 fprintf(meta,"%s\t%d\t%d\t%.12g\t%.12g\t%.12g\n",changed?"saf_dynamic_ir":"saf_static",first,last,peak,energy,tail);
 printf("W4K_SAF_NATIVE_COMMON_INPUT_PASS mode=%s first=%d last=%d tail=%.12g\n",changed?"dynamic_ir":"static",first,last,tail);
 saf_TVConv_destroy(&handle);
 free(pcm);
 for(int i=0;i<NIRS;i++)free(ir[i]);
 if(handle!=NULL)return 10;
 return 0;
}
int main(int argc,char**argv){
 if(argc!=2)return 2;
 if(write_input(argv[1]))return 3;
 char path[4096];
 if(snprintf(path,sizeof(path),"%s/native_measure.tsv",argv[1])>=(int)sizeof(path))return 4;
 FILE *meta=fopen(path,"wx");if(!meta)return 5;
 for(int i=0;i<=1;i++){int err=run(argv[1],i,meta);fflush(meta);if(err){fprintf(stderr,"W4K_SAF_FIRST_FAILURE %d %d\n",i,err);fclose(meta);return err;}}
 if(fclose(meta))return 6;
 puts("W4K_SAF_TWO_COMMON_INPUT_IR_MODES_COMPLETE");
 return 0;
}
