// Package doe builds an unbiased, shared ENU geometric input matrix for
// independent EBU and VideoLAN panning trials. It does not render or infer
// equivalence between the two engines.
package doe

import (
 "errors"
 "fmt"
 "math"
 "example.invalid/spatial-contract/contract"
)

const Schema="spatial_audio.offaxis_doe.v1"
const VideoLAN="d149ed9744fd399b835c6f2920511f8cbcfce5ea"
const EBU="2db69f8fcea0bc5db8a78e14a9c2ae6ed4283c15"

type Case struct {
 ID string `json:"id"`
 RelativeAzimuthDeg float64 `json:"relative_azimuth_deg"`
 ElevationDeg float64 `json:"elevation_deg"`
 ListenerYawDeg float64 `json:"listener_yaw_deg"`
 DistanceM float64 `json:"distance_m"`
 SourcePositionENU contract.Vec3 `json:"source_position_enu_m"`
 ListenerPositionENU contract.Vec3 `json:"listener_position_enu_m"`
 Recovered contract.RelativePose `json:"go_scene_pose"`
 Layouts []string `json:"layouts"`
 EBUResult string `json:"ebu_gain_status"`
 VideoLANResult string `json:"videolan_pcm_status"`
}
type Matrix struct {
 Schema string `json:"schema"`
 Classification string `json:"classification"`
 TimebaseHz int `json:"sample_rate_hz"`
 VideoLANRevision string `json:"videolan_revision"`
 EBURevision string `json:"ebu_revision"`
 Cases []Case `json:"cases"`
 Claim string `json:"claim"`
}
func normalize(deg float64)float64{
 v:=math.Mod(deg+180,360);if v<0{v+=360};return v-180
}
func Generate()(Matrix,error){
 m:=Matrix{
  Schema:Schema,Classification:contract.Public,TimebaseHz:48000,
  VideoLANRevision:VideoLAN,EBURevision:EBU,
  Claim:"CANONICAL_POSITIONS_ONLY_NO_NATIVE_COMPARISON_NO_PERCEPTUAL_CLAIM",
 }
 // Signed azimuth from listener forward: + right/east; - left/west.
 azimuths:=[]float64{0,45,-45,70,-70,120,180}
 elevations:=[]float64{0,30}
 yaws:=[]float64{0,90,180}
 listener:=contract.Vec3{X:1,Y:2,Z:0.5}
 dist:=10.0
 seen:=map[string]bool{}
 for _,yaw:=range yaws{
  for _,el:=range elevations{
   for _,az:=range azimuths{
    bearing:=(az+yaw)*math.Pi/180
    r:=dist*math.Cos(el*math.Pi/180)
    position:=contract.Vec3{
     X:listener.X+r*math.Sin(bearing),
     Y:listener.Y+r*math.Cos(bearing),
     Z:listener.Z+dist*math.Sin(el*math.Pi/180),
    }
    scene:=contract.SyntheticFixture()
    scene.Listener=[]contract.Key{{TimeMS:0,Position:listener,YawDeg:yaw}}
    scene.Emitters[0].Motion=[]contract.Key{{TimeMS:0,Position:position}}
    pose,e:=contract.PoseAtFrame(scene,scene.Emitters[0].ID,0);if e!=nil{return Matrix{},e}
    if math.Abs(normalize(pose.AzimuthDeg-az))>1e-8 ||
       math.Abs(pose.ElevationDeg-el)>1e-8 ||
       math.Abs(pose.DistanceM-dist)>1e-8 {
     return Matrix{},fmt.Errorf("geometry orientation mismatch yaw=%g az=%g elevation=%g recovered=%+v",yaw,az,el,pose)
    }
    id:=fmt.Sprintf("yaw_%03.0f_el_%02.0f_az_%+04.0f",yaw,el,az)
    if seen[id]{return Matrix{},errors.New("duplicate DoE case")}
    seen[id]=true
    m.Cases=append(m.Cases,Case{
     ID:id,RelativeAzimuthDeg:normalize(az),ElevationDeg:el,
     ListenerYawDeg:yaw,DistanceM:dist,
     SourcePositionENU:position,ListenerPositionENU:listener,
     Recovered:pose,Layouts:[]string{"surround_5_1","surround_7_1"},
     EBUResult:"NOT_MEASURED",VideoLANResult:"NOT_MEASURED",
    })
   }
  }
 }
 if len(m.Cases)!=42{return Matrix{},errors.New("incomplete scientific test matrix")}
 return m,nil
}
