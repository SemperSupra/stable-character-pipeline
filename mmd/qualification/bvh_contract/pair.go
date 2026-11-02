package bvh

import (
	"errors"
)

// Pair is an explicitly source-only clock compatibility receipt, not proof of
// paired camera/capture session, performer identity, contact or gait truth.
type Pair struct {
	Schema           string `json:"schema"`
	Status           string `json:"status"`
	ActorAHash       string `json:"actor_a_sha256"`
	ActorBHash       string `json:"actor_b_sha256"`
	FrameTime        string `json:"frame_time_seconds"`
	Frames           int    `json:"frames"`
	ActorAStart      Vec3   `json:"actor_a_root_start_m"`
	ActorBStart      Vec3   `json:"actor_b_root_start_m"`
	ActorAEnd        Vec3   `json:"actor_a_root_end_m"`
	ActorBEnd        Vec3   `json:"actor_b_root_end_m"`
	SourceRights     string `json:"source_rights"`
	NativeIdentity   string `json:"native_identity"`
	SynchronizedTake bool   `json:"synchronized_original_take_verified"`
	Anatomy          string `json:"anatomy"`
	PrivateR009      string `json:"private_R009"`
}

func CheckPair(a, b *Motion) (*Pair, error) {
	if a == nil || b == nil {
		return nil, errors.New("MISSING_PAIR_INPUT")
	}
	if a.Rights != "ORIGINAL_SELF_AUTHORED_SYNTHETIC" || b.Rights != a.Rights {
		return nil, errors.New("UNADMITTED_OR_MISMATCHED_RIGHTS")
	}
	if a.SourceSHA256 == b.SourceSHA256 {
		return nil, errors.New("DUPLICATED_SOURCE_BYTES_NOT_DISTINCT_ACTORS")
	}
	if a.FrameTimeSeconds != b.FrameTimeSeconds {
		return nil, errors.New("UNMATCHED_ORIGIN_CLOCK")
	}
	if len(a.Frames) != len(b.Frames) || len(a.Frames) < 2 {
		return nil, errors.New("UNMATCHED_FRAME_COUNT")
	}
	if !finite(a.MeterPerUnit) || !finite(b.MeterPerUnit) || a.MeterPerUnit <= 0 || a.MeterPerUnit != b.MeterPerUnit {
		return nil, errors.New("UNMATCHED_EXPLICIT_UNIT_SCALE")
	}
	a0, err := a.Evaluate(0)
	if err != nil {
		return nil, err
	}
	b0, err := b.Evaluate(0)
	if err != nil {
		return nil, err
	}
	a1, err := a.Evaluate(len(a.Frames) - 1)
	if err != nil {
		return nil, err
	}
	b1, err := b.Evaluate(len(b.Frames) - 1)
	if err != nil {
		return nil, err
	}
	return &Pair{Schema: "scp.bvh.original-synthetic-paired-source-clock.v1",
		Status:     "CLOCK_COMPATIBLE_ORIGINAL_SYNTHETIC_ONLY_SESSION_SYNC_UNKNOWN",
		ActorAHash: a.SourceSHA256, ActorBHash: b.SourceSHA256,
		FrameTime: a.FrameTimeSeconds, Frames: len(a.Frames),
		ActorAStart: a0[0].PositionMeters, ActorBStart: b0[0].PositionMeters,
		ActorAEnd: a1[0].PositionMeters, ActorBEnd: b1[0].PositionMeters,
		SourceRights: a.Rights, NativeIdentity: "NOT_VERIFIED", SynchronizedTake: false,
		Anatomy: "UNKNOWN_NOT_MEASURED", PrivateR009: "HELD_NOT_ADMITTED"}, nil
}
