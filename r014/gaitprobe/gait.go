package main

import (
	"math"
)

// Analytic two-segment leg foot-contact research controller.
// This creates WORLD-space target trajectories; it does not retarget a Blender rig.
const (
	FPS           = 24
	Seconds       = 7.0
	StepSecs      = 0.34
	StepEverySecs = 0.44
	HipHeight     = 0.87
	UpperLeg      = 0.55
	LowerLeg      = 0.55
)

type Vec3 struct {
	X float64 `json:"x"`
	Y float64 `json:"y"`
	Z float64 `json:"z"`
}

func (a Vec3) Add(b Vec3) Vec3      { return Vec3{a.X + b.X, a.Y + b.Y, a.Z + b.Z} }
func (a Vec3) Sub(b Vec3) Vec3      { return Vec3{a.X - b.X, a.Y - b.Y, a.Z - b.Z} }
func (a Vec3) Times(t float64) Vec3 { return Vec3{a.X * t, a.Y * t, a.Z * t} }
func (a Vec3) Dot(b Vec3) float64   { return a.X*b.X + a.Y*b.Y + a.Z*b.Z }
func (a Vec3) Norm() float64        { return math.Sqrt(a.Dot(a)) }
func (a Vec3) Unit() Vec3 {
	n := a.Norm()
	if n < 1e-8 {
		return Vec3{}
	}
	return a.Times(1 / n)
}
func ease(x float64) float64 {
	if x < 0 {
		x = 0
	}
	if x > 1 {
		x = 1
	}
	return x * x * (3 - 2*x)
}
func velocity(t float64) float64 {
	switch {
	case t < 0:
		return 0
	case t < 1:
		return 0.8 * ease(t)
	case t < 4.5:
		return 0.8
	case t < 5.7:
		return 0.65
	case t < 6.7:
		return 0.65 * (1 - ease((t-5.7)/1.0))
	default:
		return 0
	}
}
func heading(t float64) float64 { return math.Pi / 3 * ease((t-4.5)/1.2) }
func forward(yaw float64) Vec3  { return Vec3{math.Cos(yaw), math.Sin(yaw), 0} }
func right(yaw float64) Vec3    { return Vec3{-math.Sin(yaw), math.Cos(yaw), 0} }

type Foot struct {
	Pose     Vec3    `json:"position"`
	Contact  bool    `json:"contact"`
	Start    Vec3    `json:"-"`
	Target   Vec3    `json:"-"`
	LiftTime float64 `json:"-"`
	Swing    bool    `json:"-"`
}
type LegFrame struct {
	Hip         Vec3    `json:"hip"`
	Knee        Vec3    `json:"knee"`
	Ankle       Vec3    `json:"ankle"`
	Contact     bool    `json:"contact"`
	IKResidual  float64 `json:"ik_residual_m"`
	ReachExcess float64 `json:"reach_excess_m"`
}
type Frame struct {
	Number int      `json:"frame"`
	Time   float64  `json:"time_seconds"`
	Phase  string   `json:"phase"`
	Root   Vec3     `json:"root"`
	Speed  float64  `json:"root_speed_m_per_s"`
	Yaw    float64  `json:"heading_radians"`
	Left   LegFrame `json:"left_leg"`
	Right  LegFrame `json:"right_leg"`
}
type Receipt struct {
	Status             string   `json:"status"`
	TotalFrames        int      `json:"total_frames"`
	FramesPerSecond    int      `json:"fps"`
	ContactFrames      int      `json:"foot_contact_frames"`
	MaxFootSlipM       float64  `json:"max_planted_foot_slip_m"`
	MaxIKResidualM     float64  `json:"max_ik_residual_m"`
	MaxReachExcessM    float64  `json:"max_unreachable_leg_excess_m"`
	MinGroundHeightM   float64  `json:"min_ground_height_m"`
	TotalRootDistanceM float64  `json:"total_root_distance_m"`
	TurnRadians        float64  `json:"total_heading_change_radians"`
	StepEvents         int      `json:"step_events"`
	Limitations        []string `json:"limitations"`
}

