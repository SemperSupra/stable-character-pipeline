package main

import (
    "bytes"
    "crypto/sha256"
    "encoding/json"
    "errors"
    "flag"
    "fmt"
    "io"
    "math"
    "os"
)

type Item struct {
    ID string `json:"id"`
    AdultState string `json:"adult_state"`
    Height float64 `json:"height_cm"`
    Shoulder float64 `json:"shoulder_cm"`
    Waist float64 `json:"waist_cm"`
    Hip float64 `json:"hip_cm"`
    Inseam float64 `json:"inseam_cm"`
    Muscularity float64 `json:"muscularity"`
    Fullness float64 `json:"fullness"`
    WaistHipRatio float64 `json:"waist_hip_ratio"`
    InseamHeightRatio float64 `json:"inseam_height_ratio"`
    NativeMHR json.RawMessage `json:"native_mhr_map"`
    NativeMPFB json.RawMessage `json:"native_mpfb_map"`
}
type Catalog struct {
    Schema int `json:"schema"`
    Status string `json:"status"`
    Items []Item `json:"items"`
}
func finite(v float64) bool { return !math.IsNaN(v) && !math.IsInf(v,0) }
func Validate(data []byte) (int,error) {
    dec:=json.NewDecoder(bytes.NewReader(data))
    dec.DisallowUnknownFields()
    var c Catalog
    if err:=dec.Decode(&c);err!=nil {return 0,err}
    var extra any
    if err:=dec.Decode(&extra);!errors.Is(err,io.EOF) {return 0,fmt.Errorf("trailing JSON or decode error: %v",err)}
    if c.Schema!=1 || c.Status!="TOY_SYNTHETIC_PUBLIC_ONLY" || len(c.Items)!=3 {return 0,errors.New("research status/schema/item count mismatch")}
    seen:=map[string]bool{}
    for _,p:=range c.Items {
        if p.ID=="" || seen[p.ID] {return 0,fmt.Errorf("duplicate/missing id %q",p.ID)}
        seen[p.ID]=true
        if p.AdultState!="FICTIONAL_ADULT" {return 0,fmt.Errorf("%s: missing fictional adult state",p.ID)}
        vals:=[]float64{p.Height,p.Shoulder,p.Waist,p.Hip,p.Inseam,p.Muscularity,p.Fullness,p.WaistHipRatio,p.InseamHeightRatio}
        for _,v:=range vals {if !finite(v) {return 0,fmt.Errorf("%s: nonfinite",p.ID)}}
        if p.Height<140 || p.Height>210 || p.Shoulder<30 || p.Shoulder>55 || p.Waist<50 || p.Waist>140 || p.Hip<50 || p.Hip>150 ||
            p.Inseam<=0 || p.Inseam>=p.Height || p.Muscularity<0 || p.Muscularity>1 || p.Fullness<0 || p.Fullness>1 {
            return 0,fmt.Errorf("%s: metric bounds",p.ID)
        }
        if math.Abs(p.WaistHipRatio-p.Waist/p.Hip)>0.00011 || math.Abs(p.InseamHeightRatio-p.Inseam/p.Height)>0.00011 {
            return 0,fmt.Errorf("%s: stale derived ratios",p.ID)
        }
        if string(p.NativeMHR)!="null" || string(p.NativeMPFB)!="null" {
            return 0,fmt.Errorf("%s: premature native slider mapping",p.ID)
        }
    }
    return len(c.Items),nil
}
func main() {
    f:=flag.String("file","fixtures.json","synthetic public fixture JSON path")
    flag.Parse()
    data,err:=os.ReadFile(*f)
    if err!=nil {fmt.Fprintln(os.Stderr,err);os.Exit(2)}
    count,err:=Validate(data)
    if err!=nil {fmt.Fprintln(os.Stderr,err);os.Exit(2)}
    digest:=sha256.Sum256(data)
    receipt:=struct{
        Status string `json:"status"`
        Items int `json:"items"`
        InputSHA256 string `json:"input_sha256"`
        Limitations []string `json:"limitations"`
    }{
        "PASS_PUBLIC_TOY_CONTRACT_ONLY",count,fmt.Sprintf("%x",digest),
        []string{"Not private CPE catalog execution","Not backend native control calibration","Not visual/photorealism/age inference","No policy verdict or canonical CPE promotion"},
    }
    out,err:=json.MarshalIndent(receipt,"","  ")
    if err!=nil {panic(err)}
    fmt.Println(string(out))
}
