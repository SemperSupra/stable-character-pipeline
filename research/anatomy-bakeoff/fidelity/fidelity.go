// Package fidelity qualifies *evidence contracts*, not medical accuracy or
// photorealism. No model assets or human/physics engines are imported.
package fidelity

import (
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "regexp"
 "sort"
)

const Schema = "scp.anatomy.fidelity.v1"
type Tier string
const (
 L0 Tier = "L0_SELECTABLE_GEOMETRY"
 L1 Tier = "L1_ANIMATED_RENDER_ASSET"
 L2 Tier = "L2_PHYSICAL_SIMULATION"
)
var shaPattern=regexp.MustCompile(`^[0-9a-f]{64}$`)
var validView=map[string]bool{"ISA":true,"PART_OF":true,"HRA_REFERENCE":true,"NATIVE":true}
var validOntology=map[string]bool{"FMA":true,"UBERON":true,"LOCAL":true}
type Representation struct {
 Source string `json:"source"`
 Version string `json:"version"`
 View string `json:"view"`
 Ontology string `json:"ontology"`
 ConceptID string `json:"concept_id"`
 GeometryID string `json:"geometry_id"`
 AssetSHA256 string `json:"asset_sha256"`
 Rights string `json:"rights"`
 Frame string `json:"coordinate_frame"`
 GeometryVertices uint64 `json:"geometry_vertices"`
 SourceImportObserved bool `json:"source_import_observed"`
}
type RigEvidence struct {
 NativeRig string `json:"native_rig"`
 RigRevision string `json:"rig_revision"`
 AttachmentID string `json:"attachment_id"`
 PoseReceiptSHA256 string `json:"pose_receipt_sha256"`
 RefitReceiptSHA256 string `json:"refit_receipt_sha256"`
}
type ProductionEvidence struct {
 VisualReviewReceiptSHA256 string `json:"visual_review_receipt_sha256"`
 SavedSceneReceiptSHA256 string `json:"saved_scene_receipt_sha256"`
 InterchangeReceiptSHA256 string `json:"interchange_receipt_sha256"`
}
type SolverEvidence struct {
 Solver string `json:"solver"`
 Version string `json:"version"`
 MaterialModel string `json:"material_model"`
 CollisionReceiptSHA256 string `json:"collision_receipt_sha256"`
 SignedJacobianReceiptSHA256 string `json:"signed_jacobian_receipt_sha256"`
 TemporalReceiptSHA256 string `json:"temporal_receipt_sha256"`
}
type Feature struct {
 Schema string `json:"schema"`
 ID string `json:"id"`
 CanonicalOntology string `json:"canonical_ontology"`
 CanonicalConceptID string `json:"canonical_concept_id"`
 Representations []Representation `json:"representations"`
 Rig RigEvidence `json:"rig"`
 Render ProductionEvidence `json:"render"`
 Solver SolverEvidence `json:"solver"`
 Visible bool `json:"visible"`
 PhysicsActive bool `json:"physics_active"`
 CollisionActive bool `json:"collision_active"`
}
type Verdict struct {
 Schema string `json:"schema"`
 FeatureID string `json:"feature_id"`
 Target Tier `json:"target"`
 Status string `json:"status"`
 Missing []string `json:"missing"`
 GeometrySources []string `json:"geometry_sources"`
 Caveat string `json:"caveat"`
}
func validHash(s string)bool{return shaPattern.MatchString(s)}
func accepted(t Tier)bool{return t==L0||t==L1||t==L2}
func validateConcept(n,id string)bool{
 if id==""{return false}
 if n=="FMA"{return regexp.MustCompile(`^FMA[0-9]+$`).MatchString(id)}
 if n=="UBERON"{return regexp.MustCompile(`^UBERON:[0-9]+$`).MatchString(id)}
 if n=="LOCAL"{return len(id)>3}
 return false
}
func Validate(f Feature)error{
 if f.Schema!=Schema||f.ID==""{return errors.New("INVALID_SCHEMA_OR_ID")}
 if !validateConcept(f.CanonicalOntology,f.CanonicalConceptID){return errors.New("INVALID_CANONICAL_CONCEPT")}
 bySource:=map[string]bool{}
 for _,r:=range f.Representations{
  if r.Source==""||r.Version==""||r.Frame==""||r.GeometryID==""||!validView[r.View]||
   !validOntology[r.Ontology]||!validateConcept(r.Ontology,r.ConceptID){
   return errors.New("INVALID_SOURCE_REPRESENTATION")
  }
  if r.AssetSHA256!=""&&!validHash(r.AssetSHA256){return errors.New("INVALID_ASSET_HASH")}
  if r.Rights!="ADMITTED"&&r.Rights!="UNKNOWN"&&r.Rights!="DENIED"&&r.Rights!="NOT_REVIEWED"{
   return errors.New("INVALID_RIGHTS_STATE")
  }
  key:=fmt.Sprintf("%s/%s/%s/%s",r.Source,r.Version,r.View,r.GeometryID)
  if bySource[key]{return errors.New("DUPLICATE_GEOMETRY_IN_SAME_SOURCE_VIEW")}
  bySource[key]=true
 }
 return nil
}
func digest(v any) string{
 b,_:=json.Marshal(v)
 h:=sha256.Sum256(b)
 return hex.EncodeToString(h[:])
}
func Evaluate(f Feature,t Tier)(Verdict,error){
 v:=Verdict{Schema:Schema,FeatureID:f.ID,Target:t,
  Status:"HOLD_MISSING_OR_UNVERIFIED_EVIDENCE",
  Missing:[]string{},GeometrySources:[]string{},
  Caveat:"Source/structure/rig evidence contract only; never implies medical truth or photoreal image quality."}
 if !accepted(t){return v,errors.New("UNSUPPORTED_FIDELITY_TIER")}
 if err:=Validate(f);err!=nil{return v,err}
 add:=func(reason string){v.Missing=append(v.Missing,reason)}
 hasGeometry:=false
 for _,r:=range f.Representations{
  if r.Rights=="ADMITTED"&&r.SourceImportObserved&&r.GeometryVertices>0&&validHash(r.AssetSHA256){
   hasGeometry=true
   v.GeometrySources=append(v.GeometrySources,r.Source+"@"+r.Version+"/"+r.View+":"+r.GeometryID)
  }
 }
 sort.Strings(v.GeometrySources)
 if !hasGeometry{add("L0_VERIFIED_IMPORTED_GEOMETRY_WITH_SOURCE_SHA_AND_RIGHTS")}
 if t==L1||t==L2{
  if f.Rig.NativeRig==""||f.Rig.RigRevision==""||f.Rig.AttachmentID==""{
   add("L1_NATIVE_RIG_AND_ATTACHMENT")
  }
  if !validHash(f.Rig.PoseReceiptSHA256)||!validHash(f.Rig.RefitReceiptSHA256){
   add("L1_POSE_AND_REFIT_EVIDENCE")
  }
  if !validHash(f.Render.VisualReviewReceiptSHA256)||
    !validHash(f.Render.SavedSceneReceiptSHA256)||
    !validHash(f.Render.InterchangeReceiptSHA256){
   add("L1_VISUAL_NATIVE_AND_TARGET_INTERCHANGE_EVIDENCE")
  }
 }
 if t==L2{
  if f.Solver.Solver==""||f.Solver.Version==""||f.Solver.MaterialModel==""{
   add("L2_MATERIAL_AND_SOLVER_SPECIFICATION")
  }
  if !validHash(f.Solver.CollisionReceiptSHA256)||
   !validHash(f.Solver.SignedJacobianReceiptSHA256)||
   !validHash(f.Solver.TemporalReceiptSHA256){
   add("L2_CONTACT_SIGNED_VOLUME_AND_TIMEBASE_EVIDENCE")
  }
 }
 if len(v.Missing)==0{v.Status="EVIDENCE_CONTRACT_COMPLETE_REVIEW_REQUIRED"}
 return v,nil
}
// Crosswalk types are an explicit, manual / reviewed proposition. Matching
// English words cannot silently certify UBERON-to-FMA equivalence.
type Crosswalk struct {
 FromOntology string `json:"from_ontology"`
 FromID string `json:"from_id"`
 ToOntology string `json:"to_ontology"`
 ToID string `json:"to_id"`
 ReviewStatus string `json:"review_status"`
 EvidenceSHA256 string `json:"evidence_sha256"`
}
func CrosswalkEligible(x Crosswalk)bool{
 return x.FromOntology!=x.ToOntology&&
  validateConcept(x.FromOntology,x.FromID)&&validateConcept(x.ToOntology,x.ToID)&&
  x.ReviewStatus=="REVIEWED"&&validHash(x.EvidenceSHA256)
}
func PhysicsStateDigest(f Feature)string{
 // View is excluded. This is a structural digest, NOT a simulation result.
 return digest(struct{
  ID string
  Rig RigEvidence
  Solver SolverEvidence
  PhysicsActive bool
  CollisionActive bool
 }{f.ID,f.Rig,f.Solver,f.PhysicsActive,f.CollisionActive})
}
