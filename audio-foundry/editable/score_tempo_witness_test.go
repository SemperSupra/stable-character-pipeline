package editable

import(
 "bytes"
 "encoding/binary"
 "strings"
 "testing"
)
func fixtureTempoWav(t *testing.T)(Project,ScoreRequest){
 t.Helper()
 p:=EightBarFixtureProject()
 r,e:=FormatScoreRequest(p,[]TempoPoint{{AtTick:0,BPM:120},{AtTick:16*PPQ,BPM:90}},
 []ChoreographyEvent{{ID:"first",ActorID:"actor-a",Role:"leader",Action:"step",Tick:0},
 {ID:"reply",ActorID:"actor-b",Role:"follower",Action:"turn",Tick:17*PPQ}})
 if e!=nil{t.Fatal(e)}
 return p,r
}
func TestOriginalSyntheticWAVMIDIAndScoreReference(t *testing.T){
 p,r:=fixtureTempoWav(t)
 wav,mid,score,rec,e:=RenderOriginalSyntheticTempoWitness(p,r);if e!=nil{t.Fatal(e)}
 if rec.SampleRate!=48000||rec.SampleCount!=896000||len(rec.NoteOnsets)!=20||rec.NoteOnsets[12].Sample!=384000||
 rec.NoteOnsets[13].Sample!=448000||rec.Status!="ORIGINAL_SYNTHETIC_WAV_GENERATED_EXTERNAL_ONSET_REVIEW_REQUIRED" {t.Fatalf("missing original witness %+v",rec)}
 if !bytes.Equal(wav[:4],[]byte("RIFF"))||!bytes.Equal(wav[8:12],[]byte("WAVE"))||int(binary.LittleEndian.Uint32(wav[40:44]))!=2*896000 {t.Fatal("WAV header mismatch")}
 if !bytes.Equal(mid[:4],[]byte("MThd"))||bytes.Count(mid,[]byte{0xFF,0x51,0x03})!=2 {t.Fatal("MIDI not tempo aware")}
 if !strings.Contains(string(score),"<measure number=\"5\">")||
 !strings.Contains(string(score),"<per-minute>90</per-minute>")||strings.Count(string(score),"<measure number=")!=8 {t.Fatal("wrong MusicXML tempo/measure")}
 if int16(binary.LittleEndian.Uint16(wav[44:46]))!=12000{t.Fatal("undetectable onset")}
 wav2,mid2,score2,rec2,e:=RenderOriginalSyntheticTempoWitness(p,r);if e!=nil{t.Fatal(e)}
 if !bytes.Equal(wav,wav2)||!bytes.Equal(mid,mid2)||!bytes.Equal(score,score2)||rec.WAVSHA256!=rec2.WAVSHA256 {t.Fatal("non-reproducible render")}
 if _,e:=ImportMIDI(p,mid);e==nil{t.Fatal("old source MIDI importer incorrectly admitted multitempo stream")}
}
func TestTempoWitnessRejectsUnqualifiedTransforms(t *testing.T){
 p,r:=fixtureTempoWav(t)
 r.Tempo[1].AtTick=17*PPQ
 if _,_,_,_,e:=RenderOriginalSyntheticTempoWitness(p,r);e==nil{t.Fatal("unqualified off-bar MusicXML emitted")}
 p,r=fixtureTempoWav(t);r.AudioProjectSHA256="forged"
 if _,_,_,_,e:=RenderOriginalSyntheticTempoWitness(p,r);e==nil{t.Fatal("forged source accepted")}
 p,r=fixtureTempoWav(t);r.Tempo[1].BPM=0
 if _,_,_,_,e:=RenderOriginalSyntheticTempoWitness(p,r);e==nil{t.Fatal("illegal BPM accepted")}
}
