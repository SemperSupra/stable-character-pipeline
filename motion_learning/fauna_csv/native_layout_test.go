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
    // Caller-supplied integrity pin does not prove file rights.
    o,e:=ProbeNativeLayout(raw,Digest(raw))
    if e!=nil{t.Fatal(e)}
    if o.Schema!=NativeCSVSchema||o.Status!="PASS_NATIVE_LAYOUT_SHAPE_ONLY"||
       o.DatasetAdmission!="NOT_ADMITTED"||o.SourceAuthority!="PINNED_PUBLIC_THIRD_PARTY_COPY_NOT_ORIGINAL_VHDC_BYTES" ||
       o.DataRows!=5||o.FirstFrame!=1||o.LastFrame!=5 ||
       o.LandmarkXYZChannelsPresent!=true {
        t.Fatalf("inconsistent original synthetic header shape: %+v",o)
    }
    if o.FirstTimeNumber!=0||math.Abs(o.LastTimeNumber-.067)>1e-9||
       math.Abs(o.MinTimeDeltaNumber-.016)>1e-9||math.Abs(o.MaxTimeDeltaNumber-.017)>1e-9 {
        t.Fatalf("lossy timestamp rounding not detected: %+v",o)
    }
    if o.FPS!="UNKNOWN"||o.Units!="UNKNOWN"||o.SourceAxes!="UNKNOWN"||
       o.RootFrame!="UNKNOWN"||o.TruePhysicalContactEstablished||
       o.MeasurementOriginIndependentlyAuthenticated||o.OriginalSiteBytesIndependentlyAuthenticated{
        t.Fatal("schema-only reference promoted to measured physics/source rights")
    }
}
func TestNativeShapeMutationKill(t *testing.T){
    raw:=nativeFixture(t)
    cases:=[]struct{name string;fn func(string)string}{
        {"copied source authenticity marker",func(s string)string{return strings.Replace(s,`"Frame#"`,`"Time"`,`"HeadX"`,`"HeadY"`,`"HeadZ"`,`"WithersX"`,`"WithersY"`,`"WithersZ"`,`"SacrumX"`,`"SacrumY"`,`"SacrumZ"`,`"HFLX"`,`"HFLY"`,`"HFLZ"`,`"HFRX"`,`"HFRY"`,`"HFRZ"`,`"HHLX"`,`"HHLY"`,`"HHLZ"`,`"HHRX"`,`"HHRY"`,`"HHRZ"`, "WRONG_HEADER",1)}},
        {"time renamed",func(s string)string{return strings.Replace(s,`"Time"`,`"HeadX"`,`"TimeMilliseconds"`,`"HeadX"`,1)}},
        {"source channel reorder",func(s string)string{return strings.Replace(s,`"HFLX"`,`"HFLY"`,`"HFLY"`,`"HFLX"`,1)}},
        {"nonfinite measurement",func(s string)string{return strings.Replace(s,"1,0.000,10,","1,0.000,NaN,",1)}},
        {"negative timestamp",func(s string)string{return strings.Replace(s,"2,0.017,","2,-0.017,",1)}},
        {"nonmonotonic timestamp",func(s string)string{return strings.Replace(s,"3,0.033,","3,0.017,",1)}},
        {"missing frame",func(s string)string{return strings.Replace(s,"3,0.033,","4,0.033,",1)}},
        {"duplicate frame",func(s string)string{return strings.Replace(s,"3,0.033,","2,0.033,",1)}},
        {"unnaturally large coordinate",func(s string)string{return strings.Replace(s,"1,0.000,10,","1,0.000,1000000001,",1)}},
        {"extra column",func(s string)string{return strings.Replace(s,"1,0.000,10,","1,0.000,999,10,",1)}},
        {"missing column",func(s string)string{return strings.Replace(s,"1,0.000,10,","1,0.000,",1)}},
        {"too few rows",func(s string)string{return strings.Join(strings.Split(s,"
")[:3],"
")}},
    }
    for _,tc:=range cases{t.Run(tc.name,func(t *testing.T){
       changed:=[]byte(tc.fn(string(raw)))
       if bytes.Equal(changed,raw){t.Fatal("test mutation did not change source")}
       if _,e:=ProbeNativeLayout(changed,Digest(changed));e==nil{
          t.Fatal("source invalid despite exact recomputed hash (hash alone not schema approval)")
       }
    })}
    if _,e:=ProbeNativeLayout(raw,strings.Repeat("0",64));e==nil{
        t.Fatal("accepted wrong independently supplied digest")
    }
    if _,e:=ProbeNativeLayout(raw,"");e==nil{
        t.Fatal("accepted missing expected digest")
    }
    if _,e:=ProbeNativeLayout([]byte(""),Digest(raw));e==nil{
        t.Fatal("accepted empty source")
    }
}
func TestSyntheticMarkerAndNativeHeaderRemainDisjoint(t *testing.T){
    old,e:=os.ReadFile("testdata/original.synthetic-horse.csv");if e!=nil{t.Fatal(e)}
    if _,e:=ProbeNativeLayout(old,Digest(old));e==nil{
        t.Fatal("legacy synthetic marker CSV accepted as native header")
    }
    native:=nativeFixture(t)
    if _,e:=Parse(native,"synthetic:horse","synthetic:session");e==nil{
        t.Fatal("native-shaped synthetic CSV accepted as legacy data without explicit marker")
    }
}
