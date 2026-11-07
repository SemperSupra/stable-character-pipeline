package main

// NativeGateReview is a read-only static coverage witness, not an execution oracle.
// It deliberately refuses to infer safety from green CI, a path-only diff or
// assertion text outside an active (indented) python3 heredoc run step.
import (
	"crypto/sha256"
	"encoding/hex"
	"regexp"
	"strconv"
	"strings"
	"testing"
)

const nativeGateSchema = "scp.r009.native_gate_static_review.v1"

var (
	rgSchema  = regexp.MustCompile(`^assert\s+bvh\["schema"\]\s*==\s*"scp\.r009\.original_bvh_surface_contact\.v([0-9]+)"\s*$`)
	rgFrames  = regexp.MustCompile(`^assert\s+bvh\["motion_frames_evaluated"\]\s*==\s*([0-9]+)\s*$`)
	rgIndices = regexp.MustCompile(`^assert\s+bvh\["frame_indices"\]\s*==\s*list\(range\(0,143,([0-9]+)\)\)\s*$`)
	rgFull    = regexp.MustCompile(`^assert\s+bvh\["all_72_motion_frames_evaluated"\]\s*$`)
	rgNotFull = regexp.MustCompile(`^assert\s+not\s+bvh\["all_72_motion_frames_evaluated"\]\s*$`)
)

type nativeGateWitness struct {
	Schema                     string `json:"schema"`
	SourceSHA256               string `json:"source_sha256"`
	BVHSchemaVersion           int    `json:"bvh_schema_version"`
	FramesAsserted             int    `json:"frames_asserted"`
	FrameStepAsserted          int    `json:"frame_step_asserted"`
	Full72Asserted             bool   `json:"full_72_asserted"`
	StaticClass                string `json:"static_class"`
	RuntimeExecuted            bool   `json:"runtime_executed"`
	NativeScientificAcceptance bool   `json:"native_scientific_acceptance"`
}

