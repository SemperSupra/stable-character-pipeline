package r015gate

// Byte binding is NOT trusted measurements, calibrated anatomy, source-rights
// verification or permission to canonicalize a CharacterPack. It narrows the
// known prototype false-positive surface (empty/forged measurement provenance).

import (
 "bytes"
 "crypto/sha256"
 "encoding/hex"
 "encoding/json"
 "errors"
 "fmt"
 "math"
 "os"
 "io"
 "strings"
)

type BoundProof struct {
 GeometryPath string
 GeometrySHA256 string
 MeasurementReceiptPath string
 MeasurementReceiptSHA256 string
}

type MeasurementReceipt struct {
 Schema string `json:"schema"`
 GeometrySHA256 string `json:"geometry_sha256"`
 Measurements []Measurement `json:"measurements"`
 ClaimedScaleMethod string `json:"claimed_scale_method"`
 ClaimedIssuer string `json:"claimed_issuer"`
}

func validDigest(s string) bool {
 if len(s)!=64 {return false}
 b,e:=hex.DecodeString(s)
 return e==nil && len(b)==32 && strings.ToLower(s)==s
}
func readBound(path string, expected string, maxBytes int64)([]byte,error){
 if !validDigest(expected) {return nil,errors.New("SHA256 format requires full lowercase 64 hex")}
 if path=="" {return nil,errors.New("missing evidence path")}
 info,e:=os.Stat(path)
 if e!=nil {return nil,fmt.Errorf("evidence unavailable: %w",e)}
 if !info.Mode().IsRegular()||info.Size()<1||info.Size()>maxBytes{return nil,errors.New("evidence not regular bounded file")}
 data,e:=os.ReadFile(path);if e!=nil{return nil,e}
 sum:=sha256.Sum256(data)
 if hex.EncodeToString(sum[:])!=expected{return nil,errors.New("actual evidence bytes failed SHA256 binding")}
 return data,nil
}

func equalMeasures(a,b Measurement)bool {
 return a.Name==b.Name && a.Unit==b.Unit &&
  a.Method==b.Method && a.SourceSHA==b.SourceSHA &&
  a.LandmarkProvenance==b.LandmarkProvenance &&
  !math.IsNaN(a.Value) && !math.IsNaN(b.Value) && a.Value==b.Value
}

// CheckBound fails if a read-back of actual evidence files contradicts
// caller-asserted source and claim bytes; otherwise it ALWAYS abstains because
// an arbitrary actor can author a self-consistent but FALSE geometry/scale
// record. A SHA or a caller-supplied issuer label cannot prove metric reality.
func CheckBound(e Evidence, proof BoundProof) Result {
 base:=Check(e)
 if base.Status==Reject {return base}
 reject:=func(code string) Result {
  return Result{Status:Reject,Reasons:[]string{code}}
 }
 if !validDigest(proof.GeometrySHA256)||
    !validDigest(proof.MeasurementReceiptSHA256) {
  return reject("invalid_provenance_sha256_format")
 }
 geom,err:=readBound(proof.GeometryPath,proof.GeometrySHA256,128<<20)
 if err!=nil{return reject("geometry_byte_binding_failed")}
 receiptData,err:=readBound(proof.MeasurementReceiptPath,proof.MeasurementReceiptSHA256,2<<20)
 if err!=nil{return reject("measurement_receipt_byte_binding_failed")}
 if len(geom)==0 {return reject("empty_source_geometry")}
 dec:=json.NewDecoder(bytes.NewReader(receiptData))
 dec.DisallowUnknownFields()
 var receipt MeasurementReceipt
 if err=dec.Decode(&receipt);err!=nil{return reject("invalid_measurement_receipt")}
 var extra interface{}
 if dec.Decode(&extra)!=io.EOF {return reject("extra_untrusted_receipt_payload")}
 if receipt.Schema!="r015.measurement.claims.source_bound.v1" {
  return reject("unknown_measurement_receipt_schema")
 }
 if receipt.GeometrySHA256!=proof.GeometrySHA256{return reject("geometry_receipt_not_bound_to_bytes")}
 if len(receipt.Measurements)!=len(e.Measurements){return reject("measurement_list_length_mismatch")}
 for i,m:=range e.Measurements {
  if !validDigest(m.SourceSHA)||m.SourceSHA!=proof.GeometrySHA256 {
    return reject("claim_geometry_sha256_unbound")
  }
  if !equalMeasures(m,receipt.Measurements[i]) {
    return reject("claim_value_unit_method_or_landmark_mismatch")
  }
 }
 // e.NativeReopened, e.RightsKnown, e.IndependentScaleCalibrated and alleged
 // issuers are bool/string claims. No authentic independent evaluator, metric
 // caliper, raw 3D mesh provenance or trusted signer is integrated here.
 return Result{Status:Unknown,Reasons:append(base.Reasons,
  "byte_binding_verified",
  "caller_asserted_geometry_and_scale_not_independently_authenticated",
  "source_rights_and_anatomical_units_unverified",
  "canonical_or_release_promotion_forbidden")}
}
