package preview

import "github.com/SemperSupra/stable-character-pipeline/research/respiratory-vocal/behavior"

// Fixtures are 100% original, fixed synthetic input specifications.
// Numbers are research input knobs, not measured normal breathing,
// medically safe pressures/airflow, or real instrument performances.
func Fixtures()map[string]behavior.Performance {
 b:=func(action behavior.Action, frames ...behavior.Frame)behavior.Performance{
  return behavior.Performance{Schema:behavior.Schema,Classification:behavior.Classification,
   Action:action,SampleRateHz:behavior.Rate,Frames:frames}
 }
 acoustic:=func(kind behavior.SourceKind,hz,amp float64)behavior.Source{
  return behavior.Source{Kind:kind,NominalHz:hz,Amplitude:amp}
 }
 breath:=func(start,end int,phase behavior.Phase,route behavior.Route,flow float64,amp float64)behavior.Frame{
  f:=behavior.Frame{StartSample:start,EndSample:end,Phase:phase,Route:route,DevicePort:behavior.NoPort}
  switch route{
  case behavior.Nasal:f.NasalFlowM3S=flow;f.VelumOpen=true
  case behavior.Oral:f.OralFlowM3S=flow;f.MouthFreeOpening=true
  case behavior.Mixed:f.NasalFlowM3S=flow*.6;f.OralFlowM3S=flow*.4;f.VelumOpen=true;f.MouthFreeOpening=true
  }
  f.TotalFlowM3S=flow
  if amp>0{f.Sources=[]behavior.Source{acoustic(behavior.AirflowNoise,0,amp)}}
  return f
 }
 voiced:=func(start,end int,phase behavior.Phase,route behavior.Route,flow float64,k behavior.SourceKind,hz,amp float64)behavior.Frame{
  f:=breath(start,end,phase,route,flow,0)
  f.Sources=[]behavior.Source{acoustic(k,hz,amp)}
  return f
 }
 port:=func(action behavior.Action,kind behavior.Port,k behavior.SourceKind,pitch float64,phase behavior.Phase)behavior.Performance{
  flow:=0.0003
  if phase==behavior.Inspiration{flow= -0.0003}
  f:=behavior.Frame{StartSample:0,EndSample:24000,Phase:phase,Route:behavior.ObjectRoute,DevicePort:kind,
   ObjectFlowM3S:flow,TotalFlowM3S:flow}
  if k!=""{f.Sources=[]behavior.Source{acoustic(k,pitch,.7)}}
  return b(action,f)
 }
 click:=func(start,end int)behavior.Frame {
  return behavior.Frame{StartSample:start,EndSample:end,Phase:behavior.Pause,Route:behavior.Closed,
   DevicePort:behavior.NoPort,Sources:[]behavior.Source{acoustic(behavior.ArticulatoryClick,0,.85)}}
 }
 laughBurst:=func(start,end int)behavior.Frame{
  f:=voiced(start,end,behavior.Expiration,behavior.Oral,.00022,behavior.GlottalVoiced,185,.66)
  f.Sources=append(f.Sources,acoustic(behavior.AirflowNoise,0,.16))
  return f
 }
 pause:=func(start,end int)behavior.Frame {
  return behavior.Frame{StartSample:start,EndSample:end,Phase:behavior.Pause,Route:behavior.Closed,DevicePort:behavior.NoPort}
 }
 sob:=voiced(0,24000,behavior.Expiration,behavior.Oral,.00018,behavior.GlottalIrregular,215,.65)
 sob.Sources=append(sob.Sources,acoustic(behavior.AirflowNoise,0,.4))
 scream:=voiced(0,24000,behavior.Expiration,behavior.Oral,.00029,behavior.GlottalIrregular,490,.9)
 scream.Sources=append(scream.Sources,acoustic(behavior.AirflowNoise,0,.5))
 return map[string]behavior.Performance{
  "nasal_quiet":b(behavior.QuietBreath,
    breath(0,24000,behavior.Inspiration,behavior.Nasal,-.0001,.30),
    breath(24000,48000,behavior.Expiration,behavior.Nasal,.0001,.30)),
  "oral_quiet":b(behavior.QuietBreath,
    breath(0,24000,behavior.Inspiration,behavior.Oral,-.0001,.30),
    breath(24000,48000,behavior.Expiration,behavior.Oral,.0001,.30)),
  "oral_heavy":b(behavior.DeepBreath,
    breath(0,24000,behavior.Inspiration,behavior.Oral,-.00030,.60),
    breath(24000,48000,behavior.Expiration,behavior.Oral,.00030,.60)),
  "panting":b(behavior.Pant,
    breath(0,6000,behavior.Expiration,behavior.Oral,.00030,.80),
    breath(6000,12000,behavior.Inspiration,behavior.Oral,-.00030,.80),
    breath(12000,18000,behavior.Expiration,behavior.Oral,.00030,.80),
    breath(18000,24000,behavior.Inspiration,behavior.Oral,-.00030,.80)),
  "humming":b(behavior.Hum,voiced(0,24000,behavior.Expiration,behavior.Nasal,.00016,behavior.GlottalVoiced,180,.75)),
  "singing_two_notes":b(behavior.Sing,
    voiced(0,12000,behavior.Expiration,behavior.Oral,.00020,behavior.GlottalVoiced,220,.75),
    voiced(12000,24000,behavior.Expiration,behavior.Oral,.00020,behavior.GlottalVoiced,261.6256,.75)),
  "lip_whistling":b(behavior.LipWhistleAction,
    voiced(0,24000,behavior.Expiration,behavior.Oral,.00025,behavior.LipWhistle,900,.80)),
  "beatbox_nonpulmonary":b(behavior.Beatbox,click(0,6000),click(6000,12000)),
  "flute_jet":port(behavior.FlutePlay,behavior.Flute,behavior.EdgeTone,660,behavior.Expiration),
  "reed_instrument":port(behavior.ReedPlay,behavior.Reed,behavior.ReedTone,233,behavior.Expiration),
  "external_whistle":port(behavior.BlowWhistle,behavior.ExternalWhistle,behavior.EdgeTone,1000,behavior.Expiration),
  "balloon_airflow":port(behavior.InflateBalloon,behavior.Balloon,behavior.ElasticNoise,0,behavior.Expiration),
  "straw_suction":port(behavior.StrawSuction,behavior.Straw,behavior.AirflowNoise,0,behavior.Inspiration),
  "crying_sob_proxy":b(behavior.Cry,sob),
  "laughing_pulses":b(behavior.Laugh,laughBurst(0,4000),pause(4000,5500),
    laughBurst(5500,9500),pause(9500,11000),laughBurst(11000,15000)),
  "scream_proxy":b(behavior.Scream,scream),
  "no_flow_silence":b(behavior.QuietBreath,pause(0,12000)),
 }
}