// reviewNativeGateV1 examines only literal assert signatures in a
// python3 - <<'PY' heredoc within a YAML `run: |` block. It is intentionally
// narrow and abstains on ambiguous/conflicting assertions or unparsed code.
func reviewNativeGateV1(input string) nativeGateWitness {
	sum := sha256.Sum256([]byte(input))
	r := nativeGateWitness{Schema: nativeGateSchema, SourceSHA256: hex.EncodeToString(sum[:]), StaticClass: "UNKNOWN_HELD"}
	if len(input) == 0 || len(input) > 1<<20 || strings.ContainsRune(input, 0) {
		return r
	}
	inRun, inPy := false, false
	runIndent := -1
	seen := 0
	contradicted := false
	inTriple := false
	foundSchema, foundFrames, foundIndices := false, false, false
	fullNeg := false
	for _, raw := range strings.Split(strings.ReplaceAll(input, "\r\n", "\n"), "\n") {
		trimmed := strings.TrimSpace(raw)
		indent := len(raw) - len(strings.TrimLeft(raw, " "))
		if strings.Contains(raw, "\t") {
			contradicted = true
			continue
		}
		if !inRun {
			if trimmed == "run: |" || trimmed == "run: |-" {
				inRun = true
				runIndent = indent
			}
			continue
		}
		if trimmed != "" && indent <= runIndent {
			inRun = false
			inPy = false
			inTriple = false
			if trimmed == "run: |" || trimmed == "run: |-" {
				inRun = true
				runIndent = indent
			}
			continue
		}
		if !inPy {
			if trimmed == "python3 - <<'PY'" {
				inPy = true
				inTriple = false
				seen++
			}
			continue
		}
		if trimmed == "PY" {
			inPy = false
			inTriple = false
			continue
		}
		// We do not treat assertions in triple-quoted documentation as executable.
		if strings.Count(trimmed, `"""`)%2 == 1 || strings.Count(trimmed, `'''`)%2 == 1 {
			inTriple = !inTriple
			continue
		}
		if inTriple || strings.HasPrefix(trimmed, "#") {
			continue
		}
		// A shell/Python workflow can contain many harmless conditionals; only
		// signatures in the named heredoc qualify as static REVIEW evidence.
		// This lexical scanner cannot prove Python control-flow execution; it
		// never supplies a merge approval or a native-execution verdict.
		if m := rgSchema.FindStringSubmatch(trimmed); m != nil {
			v, _ := strconv.Atoi(m[1])
			if foundSchema && v != r.BVHSchemaVersion {
				contradicted = true
			}
			r.BVHSchemaVersion = v
			foundSchema = true
		}
		if m := rgFrames.FindStringSubmatch(trimmed); m != nil {
			v, _ := strconv.Atoi(m[1])
			if foundFrames && v != r.FramesAsserted {
				contradicted = true
			}
			r.FramesAsserted = v
			foundFrames = true
		}
		if m := rgIndices.FindStringSubmatch(trimmed); m != nil {
			v, _ := strconv.Atoi(m[1])
			if foundIndices && v != r.FrameStepAsserted {
				contradicted = true
			}
			r.FrameStepAsserted = v
			foundIndices = true
		}
		if rgFull.MatchString(trimmed) {
			r.Full72Asserted = true
		}
		if rgNotFull.MatchString(trimmed) {
			fullNeg = true
		}
	}
	if seen == 0 || inPy || inTriple || contradicted || (r.Full72Asserted && fullNeg) || !foundSchema || !foundFrames || !foundIndices {
		return r
	}
	if r.BVHSchemaVersion == 2 && r.FramesAsserted == 72 && r.FrameStepAsserted == 2 && r.Full72Asserted {
		r.StaticClass = "DECLARED_72F_V2_REVIEW_ONLY"
	} else if r.BVHSchemaVersion == 1 && r.FramesAsserted == 12 && r.FrameStepAsserted == 12 && !r.Full72Asserted && fullNeg {
		r.StaticClass = "DECLARED_12F_V1_REVIEW_ONLY"
	}
	return r
}

type nativeGatePairReview struct {
	Schema        string            `json:"schema"`
	Parent        nativeGateWitness `json:"parent"`
	Child         nativeGateWitness `json:"child"`
	Disposition   string            `json:"disposition"`
	Mutations     int               `json:"mutations"`
	MergeApproved bool              `json:"merge_approved"`
}

func compareNativeGatesV1(parent, child string) nativeGatePairReview {
	p, c := reviewNativeGateV1(parent), reviewNativeGateV1(child)
	out := nativeGatePairReview{Schema: nativeGateSchema + ".pair", Parent: p, Child: c,
		Disposition: "UNKNOWN_HELD", Mutations: 0, MergeApproved: false}
	if p.StaticClass == "DECLARED_72F_V2_REVIEW_ONLY" && c.StaticClass == "DECLARED_12F_V1_REVIEW_ONLY" {
		out.Disposition = "STATIC_COVERAGE_REGRESSION_HELD"
	} else if p.StaticClass == "DECLARED_72F_V2_REVIEW_ONLY" && c.StaticClass == "DECLARED_72F_V2_REVIEW_ONLY" {
		out.Disposition = "STATIC_PARITY_REVIEW_ONLY"
	}
	return out
}

// Test fixtures derived from explicit, versioned parent/child coverage semantics.
const parent72Workflow = `name: original
jobs:
  native:
    steps:
      - name: native validator
        run: |
          python3 - <<'PY'
          assert bvh["schema"]=="scp.r009.original_bvh_surface_contact.v2"
          assert bvh["motion_frames_evaluated"]==72
          assert bvh["frame_indices"]==list(range(0,143,2))
          assert bvh["all_72_motion_frames_evaluated"]
          PY
`
const child12Workflow = `name: original
jobs:
  native:
    steps:
      - name: native validator
        run: |
          python3 - <<'PY'
          assert bvh["schema"]=="scp.r009.original_bvh_surface_contact.v1"
          assert bvh["motion_frames_evaluated"]==12
          assert bvh["frame_indices"]==list(range(0,143,12))
          assert not bvh["all_72_motion_frames_evaluated"]
          PY
`

