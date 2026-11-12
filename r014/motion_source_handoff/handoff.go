// Package handoff is a target-facing admission guard for the R014 MHR human.
// It does not create a competing canonical walk-motion IR or process raw mocap.
// Upstream owners: motion source #349/#29, W07 #84, protected R009 #23.
package handoff

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"math"
	"os"
	"sort"
	"strings"
)

const Schema = "r014.existing_motion_source_handoff.v1"

const (
	CatalogOnly = "CATALOG_ONLY"
	Programmatic = "ORIGINAL_PROGRAMMATIC"
	ExternalCapture = "EXTERNAL_MOCAP"
)

type Source struct {
	ID string `json:"id"`
	Dataset string `json:"dataset"`
	Take string `json:"take"`
	Kind string `json:"kind"`
	PublisherURL string `json:"publisher_url"`
	TermsURL string `json:"terms_url"`
	OriginalSHA256 string `json:"original_sha256"`
	SkeletonSHA256 string `json:"skeleton_sha256"`
	OwnerAdmissionRef string `json:"owner_admission_ref"`
	LicenseClassification string `json:"license_classification"`
	Venue string `json:"venue"`
	SourceFPS float64 `json:"source_fps"`
	SourceFPSObserved bool `json:"source_fps_observed"`
	SourceUnit string `json:"source_unit"`
	SourceUnitObserved bool `json:"source_unit_observed"`
	RawCaptureVerified bool `json:"raw_capture_verified"`
	ObservedJointChannels []string `json:"observed_joint_channels"`
	ObservedContact bool `json:"observed_ground_contact"`
	EstimatedContact bool `json:"estimated_ground_contact"`
	Provenance string `json:"provenance"`
	ParentSchema string `json:"parent_schema"`
	Notes string `json:"notes"`
}

type Packet struct {
	Schema string `json:"schema"`
	UpstreamAuthorities []string `json:"upstream_authorities"`
	R014Target string `json:"r014_target"`
	Sources []Source `json:"sources"`
}

type Disposition struct {
	ID string `json:"id"`
	Status string `json:"status"`
	AllowedRoles []string `json:"allowed_roles"`
	RefusedRoles []string `json:"refused_roles"`
	BlockingReasons []string `json:"blocking_reasons"`
	RequiresPrivateCompute bool `json:"requires_private_compute"`
}

type Receipt struct {
	Schema string `json:"schema"`
	Status string `json:"status"`
	ManifestSHA256 string `json:"manifest_sha256"`
	R014Model string `json:"r014_model"`
	R014ReleaseStatus string `json:"r014_release_status"`
	UpstreamReferences []string `json:"upstream_references"`
	SourceDispositions []Disposition `json:"source_dispositions"`
	Limitations []string `json:"limitations"`
}

var requiredOwners = []string{
	"SemperSupra/stable-character-pipeline/issues/349",
	"SemperSupra/stable-character-pipeline/issues/29",
	"SemperSupra/stable-character-pipeline/issues/84",
	"SemperSupra/stable-character-pipeline-private/issues/23",
	"SemperSupra/stable-character-pipeline-private/issues/138",
}
var measuredRoles = []string{"root", "pelvis", "spine", "left_hip", "right_hip", "left_knee", "right_knee", "left_shoulder", "right_shoulder", "left_elbow", "right_elbow"}
var prohibitedCMURoles = []string{"left_toe", "right_toe", "left_finger", "right_finger", "left_thumb", "right_thumb", "ground_contact_observed"}
var syntheticRoles = []string{"root", "left_ankle_target", "right_ankle_target", "left_contact_estimate", "right_contact_estimate"}

func digest(raw []byte) string { s := sha256.Sum256(raw); return hex.EncodeToString(s[:]) }

func isSHA(s string) bool {
	if len(s) != 64 || strings.ToLower(s) != s { return false }
	_, err := hex.DecodeString(s)
	return err == nil
}

