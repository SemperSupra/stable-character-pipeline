// Public synthetic renderer admission, pinned upstream runtime compiled separately.
// This file is first-party qualification logic, not a copied implementation.
#include "Renderer.h"
#include "RendererMetadata.h"
#include "LoudspeakerLayouts.h"
#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
constexpr unsigned kRate=48000, kFrames=1024, kBlocks=24;
struct Target { const char* name; spaudio::OutputLayout layout; unsigned count; };
const Target kTargets[]={
 {"stereo",spaudio::OutputLayout::Stereo,2},
 {"binaural",spaudio::OutputLayout::Binaural,2},
 {"surround_5_1",spaudio::OutputLayout::FivePointOne,6},
 {"surround_7_1",spaudio::OutputLayout::SevenPointOne,8},
 {"immersive_5_1_4",spaudio::OutputLayout::FivePointOnePointFour,10},
 {"immersive_7_1_4",spaudio::OutputLayout::SevenPointOnePointFour,12},
};
void put16(std::ofstream& f, uint16_t v){char b[2]={(char)(v&255),(char)((v>>8)&255)};f.write(b,2);}
void put32(std::ofstream& f, uint32_t v){char b[4]={(char)(v&255),(char)((v>>8)&255),(char)((v>>16)&255),(char)((v>>24)&255)};f.write(b,4);}
// IEEE f32 multichannel WAV, channel mapping authoritative in adjacent JSON, not WAV default masks.
void writeWAV(const std::string& path,unsigned n,const std::vector<float>& interleaved){
 std::ofstream f(path,std::ios::binary);if(!f)throw std::runtime_error("cannot create wav");
 const uint64_t count=interleaved.size();
 if(count>std::numeric_limits<uint32_t>::max()/4)throw std::runtime_error("wave >4GB");
 const auto dataBytes=(uint32_t)(count*4);
 f.write("RIFF",4);put32(f,36+dataBytes);f.write("WAVEfmt ",8);
 put32(f,16);put16(f,3);put16(f,(uint16_t)n);put32(f,kRate);
 put32(f,kRate*n*4);put16(f,(uint16_t)(n*4));put16(f,32);
 f.write("data",4);put32(f,dataBytes);
 for(float x:interleaved){uint32_t bits;std::memcpy(&bits,&x,4);put32(f,bits);}
 if(!f)throw std::runtime_error("WAV I/O failure");
}
void one(const Target& t,const std::string& dir,unsigned hoaOrder=1){
 spaudio::StreamInformation in;
 in.nChannels=1;
 in.typeDefinition={spaudio::TypeDefinition::Objects};
 spaudio::Renderer renderer;
 if(!renderer.Configure(t.layout,hoaOrder,kRate,kFrames,in,"",true))throw std::runtime_error(std::string(t.name)+" configure failed");
 const unsigned channels=renderer.GetSpeakerCount();
 if(channels!=t.count)throw std::runtime_error(std::string(t.name)+" unexpected channel count "+std::to_string(channels));
 renderer.Reset(); // control: explicitly clear configured buffers, filters and interpolators
 std::vector<std::vector<float>> bufs(channels,std::vector<float>(kFrames,0.f));
 std::vector<float*> pointers;for(auto& c:bufs)pointers.push_back(c.data());
 std::vector<float> inSignal(kFrames);
 std::vector<float> interleaved;interleaved.reserve((size_t)kBlocks*kFrames*channels);
 std::vector<double> energy(channels,0.0);
 double absMax=0.0;bool positive=false;
 for(unsigned block=0;block<kBlocks;block++){
   for(unsigned i=0;i<kFrames;i++){
    const double tsec=(double)(block*kFrames+i)/kRate;
    inSignal[i]=(float)(0.11*std::sin(2.0*3.141592653589793*410.0*tsec));
   }
   spaudio::ObjectMetadata md;
   md.blockLength=kFrames;
   md.trackInd=0;
   const double span=(t.layout==spaudio::OutputLayout::Stereo) ? 20.0 : 70.0;
   md.position=spaudio::PolarPosition<double>{block < kBlocks/2 ? span : -span, 0.0, 1.0};
   md.jumpPosition.flag=false; // control experiment: gain interpolation rather than zero-length jumps
   renderer.AddObject(inSignal.data(),kFrames,md);
   for(auto &c:bufs)std::fill(c.begin(),c.end(),0.f);
   renderer.GetRenderedAudio(pointers.data(),kFrames);
   for(unsigned i=0;i<kFrames;i++){
     for(unsigned ch=0;ch<channels;ch++){
       const float s=bufs[ch][i];
       if(!std::isfinite(s))throw std::runtime_error(std::string(t.name)+" NaN/Inf block="+std::to_string(block)+" sample="+std::to_string(i)+" channel="+std::to_string(ch)+" azimuth="+std::to_string(block < kBlocks/2 ? span : -span));
       absMax=std::max(absMax,std::abs((double)s));
       energy[ch]+=(double)s*s;
       if(s!=0.f)positive=true;
       interleaved.push_back(s);
     }
   }
 }
 if(!positive || absMax<1.e-7 || absMax>1.0)throw std::runtime_error(std::string(t.name)+" silent or clipped output");
 const std::string dest=dir+"/"+t.name+".wav";
 writeWAV(dest,channels,interleaved);
 std::cout<<"{\"profile\":\""<<t.name<<"\",\"channels\":"<<channels
          <<",\"samples_per_channel\":"<<(kBlocks*kFrames)
          <<",\"peak\":"<<std::setprecision(9)<<absMax<<",\"channel_energy\":[";
 for(unsigned ch=0;ch<channels;ch++){if(ch)std::cout<<",";std::cout<<std::setprecision(9)<<energy[ch];}
 std::cout<<"],\"wav\":\""<<t.name<<".wav\"}"<<std::endl;
}
}
int main(int argc,char**argv){
 if(argc!=3){std::cerr<<"usage: spatial-qual supported|stereo-negative OUTPUT_DIRECTORY\n";return 2;}
 const std::string mode=argv[1];
 if(mode=="stereo-negative"){
   try{one(kTargets[0],argv[2]);std::cerr<<"unexpected_stereo_success_not_yet_qualified\n";return 0;}
   catch(const std::exception&e){std::cerr<<"spatial_native_FIRST_FAILURE "<<e.what()<<'\n';return 1;}
 }
 if(mode=="stereo-hoa0"){
   try{one(kTargets[0],argv[2],0);std::cout<<"stereo_hoa0_FINITE_CONTROL_ONLY not_admitted"<<std::endl;return 0;}
   catch(const std::exception&e){std::cerr<<"stereo_hoa0_FIRST_FAILURE "<<e.what()<<'\n';return 1;}
 }
 if(mode!="supported"){std::cerr<<"unknown diagnostic mode\n";return 2;}
 bool failed=false;
 for(const auto&t:kTargets){
  if(t.layout==spaudio::OutputLayout::Stereo)continue; // quarantined: proven NaN on first sample
  try{one(t,argv[2]);}
  catch(const std::exception&e){std::cerr<<"spatial_native_FIRST_FAILURE "<<e.what()<<'\n';failed=true;}
 }
 if(failed)return 1;
 std::cout<<"spatial_native_PASS profiles=5 stereo=UNQUALIFIED"<<std::endl;
 return 0;
}