func phase(t float64) string {
	if t < 1 {
		return "start"
	}
	if t < 4.5 {
		return "walk"
	}
	if t < 5.7 {
		return "turn"
	}
	if t < 6.7 {
		return "stop"
	}
	return "stand"
}
func kneeSolve(hip, ankle, forward Vec3) (Vec3, float64, float64) {
	axis := ankle.Sub(hip)
	d := axis.Norm()
	reachExcess := math.Max(0, d-(UpperLeg+LowerLeg))
	if d < 1e-8 {
		return hip, 1, 0
	}
	u := axis.Unit()
	a := (UpperLeg*UpperLeg - LowerLeg*LowerLeg + d*d) / (2 * d)
	// If unreachable, put knee on the extension and preserve residual rather than
	// silently displaying a geometrically invalid two-bone linkage.
	if a > UpperLeg {
		a = UpperLeg
	}
	h := math.Sqrt(math.Max(0, UpperLeg*UpperLeg-a*a))
	perp := forward.Sub(u.Times(u.Dot(forward))).Unit()
	if perp.Norm() < 0.01 {
		perp = Vec3{0, 1, 0}
	}
	knee := hip.Add(u.Times(a)).Add(perp.Times(h))
	err := math.Max(math.Abs(knee.Sub(hip).Norm()-UpperLeg), math.Abs(ankle.Sub(knee).Norm()-LowerLeg))
	return knee, err, reachExcess
}
func Simulate() ([]Frame, Receipt) {
	feet := [2]Foot{{Pose: Vec3{0, -.10, 0}, Contact: true}, {Pose: Vec3{0, .10, 0}, Contact: true}}
	frames := make([]Frame, 0, int(Seconds*FPS)+1)
	root := Vec3{}
	lastStep := -100.0
	nextSide := 0
	steps := 0
	maxSlip := 0.
	maxIK := 0.
	maxReach := 0.
	minZ := 1e9
	contacts := 0
	prev := feet
	for i := 0; i <= int(Seconds*FPS); i++ {
		t := float64(i) / FPS
		dt := 1.0 / FPS
		yaw := heading(t)
		fwd := forward(yaw)
		side := right(yaw)
		speed := velocity(t)
		if i > 0 {
			root = root.Add(fwd.Times(speed * dt))
		}
		// Fixed cadence, alternating leg planning. One leg is never airborne while
		// the other swings, making the stance-foot world-lock a checkable invariant.
		if t >= .65 && t < 6.1 && t-lastStep >= StepEverySecs && speed > .12 && !feet[0].Swing && !feet[1].Swing {
			foot := &feet[nextSide]
			foot.Swing = true
			foot.Contact = false
			foot.LiftTime = t
			foot.Start = foot.Pose
			sidem := 1.0
			if nextSide == 0 {
				sidem = -1
			}
			future := root.Add(fwd.Times(speed*StepSecs + .27))
			foot.Target = future.Add(side.Times(sidem * .10))
			foot.Target.Z = 0
			lastStep = t
			nextSide = 1 - nextSide
			steps++
		}
		for q := 0; q < 2; q++ {
			ft := &feet[q]
			if ft.Swing {
				u := (t - ft.LiftTime) / StepSecs
				if u >= 1 {
					ft.Pose = ft.Target
					ft.Swing = false
					ft.Contact = true
				} else {
					alpha := ease(u)
					ft.Pose = ft.Start.Times(1 - alpha).Add(ft.Target.Times(alpha))
					ft.Pose.Z = .075 * math.Sin(math.Pi*u)
				}
			}
			if i > 0 && prev[q].Contact && ft.Contact {
				slip := ft.Pose.Sub(prev[q].Pose).Norm()
				if slip > maxSlip {
					maxSlip = slip
				}
				contacts++
			}
			if ft.Pose.Z < minZ {
				minZ = ft.Pose.Z
			}
		}
		legs := [2]LegFrame{}
		for q := 0; q < 2; q++ {
			sign := 1.
			if q == 0 {
				sign = -1
			}
			hip := root.Add(side.Times(sign * .10))
			hip.Z = HipHeight + .010*math.Sin(4*math.Pi*t)
			knee, err, excess := kneeSolve(hip, feet[q].Pose, fwd)
			legs[q] = LegFrame{Hip: hip, Knee: knee, Ankle: feet[q].Pose, Contact: feet[q].Contact, IKResidual: err, ReachExcess: excess}
			if err > maxIK {
				maxIK = err
			}
			if excess > maxReach {
				maxReach = excess
			}
		}
		frames = append(frames, Frame{Number: i + 1, Time: t, Phase: phase(t), Root: root, Speed: speed, Yaw: yaw, Left: legs[0], Right: legs[1]})
		prev = feet
	}
	rec := Receipt{Status: "PASS_TRAJECTORY_AND_CONTACT_PROOF_ONLY", TotalFrames: len(frames), FramesPerSecond: FPS, ContactFrames: contacts, MaxFootSlipM: maxSlip, MaxIKResidualM: maxIK, MaxReachExcessM: maxReach, MinGroundHeightM: minZ, TotalRootDistanceM: root.Norm(), TurnRadians: heading(Seconds), StepEvents: steps, Limitations: []string{
		"Mathematical pelvis/foot/IK targets only; NOT yet transferred to a Blender human rig",
		"No force plates, heel/toe rolling, muscle dynamics or anatomical qualification",
		"No real gait anthropometry, collision, skin/materials, facial or finger performance",
		"Cannot replace video visual QA or independent physical/biomechanical review",
	}}
	if maxSlip > 1e-9 || maxIK > 1e-6 || maxReach > 1e-6 || minZ < -1e-8 || steps < 5 {
		rec.Status = "HOLD_KINEMATIC_INVARIANT_FAILURE"
	}
	return frames, rec
}
