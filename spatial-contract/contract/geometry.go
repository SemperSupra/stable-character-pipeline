package contract

import (
 "errors"
 "fmt"
 "math"
)

// RelativePose is a specific listener-relative source pose at one *integer*
// sample, under world ENU +X east, +Y north, +Z up, meters. Positive azimuth
// is clockwise toward east/right from the listener's forward (+Y at yaw 0).
// Pitch/roll, Doppler, environmental propagation and head pose are NOT modeled.
type RelativePose struct {
 EmitterID string `json:"emitter_id"`
 Frame int `json:"frame"`
 TimeSeconds float64 `json:"time_seconds"`
 Relative Vec3 `json:"relative_position_m"`
 DistanceM float64 `json:"distance_m"`
 AzimuthDeg float64 `json:"azimuth_deg"`
 ElevationDeg float64 `json:"elevation_deg"`
 ListenerYawDeg float64 `json:"listener_yaw_deg"`
 Interpolation string `json:"interpolation"`
 Unmodeled []string `json:"unmodeled_effects"`
}
func wrapAngle(deg float64)float64{
 out:=math.Mod(deg+180,360)
 if out<0{out+=360}
 return out-180
}
func interpolateKey(keys []Key,frame int)(Key,error){
 if len(keys)==0{return Key{},errors.New("no keyframes")}
 last:=keys[len(keys)-1]
 if frame<0{return Key{},errors.New("negative frame")}
 if frame<=keys[0].TimeMS*48{return keys[0],nil}
 if frame>=last.TimeMS*48{return last,nil}
 for i:=1;i<len(keys);i++{
  start,end:=keys[i-1],keys[i]
  a,b:=start.TimeMS*48,end.TimeMS*48
  if frame<=b {
   fraction:=float64(frame-a)/float64(b-a)
   point:=Vec3{
    X:start.Position.X+(end.Position.X-start.Position.X)*fraction,
    Y:start.Position.Y+(end.Position.Y-start.Position.Y)*fraction,
    Z:start.Position.Z+(end.Position.Z-start.Position.Z)*fraction,
   }
   yaw:=wrapAngle(start.YawDeg+wrapAngle(end.YawDeg-start.YawDeg)*fraction)
   return Key{TimeMS:frame/48,Position:point,YawDeg:yaw},nil
  }
 }
 return last,nil
}
// PoseAtFrame performs sample-clock conversion; it is a metadata plan, not
// proof of spatial audio, and fails rather than silently dropping unsupported
// cardioid/spread, roll, propagation or multichannel source behavior.
func PoseAtFrame(s Scene,id string,frame int)(RelativePose,error){
 if e:=s.Validate();e!=nil{return RelativePose{},e}
 if frame<0||frame>=s.DurationMS*48{return RelativePose{},errors.New("frame outside scene")}
 var em *Emitter
 for i:=range s.Emitters {if s.Emitters[i].ID==id{em=&s.Emitters[i];break}}
 if em==nil{return RelativePose{},fmt.Errorf("missing emitter %q",id)}
 if em.Directivity!="omni" || em.SpreadDeg!=0{return RelativePose{},errors.New("emitter directivity/spread requires unqualified backend")}
 listener,e:=interpolateKey(s.Listener,frame);if e!=nil{return RelativePose{},e}
 source,e:=interpolateKey(em.Motion,frame);if e!=nil{return RelativePose{},e}
 dx:=source.Position.X-listener.Position.X
 dy:=source.Position.Y-listener.Position.Y
 dz:=source.Position.Z-listener.Position.Z
 horizontal:=math.Hypot(dx,dy)
 distance:=math.Hypot(horizontal,dz)
 if distance<1e-8{return RelativePose{},errors.New("emitter coincides with listener; undefined azimuth")}
 bearing:=math.Atan2(dx,dy)*180/math.Pi
 azimuth:=wrapAngle(bearing-listener.YawDeg)
 elevation:=math.Atan2(dz,horizontal)*180/math.Pi
 return RelativePose{
  EmitterID:id,Frame:frame,TimeSeconds:float64(frame)/48000,
  Relative:Vec3{dx,dy,dz},DistanceM:distance,AzimuthDeg:azimuth,
  ElevationDeg:elevation,ListenerYawDeg:wrapAngle(listener.YawDeg),
  Interpolation:"linear_position_shortest_yaw_at_exact_sample",
  Unmodeled:[]string{"head_pitch_roll","doppler","occlusion","room_impulse_response","speed_of_sound_attenuation"},
 },nil
}