func evaluateOne(x Source) (Disposition, error) {
	d := Disposition{ID:x.ID, Status:"HOLD_SOURCE_RIGHTS_OR_BYTES", RefusedRoles: []string{}, BlockingReasons: []string{}}
	if x.ID == "" || x.Dataset == "" || x.Take == "" || x.PublisherURL == "" || x.TermsURL == "" {
		return d, errors.New("missing source identity, recording, publisher or terms")
	}
	if !strings.HasPrefix(x.PublisherURL,"https://") || !strings.HasPrefix(x.TermsURL,"https://") {
		return d, errors.New("source and terms must be securely recorded")
	}
	if x.Kind != Programmatic && x.Kind != ExternalCapture {
		return d, fmt.Errorf("invalid source classification %s",x.Kind)
	}
	if x.SourceFPS < 0 || math.IsNaN(x.SourceFPS) || math.IsInf(x.SourceFPS,0) {
		return d, errors.New("invalid fps")
	}
	if x.OriginalSHA256 != "" && !isSHA(x.OriginalSHA256) {return d,errors.New("forged original hash")}
	if x.SkeletonSHA256 != "" && !isSHA(x.SkeletonSHA256) {return d,errors.New("forged skeleton hash")}
	if x.Kind==Programmatic {
		if x.Dataset!="SCP_GO_GAIT" || x.ParentSchema!="r014.gaitprobe.169f" || x.Provenance!="PROGRAMMATIC" {
			return d, errors.New("unknown original synthetic motion source lineage")
		}
		if x.LicenseClassification!="SELF_AUTHORED" || x.RawCaptureVerified {
			return d,errors.New("synthetic source misclassified as original capture")
		}
		if x.OriginalSHA256!="44d8ebb4bee9a01f522a92ff4377c4cc66c9b19df835bb4b6a1e2a847179fd56" {
			return d,errors.New("original pinned R014 169-frame Go donor digest mismatch")
		}
		d.AllowedRoles=append([]string{},syntheticRoles...)
		d.Status="PASS_ORIGINAL_PROCEDURAL_LINEAGE_ONLY"
		d.BlockingReasons=append(d.BlockingReasons,"NOT_MEASURED_HUMAN_MOTION_OR_NATURAL_HEEL_TOE")
		return d,nil
	}
	if x.Dataset!="CMU_MOCAP" && x.Dataset!="AIST_PLUS_PLUS" && x.Dataset!="DANCEDB" && x.Dataset!="OTHER_EXTERNAL" {
		return d,errors.New("unknown external dataset type")
	}
	if x.Dataset=="CMU_MOCAP" {
		if x.ObservedContact {
			return d,errors.New("CMU toe ground contact cannot be claimed directly observed")
		}
		for _,role := range x.ObservedJointChannels {
			for _,bad := range prohibitedCMURoles {
				if role==bad {return d,fmt.Errorf("CMU source channel %s cannot be accepted as measured reliable motion",role)}
			}
		}
		d.RefusedRoles=append(d.RefusedRoles,prohibitedCMURoles...)
		// Do not grant measured roles based on dataset landing-page or description.
		if x.Take=="07_01" && x.ParentSchema=="scp.walk_motion.v1" {
			return d,errors.New("W07 existing v1 is 2D 72f synthetic; it is not a native 3D ASF/AMC carrier")
		}
	}
	if x.ParentSchema=="scp.walk_motion.v1" {
		return d,errors.New("source-neutral W07 v1 cannot be silently promoted to general 3D source IR")
	}
	if x.Venue=="public_github_actions" && x.OwnerAdmissionRef=="" {
		return d,errors.New("external capture cannot be placed on public Actions by manifest alone")
	}
	if x.LicenseClassification==CatalogOnly || !x.RawCaptureVerified || !isSHA(x.OriginalSHA256) || !isSHA(x.SkeletonSHA256) {
		d.Status="HOLD_CATALOG_OR_UNVERIFIED_CAPTURE"
		d.BlockingReasons=append(d.BlockingReasons, "EXACT_SOURCE_FILE_HASH_AND_RIGHTS_ADMISSION_REQUIRED")
		if x.OwnerAdmissionRef=="" {d.BlockingReasons=append(d.BlockingReasons,"R012_R009_OWNER_ADMISSION_REQUIRED")}
		d.RequiresPrivateCompute=true
		return d,nil
	}
	if x.OwnerAdmissionRef=="" || x.Venue!="private_offline" || !x.SourceFPSObserved || !x.SourceUnitObserved {
		d.Status="HOLD_OWNER_VENUE_CLOCK_OR_UNIT_PROOF"
		d.RequiresPrivateCompute=true
		d.BlockingReasons=append(d.BlockingReasons,"SOURCE_ADMISSION_IS_A_CLAIM_NOT_CRYPTOGRAPHIC_GRANT")
		return d,nil
	}
	// Still only a source metadata candidate: actual extracted FK, contact and
	// 3D MHR retargeting have not run, and owner approval cannot be forged by JSON.
	d.Status="READY_FOR_INDEPENDENT_PRIVATE_SOURCE_REVIEW_ONLY"
	d.RequiresPrivateCompute=true
	d.AllowedRoles=append([]string{},measuredRoles...)
	d.BlockingReasons=append(d.BlockingReasons,"NO_ACTUAL_MHR_MOTION_RETARGET_OR_VERIFIED_MEASURED_JOINTS")
	return d,nil
}

