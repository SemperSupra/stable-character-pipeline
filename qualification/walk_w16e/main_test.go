package main
import ("math/big";"testing")
func mk(tick,num,den string)Clock{return Clock{tick,num,den,"0","1"}}
func TestExact12Video24PCM48(t *testing.T){
 p,e:=packet("forward");if e!=nil{t.Fatal(e)}
 if p.MotionToPCMExactSamples!="4000"||p.VideoToPCMExactSamples!="2000"||
 p.OneNTSCFrameInPCMSamples.Numerator!="8008"||
 p.OneNTSCFrameInPCMSamples.Denominator!="5"{t.Fatal(p)}
 for _,tick:=range []string{"0","1","12","48","720","1152921504606846976"}{
  m:=mk(tick,"12","1"); doubled:=new(big.Int);doubled.SetString(tick,10);doubled.Mul(doubled,big.NewInt(2))
  ok,e:=same(m,mk(doubled.String(),"24","1"));if e!=nil||!ok{t.Fatal(tick,e)}
 }
}
func TestMMDHugeTickFloatCollapseRejected(t *testing.T){
 a:=mk("1152921504606846976","30","1");b:=mk("1152921504606846977","30","1")
 sameTime,e:=same(a,b);if e!=nil||sameTime{t.Fatal("MMD_REPRO_FLOAT64_FALSE_GREEN",e)}
 x,_:=timestamp(a);y,_:=timestamp(b)
 diff:=new(big.Rat).Sub(y,x)
 if diff.RatString()!="1/30"{t.Fatal(diff)}
}
func TestNegativeSourceOriginAndDrift(t *testing.T){
 a:=mk("13","12","1")
 b:=mk("26","24","1")
 b.OriginNumerator="1";b.OriginDenominator="12"
 ok,e:=same(a,b);if e!=nil||ok{t.Fatal("ORIGIN_FALSE_EQUIVALENCE")}
 b.OriginNumerator="0"
 ok,e=same(a,b);if e!=nil||!ok{t.Fatal(e)}
 b.OriginNumerator="-1";b.OriginDenominator="12"
 ok,e=same(a,b);if e!=nil||ok{t.Fatal("ORIGIN_NEGATIVE_IGNORED")}
}
func TestFractionalSampleNoSilentRounding(t *testing.T){
 s,e:=sampleIndex(mk("1","30000","1001"),"48000");if e!=nil{t.Fatal(e)}
 if s.RatString()!="8008/5"||s.IsInt(){t.Fatal(s)}
 five,e:=sampleIndex(mk("5","30000","1001"),"48000");if e!=nil||five.RatString()!="8008"{t.Fatal(five,e)}
}
func TestMalformedCasesFailClosed(t *testing.T){
 cases:=[]Clock{mk("01","12","1"),mk("1","0","1"),mk("1","12","0"),mk("1","12","-1"),
 mk("NaN","12","1"),mk("1","3.14","1"),mk("1","12","1"),mk("+1","12","1")}
 cases[6].OriginDenominator="0"
 for i,c:=range cases{if _,e:=timestamp(c);e==nil{t.Fatalf("BAD_CLOCK_%d_ACCEPTED",i)}}
 if _,e:=sampleIndex(mk("1","12","1"),"-48000");e==nil{t.Fatal("BAD_SAMPLE_RATE")}
 if _,e:=packet("unaccepted");e==nil{t.Fatal("BAD_PROFILE")}
}