func TestNativeGateParent72AndChild12Regression(t *testing.T) {
	got := compareNativeGatesV1(parent72Workflow, child12Workflow)
	if got.Disposition != "STATIC_COVERAGE_REGRESSION_HELD" || got.Mutations != 0 || got.MergeApproved || got.Parent.RuntimeExecuted || got.Child.NativeScientificAcceptance {
		t.Fatalf("unsafe verdict %+v", got)
	}
	if got.Parent.FramesAsserted != 72 || got.Child.FramesAsserted != 12 {
		t.Fatal("frame assertions lost")
	}
}
func TestNativeGateStaticParityStillNoMerge(t *testing.T) {
	got := compareNativeGatesV1(parent72Workflow, parent72Workflow)
	if got.Disposition != "STATIC_PARITY_REVIEW_ONLY" || got.MergeApproved {
		t.Fatalf("parity promoted %+v", got)
	}
}
func TestNativeGateCommentAndNoRunAreNotProof(t *testing.T) {
	xs := []string{
		`# ` + strings.ReplaceAll(parent72Workflow, "\n", "\n# "),
		`name: decoy\n# assert bvh["motion_frames_evaluated"]==72`,
		`run: |\n  # python3 - <<'PY'\n  # assert bvh["motion_frames_evaluated"]==72`,
		strings.Replace(parent72Workflow, "assert bvh[\"schema\"]", "# assert bvh[\"schema\"]", 1),
		strings.Replace(parent72Workflow, "assert bvh[\"all_72_motion_frames_evaluated\"]", "# assert bvh[\"all_72_motion_frames_evaluated\"]", 1),
		strings.Replace(parent72Workflow, "assert bvh[\"frame_indices\"]", "# assert bvh[\"frame_indices\"]", 1),
	}
	for i, x := range xs {
		if w := reviewNativeGateV1(x); w.StaticClass != "UNKNOWN_HELD" {
			t.Fatalf("decoy %d false pass %+v", i, w)
		}
	}
}
func TestNativeGateConflictingAssertionsFailClosed(t *testing.T) {
	x := strings.Replace(parent72Workflow, "          PY\n", "          assert bvh[\"motion_frames_evaluated\"]==12\n          PY\n", 1)
	if got := reviewNativeGateV1(x).StaticClass; got != "UNKNOWN_HELD" {
		t.Fatalf("contradiction accepted: %s", got)
	}
}
func TestNativeGateTruncatedAndMalformedFailClosed(t *testing.T) {
	for _, x := range []string{"", "run: |\n  python3 - <<'PY'\n  assert bvh[\"schema\"]==\"scp.r009.original_bvh_surface_contact.v2\"", strings.Repeat("X", 1<<20+1), parent72Workflow + "\x00"} {
		if w := reviewNativeGateV1(x); w.StaticClass != "UNKNOWN_HELD" {
			t.Fatalf("malformed proof accepted %+v", w)
		}
	}
}
func TestNativeGateRejectsDowngradeAndUnknown(t *testing.T) {
	x := strings.Replace(parent72Workflow, "==72", "==71", 1)
	if got := compareNativeGatesV1(parent72Workflow, x); got.Disposition != "UNKNOWN_HELD" {
		t.Fatalf("unknown downgraded promoted %+v", got)
	}
}
func TestNativeGateStableDigest(t *testing.T) {
	a, b := reviewNativeGateV1(parent72Workflow), reviewNativeGateV1(parent72Workflow)
	if a.SourceSHA256 != b.SourceSHA256 || len(a.SourceSHA256) != 64 {
		t.Fatal("unstable source digest")
	}
}