// Evaluate validates a source-identity packet without ever admitting any third-party
// human motion files to public Git, GHA or a released product.
func Evaluate(p Packet, sourceBytes []byte) (Receipt,error) {
	r:=Receipt{Schema:Schema,Status:"HOLD_CINEMATIC_AND_ACTUAL_MOTION_SOURCE_ADMISSION",
		ManifestSHA256:digest(sourceBytes), R014Model:"MHR_v1.0.1_NATIVE_18439v_126_bones",
		R014ReleaseStatus:"HOLD",UpstreamReferences:requiredOwners,
		Limitations:[]string{
			"NO_EXTERNAL_RAW_CAPTURE_ACQUIRED_OR_RETARGETED_BY_THIS_WORKCELL",
			"CMU_HAS_NO_RELIABLE_RECORDED_TOE_FINGER_THUMB_SOURCE; FOOT_CONTACT_SEPARATE",
			"W07_SCP_WALK_MOTION_V1_IS_2D_72F_SYNTHETIC_NOT_3D",
			"NO_ANATOMICAL_ROM_SOFT_TISSUE_FACE_HANDS_OR_CINEMATIC_QUALITY",
			"ADMISSION_REF_IN_UNTRUSTED_JSON_IS_NOT_OWNER_AUTHORIZATION"}}
	if p.Schema!=Schema || p.R014Target!="MHR_v1.0.1_NATIVE_18439v_126_bones" || len(p.Sources)<2 {
		return r,errors.New("source packet or MHR target mismatch")
	}
	o:=map[string]bool{}
	for _,ref:=range p.UpstreamAuthorities{o[ref]=true}
	for _,ref:=range requiredOwners{if !o[ref] {return r,errors.New("missing existing DLE owner "+ref)}}
	ids:=map[string]bool{}
	for _,s:=range p.Sources {
		if ids[s.ID] {return r,errors.New("duplicate capture identity")}
		ids[s.ID]=true
		d,err:=evaluateOne(s);if err!=nil{return r,fmt.Errorf("%s: %w",s.ID,err)}
		r.SourceDispositions=append(r.SourceDispositions,d)
	}
	sort.Slice(r.SourceDispositions,func(i,j int)bool{return r.SourceDispositions[i].ID<r.SourceDispositions[j].ID})
	return r,nil
}

func ReadPacket(path string)(Packet,[]byte,error) {
	var p Packet
	raw,e:=os.ReadFile(path);if e!=nil{return p,nil,e}
	dec:=json.NewDecoder(strings.NewReader(string(raw)));dec.DisallowUnknownFields()
	if e=dec.Decode(&p);e!=nil{return p,nil,e}
	return p,raw,nil
}
