/* Native permissive SAF core time-varying FFT convolution qualification.
 * Only original self-authored synthetic input + 3 FIRs; no SOFA/BRIR or
 * optional GPL tracker/HADES modules. Actual SAF upstream C ABI is linked.
 */
#include "saf.h"
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

enum { RATE=48000, FRAMES=8192, HOP=256, LENGTH=512, IRS=3 };
static int16_t source[FRAMES];
static float filters[IRS][LENGTH];
static float *irptrs[IRS] = {filters[0],filters[1],filters[2]};
typedef struct { const char *name; int which; } Schedule;
static const Schedule schedules[]={
    {"static0",0},{"static1",1},{"switch_012",2},{"cycle_012",3}
};
static void prepare_original(void){
    for(int i=0;i<FRAMES;i++){
        double value=0;
        if(i<6144){
            value=.1*sin(2.0*3.14159265358979323846*410.0*(double)i/(double)RATE);
            if(i==8*HOP || i==16*HOP)value+=.2;
        }
        source[i]=(int16_t)lrint(value*32767.0);
    }
    memset(filters,0,sizeof(filters));
    filters[0][0]=1;
    filters[1][0]=1;filters[1][64]=.25f;
    filters[2][0]=1;filters[2][128]=.5f;
}
static int write_source(const char *root){
    char path[4096];
    if(snprintf(path,sizeof(path),"%s/original_410_s16le.raw",root)>=(int)sizeof(path))return 1;
    FILE *f=fopen(path,"wbx");
    if(!f)return 2;
    size_t w=fwrite(source,sizeof(int16_t),FRAMES,f);
    int close=fclose(f);
    return (w==FRAMES && close==0)?0:3;
}
static int idx_for(int which,int hop){
    if(which==0)return 0;
    if(which==1)return 1;
    if(which==2)return hop<8?0:hop<16?1:hop<24?2:0;
    return hop<8?0:hop<24?((hop-8)/2)%3:0;
}
static int render(const char*root, const Schedule *s){
    void *handle=NULL;
    saf_TVConv_create(&handle,HOP,irptrs,LENGTH,IRS,1,0);
    if(!handle)return 3;
    float *output=(float*)calloc(FRAMES,sizeof(float));
    if(!output)return 4;
    for(int hop=0;hop<FRAMES/HOP;hop++){
        float input[HOP];
        for(int n=0;n<HOP;n++)input[n]=(float)source[hop*HOP+n]/32768.f;
        saf_TVConv_apply(handle,input,output+hop*HOP,idx_for(s->which,hop));
    }
    double peak=0,energy=0,tail=0;
    for(int i=0;i<FRAMES;i++){
        double value=output[i];
        if(!isfinite(value))return 5;
        if(fabs(value)>peak)peak=fabs(value);
        energy+=value*value;
        if(i>=6144)tail+=value*value;
    }
    if(peak<1e-7 || peak>1 || energy<1e-9)return 6;
    char path[4096];
    if(snprintf(path,sizeof(path),"%s/%s.f32",root,s->name)>=(int)sizeof(path))return 7;
    FILE *out=fopen(path,"wbx");
    if(!out)return 8;
    size_t w=fwrite(output,sizeof(float),FRAMES,out);
    int close=fclose(out);
    free(output);
    saf_TVConv_destroy(&handle);
    if(handle!=NULL || w!=FRAMES || close!=0)return 9;
    printf("SAF_NATIVE_TVCONV_PASS mode=%s peak=%.9g energy=%.9g after_source_zero_tail=%.9g\n",
            s->name,peak,energy,tail);
    return 0;
}
int main(int argc,char **argv){
    if(argc!=2){fputs("usage: saf_tvconv_batch OUT_DIR\n",stderr);return 2;}
    prepare_original();
    if(write_source(argv[1]))return 3;
    for(size_t i=0;i<sizeof(schedules)/sizeof(schedules[0]);i++){
        int result=render(argv[1],&schedules[i]);
        if(result){
            fprintf(stderr,"SAF_NATIVE_TVCONV_FIRST_FAILURE %s code=%d\n",
                    schedules[i].name,result);
            return result;
        }
    }
    puts("SAF_TVCONV_FOUR_REAL_NATIVE_OUTPUTS");
    return 0;
}
