package editable

// Original synthetic score-to-PCM onset witness, deliberately separate from
// production Audio Foundry Csound/MIDI import and its fixed-BPM contracts.
// No real performance, final music, dancer or anatomical qualification.
import(
 "bytes"
 "crypto/sha256"
 "encoding/binary"
 "encoding/hex"
 "errors"
 "fmt"
 "math"
 "math/big"
 "sort"
 "strings"
)
type NoteOnset struct{
 Pitch int `json:"pitch"`
 Tick int `json:"tick"`
 Sample int64 `json:"sample"`
}
type TempoPerformanceReceipt struct{
 Schema string `json:"schema"`
 SourceProjectSHA256 string `json:"source_project_sha256"`
 SourceClockPlanID string `json:"source_clock_plan_id"`
 WAVSHA256 string `json:"wav_sha256"`
 MIDISHA256 string `json:"midi_sha256"`
 MusicXMLSHA256 string `json:"musicxml_sha256"`
 SampleRate int `json:"sample_rate_hz"`
 SampleCount int64 `json:"sample_count"`
 PCMFormat string `json:"pcm_format"`
 NoteOnsets []NoteOnset `json:"note_onsets"`
 Status string `json:"status"`
 MIDIResolution string `json:"midi_resolution"`
}
func nearestNonnegative(r *big.Rat)(int64,error){
 if r.Sign()<0{return 0,errors.New("negative sample")}
 twice:=new(big.Int).Mul(r.Num(),big.NewInt(2))
 twice.Add(twice,r.Denom())
 divisor:=new(big.Int).Mul(r.Denom(),big.NewInt(2))
 result:=new(big.Int).Quo(twice,divisor)
 if !result.IsInt64(){return 0,errors.New("sample count overflow")}
 return result.Int64(),nil
}
func samplesAt(tick int64,tempos []TempoPoint,rate int)(int64,error){
 secs,err:=ExactSecondsAt(tick,tempos);if err!=nil{return 0,err}
 rat:=new(big.Rat).Mul(secs,new(big.Rat).SetInt64(int64(rate)))
 return nearestNonnegative(rat)
}
func TempoMusicXML(p Project,r ScoreRequest)([]byte,error){
 if err:=validRequest(p,r);err!=nil{return nil,err}
 raw,err:=p.MusicXML();if err!=nil{return nil,err}
 s:=string(raw)
 for i,tp:=range r.Tempo{
  if tp.AtTick%(4*PPQ)!=0{return nil,errors.New("tempo offset not on supported MusicXML bar boundary")}
  if i==0{continue} // base exporter already carries original source BPM
  marker:=fmt.Sprintf("<measure number=\"%d\">\n",tp.AtTick/(4*PPQ)+1)
  if strings.Count(s,marker)!=1{return nil,errors.New("tempo XML measure missing or ambiguous")}
  direction:=fmt.Sprintf("<direction><direction-type><metronome><beat-unit>quarter</beat-unit><per-minute>%d</per-minute></metronome></direction-type><sound tempo=\"%d\" /></direction>\n",tp.BPM,tp.BPM)
  s=strings.Replace(s,marker,marker+direction,1)
 }
 return []byte(s),nil
}
func TempoMIDI(p Project,r ScoreRequest)([]byte,error){
 if err:=validRequest(p,r);err!=nil{return nil,err}
 type ev struct{tick int;priority int;raw []byte}
 events:=[]ev{}
 for _,v:=range r.Tempo{
  micros:=60000000/v.BPM
  if micros<=0||micros>0xFFFFFF{return nil,errors.New("unrepresentable MIDI tempo")}
  events=append(events,ev{int(v.AtTick),0,[]byte{0xFF,0x51,0x03,byte(micros>>16),byte(micros>>8),byte(micros)}})
 }
 for _,n:=range p.Notes{
  events=append(events,ev{n.StartTick,2,[]byte{0x90,byte(n.Pitch),byte(n.Velocity)}},
    ev{n.StartTick+n.LengthTick,1,[]byte{0x80,byte(n.Pitch),0}})
 }
 sort.SliceStable(events,func(i,j int)bool{
  if events[i].tick!=events[j].tick{return events[i].tick<events[j].tick}
  return events[i].priority<events[j].priority
 })
 var track bytes.Buffer
 prev:=0
 for _,e:=range events{
  if e.tick<prev{return nil,errors.New("out-of-order MIDI event")}
  putVLQ(&track,uint32(e.tick-prev));track.Write(e.raw);prev=e.tick
 }
 putVLQ(&track,uint32(p.Beats*PPQ-prev));track.Write([]byte{0xFF,0x2F,0})
 var out bytes.Buffer
 out.WriteString("MThd")
 if err:=binary.Write(&out,binary.BigEndian,uint32(6));err!=nil{return nil,err}
 _=binary.Write(&out,binary.BigEndian,uint16(0))
 _=binary.Write(&out,binary.BigEndian,uint16(1))
 _=binary.Write(&out,binary.BigEndian,uint16(PPQ))
 out.WriteString("MTrk")
 _=binary.Write(&out,binary.BigEndian,uint32(track.Len()))
 out.Write(track.Bytes())
 return out.Bytes(),nil
}
func RenderOriginalSyntheticTempoWitness(p Project,r ScoreRequest)([]byte,[]byte,[]byte,TempoPerformanceReceipt,error){
 if err:=validRequest(p,r);err!=nil{return nil,nil,nil,TempoPerformanceReceipt{},err}
 score,err:=AlignOriginalSynthetic(p,r);if err!=nil{return nil,nil,nil,TempoPerformanceReceipt{},err}
 xml,err:=TempoMusicXML(p,r);if err!=nil{return nil,nil,nil,TempoPerformanceReceipt{},err}
 midi,err:=TempoMIDI(p,r);if err!=nil{return nil,nil,nil,TempoPerformanceReceipt{},err}
 total,err:=samplesAt(int64(p.Beats*PPQ),r.Tempo,p.Rate);if err!=nil{return nil,nil,nil,TempoPerformanceReceipt{},err}
 if total<1||total>1<<23{return nil,nil,nil,TempoPerformanceReceipt{},errors.New("PCM size unsafe")}
 pcm:=make([]int16,total)
 noteOnsets:=make([]NoteOnset,0,len(p.Notes))
 for _,n:=range p.Notes{
  start,err:=samplesAt(int64(n.StartTick),r.Tempo,p.Rate);if err!=nil{return nil,nil,nil,TempoPerformanceReceipt{},err}
  end,err:=samplesAt(int64(n.StartTick+n.LengthTick),r.Tempo,p.Rate);if err!=nil{return nil,nil,nil,TempoPerformanceReceipt{},err}
  if start<0||end>total||end<=start{return nil,nil,nil,TempoPerformanceReceipt{},errors.New("invalid note sample interval")}
  noteOnsets=append(noteOnsets,NoteOnset{Pitch:n.Pitch,Tick:n.StartTick,Sample:start})
  frequency:=440*math.Pow(2,float64(n.Pitch-69)/12)
  for j:=start;j<end;j++{
   phase:=float64(j-start)/float64(p.Rate)
   value:=int16(math.Round(2500*math.Sin(2*math.Pi*frequency*phase)))
   if j-start<64{value=12000} // independently detectable onset mark, NOT production timbre
   pcm[j]=value
  }
 }
 // canonical PCM16 LE mono WAV with exact declared length.
 wav:=make([]byte,44+2*len(pcm))
 copy(wav[0:4],"RIFF")
 binary.LittleEndian.PutUint32(wav[4:8],uint32(len(wav)-8))
 copy(wav[8:12],"WAVE");copy(wav[12:16],"fmt ")
 binary.LittleEndian.PutUint32(wav[16:20],16)
 binary.LittleEndian.PutUint16(wav[20:22],1)
 binary.LittleEndian.PutUint16(wav[22:24],1)
 binary.LittleEndian.PutUint32(wav[24:28],uint32(p.Rate))
 binary.LittleEndian.PutUint32(wav[28:32],uint32(p.Rate*2))
 binary.LittleEndian.PutUint16(wav[32:34],2)
 binary.LittleEndian.PutUint16(wav[34:36],16)
 copy(wav[36:40],"data")
 binary.LittleEndian.PutUint32(wav[40:44],uint32(2*len(pcm)))
 for i,v:=range pcm{binary.LittleEndian.PutUint16(wav[44+2*i:46+2*i],uint16(v))}
 ws:=sha256.Sum256(wav);ms:=sha256.Sum256(midi);xs:=sha256.Sum256(xml)
 receipt:=TempoPerformanceReceipt{
  Schema:"scp.original-synthetic-tempo-onset-witness.v0",
  SourceProjectSHA256:r.AudioProjectSHA256,SourceClockPlanID:score.ContentID,
  WAVSHA256:hex.EncodeToString(ws[:]),MIDISHA256:hex.EncodeToString(ms[:]),
  MusicXMLSHA256:hex.EncodeToString(xs[:]),SampleRate:p.Rate,
  SampleCount:total,PCMFormat:"MONO_PCM16_LE_ONSET_DIAGNOSTIC_NOT_MUSIC_PRODUCTION",
  NoteOnsets:noteOnsets,Status:"ORIGINAL_SYNTHETIC_WAV_GENERATED_EXTERNAL_ONSET_REVIEW_REQUIRED",
  MIDIResolution:"MICROSECONDS_PER_QUARTER_INTEGER_QUANTIZATION",
 }
 return wav,midi,xml,receipt,nil
}
