// groomcheck is an offline, stdlib-only source-groom identity/geometry gate.
// It does not assess motion, visual quality, animal anatomy or legal rights.
package main

import (
    "bytes"
    "crypto/sha256"
    "encoding/hex"
    "encoding/json"
    "errors"
    "fmt"
    "io"
    "math"
    "os"
    "sort"
    "strings"
)
type Fiber struct {
    ID string `json:"id"`
    Region string `json:"region"`
    SourceTriangle [3][3]float64 `json:"source_triangle_m"`
    Barycentric [3]float64 `json:"barycentric"`
    SkinWeights map[string]float64 `json:"skin_weights"`
    RestCurve [][3]float64 `json:"rest_curve_m"`
    RestLength float64 `json:"rest_length_m"`
    RootRadius float64 `json:"root_radius_m"`
    TipRadius float64 `json:"tip_radius_m"`
}
type Groom struct {
    Schema string `json:"schema"`
    GroomID string `json:"groom_id"`
    Units string `json:"units"`
    SourceKind string `json:"source_kind"`
    SourceMeshSHA256 string `json:"source_mesh_sha256"`
    Seed uint64 `json:"seed"`
    Season string `json:"season"`
    LengthScale float64 `json:"length_scale"`
    DensityScale float64 `json:"density_scale"`
    Fibers []Fiber `json:"fibers"`
}
type Receipt struct {
    Schema string `json:"schema"`
    SourceSHA256 string `json:"source_sha256"`
    Verdict string `json:"verdict"`
    FiberCount int `json:"fiber_count"`
    RegionCounts map[string]int `json:"region_counts"`
    Failures []string `json:"failures"`
    ScientificHold bool `json:"scientific_hold"`
    ReleaseAdmission bool `json:"release_admission"`
}
func finite(x float64) bool {return !math.IsNaN(x) && !math.IsInf(x,0)}
func norm3(a,b [3]float64) float64 {
    dx,dy,dz:=a[0]-b[0],a[1]-b[1],a[2]-b[2]
    return math.Sqrt(dx*dx+dy*dy+dz*dz)
}
func validate(g Groom, raw []byte) Receipt {
    receipt:=Receipt{Schema:"equine.groom.check.v1", SourceSHA256:fmt.Sprintf("%x",sha256.Sum256(raw)),
        Verdict:"REJECT_INVALID_SOURCE",RegionCounts:map[string]int{},Failures:[]string{},
        ScientificHold:true,ReleaseAdmission:false}
    bad:=func(s string){receipt.Failures=append(receipt.Failures,s)}
    if g.Schema!="equine.groom.v1" {bad("schema")}
    if len(g.GroomID)<3 || len(g.GroomID)>128 || strings.TrimSpace(g.GroomID)!=g.GroomID {bad("groom_id")}
    if g.Units!="m" {bad("units_SI")}
    if g.SourceKind!="original_synthetic" {bad("source_kind_public_gate")}
    sh,err:=hex.DecodeString(g.SourceMeshSHA256)
    if err!=nil || len(sh)!=32 || len(g.SourceMeshSHA256)!=64 {bad("source_mesh_sha256")}
    if !map[string]bool{"summer":true,"winter":true,"transitional":true}[g.Season] {bad("season")}
    if !finite(g.LengthScale)||g.LengthScale<.1||g.LengthScale>4 {bad("length_scale")}
    if !finite(g.DensityScale)||g.DensityScale<.01||g.DensityScale>5 {bad("density_scale")}
    if len(g.Fibers)<1 || len(g.Fibers)>20000 {bad("fiber_count");return receipt}
    used:=map[string]bool{}
    for index,f:=range g.Fibers{
        label:=fmt.Sprintf("fiber[%d].",index)
        if f.ID=="" || len(f.ID)>128 || used[f.ID] {bad(label+"unique_id")}
        used[f.ID]=true
        if !map[string]bool{"mane":true,"forelock":true,"tail":true,"guard":true,"undercoat":true}[f.Region] {
            bad(label+"region")
        } else {receipt.RegionCounts[f.Region]++}
        sum:=0.0
        root:=[3]float64{}
        for i,w:=range f.Barycentric {
            if !finite(w)||w<0||w>1 {bad(label+"barycentric_bounds")}
            sum+=w
            for axis,v:=range f.SourceTriangle[i]{
                if !finite(v)||math.Abs(v)>1000 {bad(label+"source_triangle_bounds")}
                root[axis]+=v*w
            }
        }
        if !finite(sum)||math.Abs(sum-1)>1e-6 {bad(label+"barycentric_sum")}
        edge1:=[3]float64{}
        edge2:=[3]float64{}
        for axis:=0;axis<3;axis++ {
            edge1[axis]=f.SourceTriangle[1][axis]-f.SourceTriangle[0][axis]
            edge2[axis]=f.SourceTriangle[2][axis]-f.SourceTriangle[0][axis]
        }
        cross:=[3]float64{
            edge1[1]*edge2[2]-edge1[2]*edge2[1],
            edge1[2]*edge2[0]-edge1[0]*edge2[2],
            edge1[0]*edge2[1]-edge1[1]*edge2[0],
        }
        area2:=math.Sqrt(cross[0]*cross[0]+cross[1]*cross[1]+cross[2]*cross[2])
        if !finite(area2)||area2<1e-10 {bad(label+"degenerate_attachment_triangle")}

        if len(f.SkinWeights)<1||len(f.SkinWeights)>8 {bad(label+"skin_groups")}
        skinSum:=0.0
        for bone,w:=range f.SkinWeights{
            if len(bone)==0 || len(bone)>128 || !finite(w) || w<=0 || w>1 {bad(label+"bone_weight")}
            skinSum+=w
        }
        if !finite(skinSum)||math.Abs(skinSum-1)>1e-6 {bad(label+"bone_sum")}
        if len(f.RestCurve)<2||len(f.RestCurve)>128 {bad(label+"rest_point_count");continue}
        for _,p:=range f.RestCurve{for _,v:=range p{if !finite(v)||math.Abs(v)>1000 {bad(label+"rest_curve_finite")}}}
        if norm3(root,f.RestCurve[0])>1e-5 {bad(label+"root_surface_mismatch")}
        length:=0.0
        for j:=1;j<len(f.RestCurve);j++{
            segment:=norm3(f.RestCurve[j-1],f.RestCurve[j])
            if !finite(segment)||segment<1e-7 {bad(label+"degenerate_segment")}
            length+=segment
        }
        if !finite(f.RestLength)||f.RestLength<=0 || f.RestLength>5 ||
            !finite(length)||math.Abs(length-f.RestLength)>math.Max(.0001,.01*f.RestLength){
            bad(label+"rest_length_m")
        }
        if !finite(f.RootRadius)||!finite(f.TipRadius)||f.RootRadius<.00001||
           f.RootRadius>.02||f.TipRadius<=0||f.TipRadius>f.RootRadius {bad(label+"taper")}
    }
    sort.Strings(receipt.Failures)
    receipt.FiberCount=len(g.Fibers)
    if len(receipt.Failures)==0 {receipt.Verdict="PASS_SOURCE_SCHEMA_ONLY"}
    return receipt
}
func run(in []byte)(Receipt,error){
    g:=Groom{}
    decoder:=json.NewDecoder(bytes.NewReader(in));decoder.DisallowUnknownFields()
    if err:=decoder.Decode(&g);err!=nil {return Receipt{},fmt.Errorf("invalid groom json: %w",err)}
    if err:=decoder.Decode(new(any));!errors.Is(err,io.EOF) {return Receipt{},errors.New("extra JSON after source")}
    return validate(g,in),nil
}
func main(){
    if len(os.Args)!=2 {fmt.Fprintln(os.Stderr,"usage: groomcheck <source.groom.json>");os.Exit(2)}
    b,err:=os.ReadFile(os.Args[1])
    if err!=nil||len(b)>10*1024*1024 {fmt.Fprintln(os.Stderr,"source missing or oversized");os.Exit(2)}
    receipt,err:=run(b)
    if err!=nil {fmt.Fprintln(os.Stderr,err);os.Exit(2)}
    encoded,err:=json.MarshalIndent(receipt,"","  ")
    if err!=nil {fmt.Fprintln(os.Stderr,err);os.Exit(2)}
    fmt.Println(string(encoded))
    if receipt.Verdict!="PASS_SOURCE_SCHEMA_ONLY"{os.Exit(1)}
}
