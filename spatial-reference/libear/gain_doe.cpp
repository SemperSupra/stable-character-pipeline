// Native EBU libear public Apache-2.0 source, exact same 42 Go DoE case directions.
// EBU gains are not directly comparable to VideoLAN time-domain PCM without
// explicitly accounting for renderer interpolation/diffuse terms.
#include "ear/ear.hpp"
#include <cmath>
#include <fstream>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
#include <iomanip>
using namespace ear;
struct LayoutDef{
 const char* name; const char* libear; std::vector<std::string> channels;
};
const LayoutDef layouts[]={
 {"surround_5_1","0+5+0",{"M+030","M-030","M+000","LFE1","M+110","M-110"}},
 {"surround_7_1","0+7+0",{"M+030","M-030","M+000","LFE1","M+090","M-090","M+135","M-135"}}
};
int main(int argc,char**argv){
 if(argc!=3){std::cerr<<"usage: gain_doe CASES.tsv OUT.tsv\n";return 2;}
 try{
  std::ifstream cases(argv[1]);
  std::ofstream out(argv[2],std::ios::out|std::ios::trunc);
  if(!cases||!out)throw std::runtime_error("cannot open source case table or output");
  out<<std::setprecision(10);
  int rows=0;
  for(const auto&c:layouts){
   Layout layout=getLayout(c.libear);
   if(layout.channels().size()!=c.channels.size())throw std::runtime_error("wrong native EBU layout");
   for(size_t k=0;k<c.channels.size();k++)
    if(layout.channels()[k].name()!=c.channels[k])throw std::runtime_error("native EBU channel order drift");
   GainCalculatorObjects calculator(layout);
   cases.clear(); cases.seekg(0);
   std::string id;double az,el,yaw;
   int n=0;
   while(cases>>id>>az>>el>>yaw){
    if(!std::isfinite(az)||!std::isfinite(el)||!std::isfinite(yaw)||
       std::abs(az)>180||el<0||el>30||yaw<0||yaw>180)
      throw std::runtime_error("inadmissible source geometry");
    ObjectsTypeMetadata meta;
    meta.position=PolarPosition(float(az),float(el),1.f);
    std::vector<float> direct(c.channels.size()),diffuse(c.channels.size());
    calculator.calculate(meta,direct,diffuse);
    double power=0;
    for(size_t j=0;j<direct.size();j++){
      if(!std::isfinite(direct[j])||!std::isfinite(diffuse[j])||
         direct[j]<-1e-7f||std::abs(direct[j])>1.001f)
        throw std::runtime_error("EBU nonfinite or negative output");
      power+=double(direct[j])*direct[j]+double(diffuse[j])*diffuse[j];
    }
    if(power<0.01||power>4 || std::abs(direct[3])>1e-6||std::abs(diffuse[3])>1e-6)
      throw std::runtime_error("EBU illegal energy or object routed into LFE");
    out<<id<<'\t'<<c.name<<'\t'<<az<<'\t'<<el<<'\t'<<yaw<<'\t';
    for(size_t j=0;j<direct.size();j++){if(j)out<<',';out<<direct[j];}
    out<<'\t';
    for(size_t j=0;j<diffuse.size();j++){if(j)out<<',';out<<diffuse[j];}
    out<<'\n';rows++;n++;
   }
   if(n!=42)throw std::runtime_error("EBU missing scheduled 42 case positions");
  }
  out.flush();if(!out)throw std::runtime_error("native EBU write failure");
  if(rows!=84)throw std::runtime_error("native EBU incomplete 5.1/7.1 rows");
  std::cout<<"SPATIAL_W3C_EBU_REAL_NATIVE_PASS rows="<<rows
           <<" layouts=surround_5_1,surround_7_1 upstream_source_only"<<std::endl;
 }catch(const std::exception&e){
  std::cerr<<"SPATIAL_W3C_EBU_FIRST_FAILURE "<<e.what()<<std::endl;return 1;
 }
 return 0;
}
