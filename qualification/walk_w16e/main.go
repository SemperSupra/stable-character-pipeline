package main

// Original public synthetic W16-E. Exact rational source-origin clock mapper.
// Float wall-clock time is forbidden in admission/equality; no media sync claim.
import (
 "encoding/json"
 "errors"
 "fmt"
 "math/big"
 "os"
)
const schema="scp.walk_exact_rational_av.v1"
const rights="ORIGINAL_SELF_AUTHORED_SYNTHETIC"
type Clock struct {
 Tick string `json:"tick"`
 RateNumerator string `json:"rate_num"`
 RateDenominator string `json:"rate_den"`
 OriginNumerator string `json:"origin_num"`
 OriginDenominator string `json:"origin_den"`
}
type Stamp struct {
 Numerator string `json:"numerator"`
 Denominator string `json:"denominator"`
}
type Packet struct {
 Schema string `json:"schema"`
 Rights string `json:"source_rights"`
 ClockScope string `json:"clock_scope"`
 MotionFramesPerSecond string `json:"motion_fps"`
 VideoFramesPerSecond string `json:"video_fps"`
 SamplesPerSecond string `json:"pcm_rate_hz"`
 MotionFrame12 Stamp `json:"motion_frame_12_seconds"`
 VideoFrame24 Stamp `json:"video_frame_24_seconds"`
 AudioSample48000 Stamp `json:"audio_sample_48000_seconds"`
 MotionToPCMExactSamples string `json:"samples_per_motion_frame"`
 VideoToPCMExactSamples string `json:"samples_per_video_frame"`
 OneNTSCFrameInPCMSamples Stamp `json:"samples_per_30000_1001_video_frame"`
 LargeAdjacentTickDistinct bool `json:"large_adjacent_tick_distinct"`
 Profile string `json:"profile"`
 Scope string `json:"scope"`
}
func integer(s string)(*big.Int,error){
 x,ok:=new(big.Int).SetString(s,10)
 if !ok || len(s)==0{return nil,errors.New("CLOCK_INTEGER_INVALID")}
 // Canonical decimal: refuse +0, leading zeros, scientific or whitespace.
 if x.String()!=s{return nil,errors.New("CLOCK_NONCANONICAL_INTEGER")}
 return x,nil
}
func rational(a,b string)(*big.Rat,error){
 x,e:=integer(a);if e!=nil{return nil,e}
 y,e:=integer(b);if e!=nil{return nil,e}
 if y.Sign()<=0{return nil,errors.New("CLOCK_DEN_NONPOSITIVE")}
 return new(big.Rat).SetFrac(x,y),nil
}
func timestamp(c Clock)(*big.Rat,error){
 tick,e:=integer(c.Tick);if e!=nil{return nil,e}
 rate,e:=rational(c.RateNumerator,c.RateDenominator);if e!=nil{return nil,e}
 if rate.Sign()<=0{return nil,errors.New("CLOCK_RATE_NONPOSITIVE")}
 origin,e:=rational(c.OriginNumerator,c.OriginDenominator);if e!=nil{return nil,e}
 return new(big.Rat).Add(origin,new(big.Rat).Quo(new(big.Rat).SetInt(tick),rate)),nil
}
func stamp(t *big.Rat)Stamp{return Stamp{t.Num().String(),t.Denom().String()}}
func same(a,b Clock)(bool,error){
 x,e:=timestamp(a);if e!=nil{return false,e}
 y,e:=timestamp(b);if e!=nil{return false,e}
 return x.Cmp(y)==0,nil
}
func sampleIndex(c Clock,sampleRate string)(*big.Rat,error){
 t,e:=timestamp(c);if e!=nil{return nil,e}
 n,e:=integer(sampleRate);if e!=nil{return nil,e}
 if n.Sign()<=0{return nil,errors.New("CLOCK_SAMPLE_RATE_NONPOSITIVE")}
 return new(big.Rat).Mul(t,new(big.Rat).SetInt(n)),nil
}
func packet(profile string)(Packet,error){
 if profile!="forward"&&profile!="outward"{return Packet{},errors.New("PROFILE")}
 at:=func(t,rateNum,rateDen string)Clock{
  return Clock{Tick:t,RateNumerator:rateNum,RateDenominator:rateDen,
   OriginNumerator:"0",OriginDenominator:"1"}
 }
 m,err:=timestamp(at("12","12","1"));if err!=nil{return Packet{},err}
 v,err:=timestamp(at("24","24","1"));if err!=nil{return Packet{},err}
 a,err:=timestamp(at("48000","48000","1"));if err!=nil{return Packet{},err}
 if m.Cmp(v)!=0||m.Cmp(a)!=0{return Packet{},errors.New("ONE_SECOND_CROSS_DOMAIN_DRIFT")}
 pPerM,err:=sampleIndex(at("1","12","1"),"48000");if err!=nil{return Packet{},err}
 pPerV,err:=sampleIndex(at("1","24","1"),"48000");if err!=nil{return Packet{},err}
 ntsc,err:=sampleIndex(at("1","30000","1001"),"48000");if err!=nil{return Packet{},err}
 if pPerM.RatString()!="4000"||pPerV.RatString()!="2000"||ntsc.RatString()!="8008/5"{
  return Packet{},errors.New("EXACT_SAMPLE_TIME_CROSSWALK")
 }
 // The exact known float64 failure case must NOT alias adjacent huge ticks.
 large:="1152921504606846976" // 2^60, beyond float64 1-tick resolution.
 next:="1152921504606846977"
 s,e:=same(at(large,"30","1"),at(next,"30","1"));if e!=nil{return Packet{},e}
 if s{return Packet{},errors.New("LARGE_TICK_FALSE_CLOCK_EQUALITY")}
 return Packet{Schema:schema,Rights:rights,ClockScope:"ARTIFICIAL_ALIGNED_ZERO_ORIGIN_RATIONAL_ONLY",
  MotionFramesPerSecond:"12/1",VideoFramesPerSecond:"24/1",SamplesPerSecond:"48000/1",
  MotionFrame12:stamp(m),VideoFrame24:stamp(v),AudioSample48000:stamp(a),
  MotionToPCMExactSamples:pPerM.RatString(),VideoToPCMExactSamples:pPerV.RatString(),
  OneNTSCFrameInPCMSamples:stamp(ntsc),LargeAdjacentTickDistinct:true,
  Profile:profile,Scope:"CLOCK_MATHEMATICS_ONLY_NO_SOURCE_AV_MUX_NO_MMD_ADMISSION"},nil
}
func main(){
 if len(os.Args)!=3{fmt.Fprintln(os.Stderr,"usage: w16e forward|outward receipt.json");os.Exit(2)}
 p,e:=packet(os.Args[1]);if e!=nil{panic(e)}
 data,e:=json.MarshalIndent(p,"","  ");if e!=nil{panic(e)}
 if e=os.WriteFile(os.Args[2],append(data,10),0644);e!=nil{panic(e)}
 fmt.Println("W16E_EXACT_AV_CLOCK_PASS",p.Profile,p.MotionToPCMExactSamples,p.OneNTSCFrameInPCMSamples)
}
