package fauna_csv

import (
    "bytes"
    "math"
    "os"
    "strings"
    "testing"
)

func nativeFixture(t *testing.T)[]byte{
    t.Helper()
    b,e:=os.ReadFile("testdata/original.synthetic-native-layout.csv")
    if e!=nil{t.Fatal(e)}
    return b
}
func TestNativeLayoutOriginalSyntheticOnly(t *testing.T){
    raw:=nativeFixture(t)
    p,e:=ProbeNativeLayout(raw,Digest(raw))
    if e!=nil{t.Fatal(e)}
    if p.Schema!=NativeCSVSchema||p.Status!="PASS_NATIVE_LAYOUT_SHAPE_ONLY"||
       p.DatasetAdmission!="NOT_ADMITTED"||p.SourceAuthority!="NOT_ATTESTED_LAYOUT_REFERENCE_ONLY" ||
       p.DataRows!=5||p.FirstFrame!=1||p.LastFrame!=5 ||
       !p.LandmarkXYZChannelsPresent {
        t.Fatalf("invalid structural receipt: %+v",p)
    }
    if p.FirstTimeNumber!=0||math.Abs(p.LastTimeNumber-.067)>1e-9||
       math.Abs(p.MinTimeDeltaNumber-.016)>1e-9||math.Abs(p.MaxTimeDeltaNumber-.017)>1e-9 {
        t.Fatalf("timestamp resolution needs explicit interval variation: %+v",p)
    }
    if p.FPS!="UNKNOWN"||p.Units!="UNKNOWN"||p.SourceTimeUnit!="UNKNOWN"||
       p.SourceAxes!="UNKNOWN"||p.RootFrame!="UNKNOWN"||
       p.TruePhysicalContactEstablished||p.MeasurementOriginIndependentlyAuthenticated||
       p.OriginalSiteBytesIndependentlyAuthenticated {
        t.Fatal("metadata-only source reference promoted to physical truth or rights")
    }
}
func TestNativeShapeMutationKill(t *testing.T){
    raw:=nativeFixture(t)
    cases:=[]struct{name string;fn func(string)string}{
        {"source frame header",func(s string)string{return strings.Replace(s,"Frame#","WrongFrame",1)}},
        {"time column name",func(s string)string{return strings.Replace(s,"Time","TimeMilliseconds",1)}},
        {"duplicate marker",func(s string)string{return strings.Replace(s,"HFLX","HFLY",1)}},
        {"nonfinite measurement",func(s string)string{return strings.Replace(s,"1,0.000,10,","1,0.000,NaN,",1)}},
        {"negative timestamp",func(s string)string{return strings.Replace(s,"2,0.017,","2,-0.017,",1)}},
        {"nonmonotonic timestamp",func(s string)string{return strings.Replace(s,"3,0.033,","3,0.017,",1)}},
        {"missing source frame",func(s string)string{return strings.Replace(s,"3,0.033,","4,0.033,",1)}},
        {"duplicate source frame",func(s string)string{return strings.Replace(s,"3,0.033,","2,0.033,",1)}},
        {"unbounded coordinate",func(s string)string{return strings.Replace(s,"1,0.000,10,","1,0.000,1000000001,",1)}},
        {"extra coordinate",func(s string)string{return strings.Replace(s,"1,0.000,10,","1,0.000,999,10,",1)}},
        {"missing coordinate",func(s string)string{return strings.Replace(s,"1,0.000,10,","1,0.000,",1)}},
        {"too few rows",func(s string)string{
            lines:=strings.Split(s,string(rune(10)))
            return strings.Join(lines[:3],string(rune(10)))
        }},
    }
    for _,tc:=range cases{t.Run(tc.name,func(t *testing.T){
        changed:=[]byte(tc.fn(string(raw)))
        if bytes.Equal(changed,raw){t.Fatal("mutation did not change bytes")}
        if _,e:=ProbeNativeLayout(changed,Digest(changed));e==nil{
            t.Fatal("changed bytes and updated digest must not bypass schema check")
        }
    })}
    if _,e:=ProbeNativeLayout(raw,strings.Repeat("0",64));e==nil{
        t.Fatal("accepted wrong independently supplied SHA256")
    }
    if _,e:=ProbeNativeLayout(raw,"");e==nil{
        t.Fatal("accepted absent independently supplied SHA256")
    }
    if _,e:=ProbeNativeLayout(nil,Digest(raw));e==nil{
        t.Fatal("accepted empty source")
    }
}
func TestSyntheticMarkerAndNativeHeaderDisjoint(t *testing.T){
    old,e:=os.ReadFile("testdata/original.synthetic-horse.csv");if e!=nil{t.Fatal(e)}
    if _,e:=ProbeNativeLayout(old,Digest(old));e==nil{
        t.Fatal("legacy synthetic marker source accepted as native shape")
    }
    fresh:=nativeFixture(t)
    if _,e:=Parse(fresh,"synthetic:horse","synthetic:session");e==nil{
        t.Fatal("native-shaped synthetic source silently accepted as previous synthetic format")
    }
}
