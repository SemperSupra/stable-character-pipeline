/* W4l libVLC: ORIGINAL synthetic PCM, native callback observation only.
 * No physical latency, HRTF equivalence, real scene, or product claim.
 * Run in isolated $0 Ubuntu CPU with distro libVLC 3.x and native callbacks.
 */
#define _POSIX_C_SOURCE 200809L
#include <vlc/vlc.h>
#include <errno.h>
#include <inttypes.h>
#include <pthread.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>
#include <unistd.h>
enum { RATE=48000, N=16384, CAP=65536 };
typedef struct {
    pthread_mutex_t lock;
    int16_t samples[CAP];
    size_t count, chunks, flushes, pauses, resumes, drains;
    int overflow;
    int64_t first_pts, last_pts;
} Capture;
static void le16(FILE*f, uint16_t x) { fputc(x&255,f); fputc((x>>8)&255,f); }
static void le32(FILE*f, uint32_t x) {
    for(int i=0;i<4;i++) fputc((x>>(i*8))&255,f);
}
static int source(const char*root) {
    char raw[4096],wav[4096];
    if(snprintf(raw,sizeof(raw),"%s/source_s16le.raw",root)>=(int)sizeof(raw) ||
       snprintf(wav,sizeof(wav),"%s/source.wav",root)>=(int)sizeof(wav)) return 2;
    FILE*a=fopen(raw,"wbx"); if(!a)return 3;
    FILE*b=fopen(wav,"wbx"); if(!b){fclose(a);return 4;}
    fwrite("RIFF",1,4,b);le32(b,36+N*2);fwrite("WAVEfmt ",1,8,b);
    le32(b,16);le16(b,1);le16(b,1);le32(b,RATE);le32(b,RATE*2);
    le16(b,2);le16(b,16);fwrite("data",1,4,b);le32(b,N*2);
    for(unsigned i=0;i<N;i++){
        uint16_t v=(i==0)?12000:(i==4096)?15000:(i==8192)?10000:0;
        le16(a,v);le16(b,v);
    }
    int ea=ferror(a),eb=ferror(b);
    int ca=fclose(a),cb=fclose(b);
    return ea||eb||ca||cb?5:0;
}
static void play_cb(void*opaque,const void*pcm,unsigned count,int64_t pts){
    Capture*c=(Capture*)opaque;
    pthread_mutex_lock(&c->lock);
    if(c->chunks==0)c->first_pts=pts;
    c->last_pts=pts;c->chunks++;
    if(!pcm || count>CAP-c->count)c->overflow=1;
    else {memcpy(c->samples+c->count,pcm,(size_t)count*2);c->count+=count;}
    pthread_mutex_unlock(&c->lock);
}
static void pause_cb(void*p,int64_t pts){(void)pts;Capture*c=p;pthread_mutex_lock(&c->lock);c->pauses++;pthread_mutex_unlock(&c->lock);}
static void resume_cb(void*p,int64_t pts){(void)pts;Capture*c=p;pthread_mutex_lock(&c->lock);c->resumes++;pthread_mutex_unlock(&c->lock);}
static void flush_cb(void*p,int64_t pts){(void)pts;Capture*c=p;pthread_mutex_lock(&c->lock);c->flushes++;pthread_mutex_unlock(&c->lock);}
static void drain_cb(void*p){Capture*c=p;pthread_mutex_lock(&c->lock);c->drains++;pthread_mutex_unlock(&c->lock);}
static int save(const char*root,Capture*c,const char*state){
    char raw[4096],meta[4096],version[4096];
    if(snprintf(raw,sizeof(raw),"%s/callback_s16le.raw",root)>=(int)sizeof(raw)||
       snprintf(meta,sizeof(meta),"%s/native_observation.json",root)>=(int)sizeof(meta)||
       snprintf(version,sizeof(version),"%s/native_libvlc_version.txt",root)>=(int)sizeof(version))return 20;
    pthread_mutex_lock(&c->lock);
    FILE*a=fopen(raw,"wbx");
    if(!a){pthread_mutex_unlock(&c->lock);return 21;}
    size_t n=fwrite(c->samples,2,c->count,a);
    int ae=ferror(a),ac=fclose(a);
    FILE*b=fopen(meta,"wx");
    if(!b){pthread_mutex_unlock(&c->lock);return 22;}
    fprintf(b,"{\"schema\":\"scp.libvlc_callback_native.v1\",\"engine\":\"libVLC\","
      "\"status\":\"%s\",\"sample_rate\":48000,\"channels\":1,\"sample_format\":\"S16N\","
      "\"input_frames\":16384,\"callback_frames\":%zu,\"chunks\":%zu,"
      "\"overflow\":%s,\"flushes\":%zu,\"drains\":%zu,\"pauses\":%zu,"
      "\"resumes\":%zu,\"first_pts\":%" PRId64 ",\"last_pts\":%" PRId64 ","
      "\"exact_source_copy_claim\":false,\"physical_latency_claim\":false}\n",
      state,c->count,c->chunks,c->overflow?"true":"false",c->flushes,c->drains,
      c->pauses,c->resumes,c->first_pts,c->last_pts);
    int be=ferror(b),bc=fclose(b);
    pthread_mutex_unlock(&c->lock);
    FILE*v=fopen(version,"wx");
    if(!v)return 23;
    fprintf(v,"%s\n",libvlc_get_version());
    int vc=fclose(v);
    return n!=c->count||ae||ac||be||bc||vc?24:0;
}
int main(int argc,char**argv){
    if(argc!=2){fputs("usage: libvlc-original OUT_EMPTY_DIR\n",stderr);return 2;}
    if(source(argv[1])){fputs("FIRST_FAILURE source write\n",stderr);return 3;}
    Capture*c=calloc(1,sizeof(*c));if(!c)return 4;
    if(pthread_mutex_init(&c->lock,NULL))return 5;
    const char*opts[]={"--intf=dummy","--no-video","--no-osd","--quiet"};
    libvlc_instance_t*vlc=libvlc_new(4,opts);
    if(!vlc){fputs("FIRST_FAILURE libvlc_new\n",stderr);return 6;}
    char path[4096];
    if(snprintf(path,sizeof(path),"%s/source.wav",argv[1])>=(int)sizeof(path))return 7;
    libvlc_media_t*m=libvlc_media_new_path(vlc,path);
    if(!m){fputs("FIRST_FAILURE media_new_path\n",stderr);return 8;}
    libvlc_media_player_t*p=libvlc_media_player_new_from_media(m);
    libvlc_media_release(m);
    if(!p){fputs("FIRST_FAILURE player\n",stderr);return 9;}
    libvlc_audio_set_callbacks(p,play_cb,pause_cb,resume_cb,flush_cb,drain_cb,c);
    libvlc_audio_set_format(p,"S16N",RATE,1);
    int play=libvlc_media_player_play(p);
    int terminal=0;
    for(int i=0;!play && i<600;i++){
        libvlc_state_t st=libvlc_media_player_get_state(p);
        if(st==libvlc_Ended){terminal=1;break;}
        if(st==libvlc_Error){terminal=-1;break;}
        struct timespec ts={.tv_sec=0,.tv_nsec=20000000L};
        nanosleep(&ts,NULL);
    }
    libvlc_media_player_stop(p);
    const char*state=play?"PLAY_REJECTED":terminal==1?"ENDED":"TIMEOUT_OR_ERROR";
    int saved=save(argv[1],c,state);
    libvlc_media_player_release(p);
    libvlc_release(vlc);
    if(saved){fprintf(stderr,"FIRST_FAILURE save=%d\n",saved);return saved;}
    if(play||terminal!=1||c->overflow||c->chunks==0){
        fprintf(stderr,"FIRST_FAILURE native_status=%s chunks=%zu overflow=%d\n",state,c->chunks,c->overflow);
        return 10;
    }
    puts("W4L_LIBVLC_NATIVE_CALLBACK_CAPTURE_COMPLETE_NOT_YET_INDEPENDENTLY_QUALIFIED");
    return 0;
}
