package main

// Contact exchange v1 is a source-only, SI, fail-closed transport contract.
// BVH overlap/proximity never implies signed penetration, force, or biological truth.
import ("math";"sort";"strings")
const exchangeSchema="equine.contact_surface_exchange.v1"
type PatchState struct {
 ID string `json:"id"`
 Wet float64 `json:"wet_fraction"`
 Deposit float64 `json:"deposited_kg_m2"`
 Residue float64 `json:"residue_kg_m2"`
 TempK float64 `json:"temperature_k"`
}
type ContactObservation struct {
 ID string `json:"id"`
 PatchID string `json:"patch_id"`
 OtherID string `json:"other_id"`
 Evidence string `json:"evidence"` // triangle_overlap / tip_proximity / unknown
 PointM [3]float64 `json:"point_m"`
 DistanceM float64 `json:"unsigned_distance_m"`
 Observed bool `json:"observed"`
}
type SurfacePacket struct {
 Schema string `json:"schema"`
 Source string `json:"source"`
 Entity string `json:"entity"`
 MeshSHA256 string `json:"mesh_sha256"`
 Solver string `json:"solver"`
 Units string `json:"units"`
 Frame string `json:"frame"`
 RateHz int `json:"rate_hz"`
 Tick int64 `json:"tick"`
 Patches []PatchState `json:"patches"`
 Contacts []ContactObservation `json:"contacts"`
 ScienceHold bool `json:"science_hold"`
 Release bool `json:"release"`
}
type SurfaceDelta struct {
 PatchID string `json:"patch_id"`
 Reason string `json:"reason"`
 Wet float64 `json:"wet_delta"`
 Deposit float64 `json:"deposited_delta_kg_m2"`
 Residue float64 `json:"residue_delta_kg_m2"`
 TempK float64 `json:"temperature_delta_k"`
}
type SurfaceVerdict struct {
 Schema string `json:"schema"`
 Verdict string `json:"verdict"`
 Preserved int `json:"preserved"`
 Changes int `json:"changes"`
 Errors []string `json:"errors"`
 ScienceHold bool `json:"science_hold"`
 Release bool `json:"release"`
}
func xfinite(v float64)bool{return !math.IsNaN(v)&&!math.IsInf(v,0)}
func xrange(v,lo,hi float64)bool{return xfinite(v)&&v>=lo&&v<=hi}
func xid(s string)bool{return len(s)>=2&&len(s)<=128&&strings.TrimSpace(s)==s&&!strings.ContainsAny(s,"\r\t\n")}
func xsha(s string)bool{
 if len(s)!=64{return false}
 for _,c:=range s{if !strings.ContainsRune("0123456789abcdef",c){return false}}
 return true
}
func inspectSurface(p SurfacePacket)[]string{
 errs:=[]string{};bad:=func(s string){errs=append(errs,s)}
 if p.Schema!=exchangeSchema||p.Source!="original_synthetic"{bad("schema_or_rights_class")}
 if !xid(p.Entity)||!xid(p.Solver)||!xsha(p.MeshSHA256){bad("source_identity")}
 if p.Units!="SI"||p.Frame!="world_Z_up"||p.RateHz!=120||p.Tick<0||p.Tick>120*86400{bad("clock_or_frame")}
 if !p.ScienceHold||p.Release{bad("unsafe_promotion")}
 if len(p.Patches)<1||len(p.Patches)>20000||len(p.Contacts)>100000{bad("size_bounds");return errs}
 known:=map[string]bool{}
 for _,s:=range p.Patches{
  if !xid(s.ID)||known[s.ID]{bad("duplicate_or_invalid_patch")}
  known[s.ID]=true
  if !xrange(s.Wet,0,1)||!xrange(s.Deposit,0,10000)||!xrange(s.Residue,0,10000)||!xrange(s.TempK,0,10000){bad("invalid_surface_state")}
 }
 ids:=map[string]bool{}
 for _,c:=range p.Contacts{
  if !xid(c.ID)||ids[c.ID]||!known[c.PatchID]||!xid(c.OtherID){bad("invalid_contact_reference")}
  ids[c.ID]=true
  if !map[string]bool{"triangle_overlap":true,"tip_proximity":true,"unknown":true}[c.Evidence]{bad("unsupported_contact_evidence")}
  if c.Observed==(c.Evidence=="unknown"){bad("observed_status_mismatch")}
  if !xrange(c.DistanceM,0,1000){bad("negative_or_nonfinite_unsigned_distance")}
  for _,v:=range c.PointM{if !xrange(v,-10000,10000){bad("invalid_contact_coordinate");break}}
  if c.Evidence=="triangle_overlap"&&c.DistanceM>1e-6{bad("overlap_distance_contradiction")}
 }
 sort.Strings(errs);return errs
}
func exchangeSurface(before,after SurfacePacket,changes []SurfaceDelta)SurfaceVerdict{
 r:=SurfaceVerdict{Schema:exchangeSchema+".verdict",Verdict:"REJECT_EXCHANGE",Errors:[]string{},ScienceHold:true,Release:false}
 bad:=func(s string){r.Errors=append(r.Errors,s)}
 for _,e:=range inspectSurface(before){bad("before:"+e)}
 for _,e:=range inspectSurface(after){bad("after:"+e)}
 if len(r.Errors)>0{sort.Strings(r.Errors);return r}
 if before.Entity!=after.Entity||before.MeshSHA256!=after.MeshSHA256||before.Source!=after.Source||before.Units!=after.Units||before.Frame!=after.Frame||before.RateHz!=after.RateHz{bad("identity_or_frame_changed")}
 if after.Tick<=before.Tick||after.Tick-before.Tick>120*600{bad("stale_or_nonmonotonic")}
 if len(changes)>len(before.Patches){bad("oversized_deltas");return r}
 current:=map[string]PatchState{};for _,p:=range after.Patches{current[p.ID]=p}
 received:=map[string]SurfaceDelta{}
 for _,d:=range changes{
  if !xid(d.PatchID)||!map[string]bool{"external_input":true,"experimental_solver":true}[d.Reason]{bad("bad_delta_source")}
  if _,ok:=received[d.PatchID];ok{bad("duplicate_delta")}
  for _,v:=range []float64{d.Wet,d.Deposit,d.Residue,d.TempK}{if !xfinite(v)||math.Abs(v)>10000{bad("bad_delta_value")}}
  received[d.PatchID]=d
 }
 if len(before.Patches)!=len(after.Patches){bad("patch_count_changed")}
 for _,p:=range before.Patches{
  n,ok:=current[p.ID];if !ok{bad("missing_patch:"+p.ID);continue}
  r.Preserved++
  diff:=[4]float64{n.Wet-p.Wet,n.Deposit-p.Deposit,n.Residue-p.Residue,n.TempK-p.TempK}
  d,has:=received[p.ID];declared:=[4]float64{d.Wet,d.Deposit,d.Residue,d.TempK}
  modified:=false
  for i:=range diff{
   if math.Abs(diff[i])>1e-9{modified=true}
   if has&&math.Abs(diff[i]-declared[i])>1e-9{bad("delta_mismatch:"+p.ID);break}
  }
  if modified&&!has{bad("silent_state_change:"+p.ID)}
  if !modified&&has{bad("redundant_delta:"+p.ID)}
  if modified&&has{r.Changes++}
 }
 for id:=range received{if _,ok:=current[id];!ok{bad("orphan_delta:"+id)}}
 sort.Strings(r.Errors)
 if len(r.Errors)==0{r.Verdict="PASS_EXPLICIT_TRANSFER_ONLY"}
 return r
}
