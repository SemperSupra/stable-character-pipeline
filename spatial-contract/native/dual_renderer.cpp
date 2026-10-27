// Original first-party integration shim; upstream renderer remains LGPLv2.1+
// pinned and dynamically linked. Reads admitted mono WAV and Go's ENU block plan.
// Deliberately NEVER invokes the known-bad native stereo rendering path.
#include "Renderer.h"
#include "RendererMetadata.h"
#include "LoudspeakerLayouts.h"
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <fcntl.h>
#include <unistd.h>
#include <cstring>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

namespace{
constexpr unsigned kRate=48000,kFrame=1024;
uint16_t get16(const unsigned char*b){return uint16_t(b[0])|(uint16_t(b[1])<<8);}
uint32_t get32(const unsigned char*b){return uint32_t(b[0])|(uint32_t(b[1])<<8)|(uint32_t(b[2])<<16)|(uint32_t(b[3])<<24);}
std::vector<float> readSource(const std::string&path){
 std::ifstream f(path,std::ios::binary|std::ios::ate);
 if(!f)throw std::runtime_error("cannot read admitted source");
 const auto size=f.tellg();
 if(size<44 || size>64*1024*1024)throw std::runtime_error("input WAV size");
 f.seekg(0);
 unsigned char h[44];f.read((char*)h,44);
 if(!f || std::memcmp(h,"RIFF",4)||std::memcmp(h+8,"WAVEfmt ",8)
   ||get32(h+16)!=16||get16(h+20)!=1||get16(h+22)!=1
   ||get32(h+24)!=kRate||get32(h+28)!=96000
   ||get16(h+32)!=2||get16(h+34)!=16||std::memcmp(h+36,"data",4))
   throw std::runtime_error("native source not canonical mono PCM16 48k WAV");
 const uint32_t count=get32(h+40)/2;
 if(get32(h+40)%2 || get32(h+4)!=(uint32_t)size-8 || get32(h+40)!=(uint32_t)size-44)
   throw std::runtime_error("source data length mismatch");
 std::vector<unsigned char>raw((size_t)count*2);
 f.read((char*)raw.data(),raw.size());
 if(!f)throw std::runtime_error("source truncated during native read");
 std::vector<float>pcm(count);
 for(size_t i=0;i<count;i++)pcm[i]=(float)(int16_t(get16(raw.data()+i*2)))/32768.f;
 return pcm;
}
void writeFloatWav(const std::string&path,const std::vector<float>&data,unsigned channels){
 if(data.size()>std::numeric_limits<uint32_t>::max()/4)throw std::runtime_error("oversized output");
 const uint32_t bytes=(uint32_t)data.size()*4;
 std::vector<unsigned char>wav((size_t)44+bytes,0);
 std::memcpy(wav.data(),"RIFF",4);
 auto u16=[&](size_t pos,uint16_t v){wav[pos]=(unsigned char)v;wav[pos+1]=(unsigned char)(v>>8);};
 auto u32=[&](size_t pos,uint32_t v){for(int i=0;i<4;i++)wav[pos+i]=(unsigned char)(v>>(8*i));};
 u32(4,36+bytes);std::memcpy(wav.data()+8,"WAVEfmt ",8);
 u32(16,16);u16(20,3);u16(22,(uint16_t)channels);
 u32(24,kRate);u32(28,kRate*channels*4);u16(32,(uint16_t)(channels*4));u16(34,32);
 std::memcpy(wav.data()+36,"data",4);u32(40,bytes);
 for(size_t i=0;i<data.size();i++){
  uint32_t bits;std::memcpy(&bits,&data[i],4);u32(44+i*4,bits);
 }
 // O_EXCL/no-follow prevents clobbering an earlier render or a symlink.
 const int fd=::open(path.c_str(),O_WRONLY|O_CREAT|O_EXCL|O_NOFOLLOW,0600);
 if(fd<0)throw std::runtime_error("native output exists, is symlink or cannot be created");
 size_t offset=0;bool ok=true;
 while(offset<wav.size()){
  const ssize_t n=::write(fd,wav.data()+offset,wav.size()-offset);
  if(n<=0){ok=false;break;}
  offset+=(size_t)n;
 }
 if(::close(fd)!=0)ok=false;
 if(!ok){::unlink(path.c_str());throw std::runtime_error("native output write failed");}
}
void run(const std::string&source,const std::string&plan,const std::string&profile,const std::string&dest){
 const bool binaural=profile=="binaural";
 if(!binaural && profile!="surround_5_1")throw std::runtime_error("unsupported or quarantined layout: "+profile);
 const auto layout=binaural?spaudio::OutputLayout::Binaural:spaudio::OutputLayout::FivePointOne;
 if(!binaural){
  const auto names=spaudio::Layout::getMatchingLayout(layout).channelNames();
  if(names!=std::vector<std::string>{"M+030","M-030","M+000","LFE1","M+110","M-110"})
   throw std::runtime_error("native channel order drift");
 }
 const std::vector<float>input=readSource(source);
 std::ifstream file(plan);if(!file)throw std::runtime_error("cannot open Go block plan");
 spaudio::StreamInformation info;
 info.nChannels=1;info.typeDefinition={spaudio::TypeDefinition::Objects};
 spaudio::Renderer renderer;
 if(!renderer.Configure(layout,1,kRate,kFrame,info,"",true))throw std::runtime_error("native Configure failed");
 const unsigned channels=renderer.GetSpeakerCount();
 if(channels!=(binaural?2u:6u))throw std::runtime_error("native output count mismatch");
 renderer.Reset();
 std::vector<std::vector<float>>out(channels,std::vector<float>(kFrame,0.f));
 std::vector<float*>ptrs;for(auto&v:out)ptrs.push_back(v.data());
 std::vector<float>result;result.reserve(input.size()*channels);
 std::vector<float>sourceBlock(kFrame,0.f);
 size_t consumed=0,blocks=0;double peak=0;
 int start=0,n=0;double az=0,el=0,distance=0;
 while(file>>start>>n>>az>>el>>distance){
  if(start<0 || (size_t)start!=consumed || n<=0 || n>(int)kFrame || consumed+(size_t)n>input.size()
  || !std::isfinite(az)||!std::isfinite(el)||!std::isfinite(distance)
  || std::abs(az)>180 || std::abs(el)>90 || distance<=0)
   throw std::runtime_error("invalid or discontinuous block metadata");
  std::fill(sourceBlock.begin(),sourceBlock.end(),0.f);
  std::copy(input.begin()+consumed,input.begin()+consumed+n,sourceBlock.begin());
  spaudio::ObjectMetadata md;
  md.blockLength=kFrame;md.trackInd=0;
  md.position=spaudio::PolarPosition<double>{az,el,distance};
  md.jumpPosition.flag=false;
  renderer.AddObject(sourceBlock.data(),kFrame,md);
  for(auto&v:out)std::fill(v.begin(),v.end(),0.f);
  renderer.GetRenderedAudio(ptrs.data(),kFrame);
  for(int i=0;i<n;i++)for(unsigned ch=0;ch<channels;ch++){
   const float sample=out[ch][i];
   if(!std::isfinite(sample))throw std::runtime_error("native nonfinite output at block "+std::to_string(blocks));
   peak=std::max(peak,std::abs((double)sample));
   result.push_back(sample);
  }
  consumed+=(size_t)n;blocks++;
 }
 if(!file.eof())throw std::runtime_error("malformed block plan suffix");
 if(consumed!=input.size() || blocks==0 || peak<1.e-6 || peak>1.0)
  throw std::runtime_error("partial, silent or clipped native audio");
 writeFloatWav(dest,result,channels);
 std::cout<<"spatial_scene_native_PASS profile="<<profile<<" source_frames="<<input.size()
  <<" channels="<<channels<<" blocks="<<blocks<<" peak="<<peak
  <<" native_stereo_QUARANTINED=true"<<std::endl;
}
// W3a native two-object render: same receiver and sample-clock, separate source
// buffers, stable emitter IDs, independently admitted Go source SHA receipts.
void runDual(const std::string&srcA,const std::string&srcB,const std::string&plan,const std::string&dest){
 const auto a=readSource(srcA),b=readSource(srcB);
 if(a.size()!=b.size()||a.empty())throw std::runtime_error("independent source frame mismatch");
 if(srcA==srcB)throw std::runtime_error("distinct source paths required");
 const auto layout=spaudio::OutputLayout::FivePointOne;
 const auto labels=spaudio::Layout::getMatchingLayout(layout).channelNames();
 if(labels!=std::vector<std::string>{"M+030","M-030","M+000","LFE1","M+110","M-110"})
  throw std::runtime_error("native 5.1 label/order drift");
 spaudio::StreamInformation info;
 info.nChannels=2;
 info.typeDefinition={spaudio::TypeDefinition::Objects,spaudio::TypeDefinition::Objects};
 spaudio::Renderer renderer;
 if(!renderer.Configure(layout,1,kRate,kFrame,info,"",true))throw std::runtime_error("two-input renderer Configure failed");
 if(renderer.GetSpeakerCount()!=6)throw std::runtime_error("wrong native layout");
 renderer.Reset();
 std::ifstream in(plan);if(!in)throw std::runtime_error("missing Go dual blockplan");
 std::vector<std::vector<float>>out(6,std::vector<float>(kFrame,0.f));
 std::vector<float*>ptrs;
 for(auto&v:out)ptrs.push_back(v.data());
 std::vector<float>data;
 data.reserve(a.size()*6);
 std::vector<float>blockA(kFrame),blockB(kFrame);
 size_t consumed=0,blocks=0;double peak=0;
 int start=0,n=0;
 std::string idA,idB;
 double azA=0,elA=0,distA=0,gainA=0,azB=0,elB=0,distB=0,gainB=0;
 while(in>>start>>n>>idA>>azA>>elA>>distA>>gainA>>idB>>azB>>elB>>distB>>gainB){
  if(start<0 || (size_t)start!=consumed || n<=0 || n>(int)kFrame ||
     consumed+(size_t)n>a.size() || idA!="robot_a" || idB!="robot_b")
   throw std::runtime_error("dual-track id/time/frame discontinuity");
  const auto valid=[](double az,double el,double distance,double gain){
    return std::isfinite(az)&&std::isfinite(el)&&std::isfinite(distance)&&std::isfinite(gain)
      &&std::abs(az)<=180&&std::abs(el)<=90&&distance>0
      &&gain>0&&gain<=1;
  };
  if(!valid(azA,elA,distA,gainA)||!valid(azB,elB,distB,gainB))
   throw std::runtime_error("invalid source pose or gain");
  std::fill(blockA.begin(),blockA.end(),0.f);
  std::fill(blockB.begin(),blockB.end(),0.f);
  for(int i=0;i<n;i++){
   blockA[i]=(float)(a[consumed+(size_t)i]*gainA);
   blockB[i]=(float)(b[consumed+(size_t)i]*gainB);
  }
  spaudio::ObjectMetadata ma,mb;
  ma.blockLength=kFrame;ma.trackInd=0;
  ma.position=spaudio::PolarPosition<double>{azA,elA,distA};
  ma.jumpPosition.flag=false;
  mb.blockLength=kFrame;mb.trackInd=1;
  mb.position=spaudio::PolarPosition<double>{azB,elB,distB};
  mb.jumpPosition.flag=false;
  renderer.AddObject(blockA.data(),kFrame,ma);
  renderer.AddObject(blockB.data(),kFrame,mb);
  for(auto&v:out)std::fill(v.begin(),v.end(),0.f);
  renderer.GetRenderedAudio(ptrs.data(),kFrame);
  for(int i=0;i<n;i++)for(unsigned ch=0;ch<6;ch++){
   const float v=out[ch][i];
   if(!std::isfinite(v))throw std::runtime_error("dual scene NaN at block "+std::to_string(blocks));
   peak=std::max(peak,std::abs((double)v));
   data.push_back(v);
  }
  consumed+=(size_t)n;blocks++;
 }
 if(!in.eof())throw std::runtime_error("invalid dual blockplan suffix");
 if(consumed!=a.size() || blocks==0 || peak<1e-7 || peak>1)
  throw std::runtime_error("silent, clipped, partial or missing dual block plan");
 writeFloatWav(dest,data,6);  // Uses inherited O_EXCL + O_NOFOLLOW.
 std::cout<<"dual_spatial_native_PASS emitters=2 frames="<<consumed
  <<" channels=6 blocks="<<blocks<<" peak="<<peak
  <<" native_stereo_QUARANTINED=true"<<std::endl;
}

}
int main(int argc,char**argv){
 if(argc!=5){std::cerr<<"usage: native-dual robot_a.wav robot_b.wav dual-plan.tsv NEW_5.1.wav\n";return 2;}
 try{runDual(argv[1],argv[2],argv[3],argv[4]);return 0;}
 catch(const std::exception&e){std::cerr<<"DUAL_NATIVE_FIRST_FAILURE "<<e.what()<<'\n';return 1;}
}
