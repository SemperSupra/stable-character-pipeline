// Apache-2.0 EBU libear used as independent reference, not a copied algorithm.
#include "ear/ear.hpp"
#include <cmath>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>

using namespace ear;
namespace {
struct Config {const char* profile;const char* layout;std::vector<std::string> labels;};
const Config configs[]={
  {"surround_5_1","0+5+0",{"M+030","M-030","M+000","LFE1","M+110","M-110"}},
  {"surround_7_1","0+7+0",{"M+030","M-030","M+000","LFE1","M+090","M-090","M+135","M-135"}}
};
void one(const Config& test){
 Layout layout=getLayout(test.layout);
 if(layout.channels().size()!=test.labels.size())throw std::runtime_error("wrong EBU layout channel count");
 for(size_t i=0;i<test.labels.size();i++)if(layout.channels()[i].name()!=test.labels[i])throw std::runtime_error("EBU label mismatch "+std::string(test.profile));
 GainCalculatorObjects gain(layout);
 std::vector<std::vector<float>> results;
 for(float az:{70.f,-70.f}){
  ObjectsTypeMetadata meta;
  meta.position=PolarPosition(az,0.f,1.f);
  std::vector<float> direct(layout.channels().size()),diffuse(layout.channels().size());
  gain.calculate(meta,direct,diffuse);
  double power=0;
  for(size_t i=0;i<direct.size();i++){
   if(!std::isfinite(direct[i])||!std::isfinite(diffuse[i])||direct[i]<-1e-7f||std::abs(direct[i])>1.001f)
     throw std::runtime_error("nonfinite/negative or out-of-range gain "+std::string(test.profile));
   power+=double(direct[i])*direct[i]+double(diffuse[i])*diffuse[i];
  }
  if(power<0.1||power>2)throw std::runtime_error("implausible object gain energy "+std::string(test.profile));
  if(std::abs(direct[3])>1e-7f || std::abs(diffuse[3])>1e-7f)throw std::runtime_error("object gain routed to LFE");
  results.push_back(direct);
  std::cout<<"libear_gain_OBS profile="<<test.profile<<" azimuth="<<az<<" direct=";
  for(size_t i=0;i<direct.size();i++){if(i)std::cout<<",";std::cout<<direct[i];}
  std::cout<<" energy="<<power<<'\n';
 }
 for(size_t i=0;i<results[0].size();i++){
  size_t other=i;
  if(i==0)other=1;else if(i==1)other=0;
  else if(i>=4)other=((i&1)==0 ? i+1 : i-1);
  if(std::abs(results[0][i]-results[1][other])>0.005f)
    throw std::runtime_error("left-right mirror symmetry violated "+std::string(test.profile));
 }
 std::cout<<"libear_gain_oracle_PASS profile="<<test.profile<<" channels="<<test.labels.size()<<" LFE_object_gain=0 mirror_tolerance=0.005"<<'\n';
}
}
int main(){
 try{for(const auto&c:configs)one(c);std::cout<<"libear_reference_PASS profiles=2"<<'\n';return 0;}
 catch(const std::exception&e){std::cerr<<"libear_FIRST_FAILURE "<<e.what()<<'\n';return 1;}
}
