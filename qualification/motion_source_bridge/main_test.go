package main
import("encoding/json";"strings";"testing")
func fixture()(map[string]any,map[string]any){
 cue:=[]any{}
 pairs:=[][3]string{{"figure-eight-bars","1-8","SOURCE_TEXT_ONLY"},{"partner-cross","1-2","DIRECTION_AND_PARTNER_NOT_A_JOINT_PATH"},{"right-shoulder-rule","1-8","SOURCE_TEXT_RULE_NO_CONTACT_CLAIM"},{"right-turn-inward","3-4","SOURCE_TEXT_ONLY"},{"recross","5-6","SOURCE_TEXT_ONLY"},{"right-turn-front","7-8","SOURCE_TEXT_ONLY"},{"half-bar-jump-cue","4,8","HALF_BAR_CUE_NO_KINEMATIC_CLAIM"}}
 for _,p:=range pairs{cue=append(cue,map[string]any{"id":p[0],"bars":p[1],"start_line":1433,"end_line":1467,"anchor":"original source span","interpretation_status":p[2]})}
 f:=map[string]any{"schema":"scp.source-figure-first-pass.v0","source_sha256":bookHash,"source_edition":edition,"name":"Cross-over","figure_start_line":1433,"figure_end_line":1467,"written_bars":8,"text_status":"SOURCE_SPANS_CHECKED_FIRST_PASS_NOT_INDEPENDENT_GOLD","diagrams_status":"ILLUSTRATIONS_NOT_DIGITALLY_QUALIFIED","music_score_status":"NO_NOTATED_SCORE_BYTES_ADMITTED","independent_review":"PENDING_SECOND_READER","physical_motion":"UNKNOWN_NOT_MEASURED","phrases":cue}
 events:=[]any{map[string]any{"id":"cue1","actor_id":"actor-a","tick":480,"exact_seconds":"1/2","exact_sample_position":"24000","evidence_status":"ORIGINAL_SYNTHETIC_TIME_PROPOSAL_NO_MEASURED_MOTION"},map[string]any{"id":"cue2","actor_id":"actor-b","tick":960,"exact_seconds":"1","exact_sample_position":"48000","evidence_status":"ORIGINAL_SYNTHETIC_TIME_PROPOSAL_NO_MEASURED_MOTION"}}
 s:=map[string]any{"schema":"scp.synthetic.score-audio-time-map.v0","source_audio_project_sha256":projectHash,"timebase":"480_MIDI_TICKS_PER_QUARTER_EXACT_RATIONAL","original_source_audio_bpm":120,"meter":"4/4_SOURCE_PROJECT_ONLY","clock_alignment_status":"DETERMINISTIC_SOURCE_CLOCK_DIVERGENCE_NOT_RENDERED_AUDIO","score_minus_audio_end_samples":"128000","original_source_audio_end_samples":"768000","proposed_score_end_samples":"896000","audio_verification":"SYNTHETIC_SCORE_TIMEMAP_ONLY_AUDIO_WAVEFORM_NOT_CHECKED","performed_audio_accepted":false,"original_source_audio_rate":48000,"events":events}
 return f,s
}
func put(a map[string]any,b map[string]any)([]byte,[]byte){x,_:=json.Marshal(a);y,_:=json.Marshal(b);return x,y}
func TestMetadataNonpromotion(t *testing.T){f,s:=fixture();a,b:=put(f,s);r,e:=bridge(a,b);if e!=nil{t.Fatal(e)};if r["admission"]!="NOT_ADMITTED"||r["qualification"]!="PASS_METADATA_NONPROMOTING_ONLY"{t.Fatal(r)};r2,e:=bridge(a,b);if e!=nil||r["figure_receipt_sha256"]!=r2["figure_receipt_sha256"]{t.Fatal("unstable hash")}}
func TestNegativeFigure(t *testing.T){
 checks:=map[string]func(map[string]any){
 "edition":func(f map[string]any){f["source_edition"]="unknown"},
 "source":func(f map[string]any){f["source_sha256"]=strings.Repeat("0",64)},
 "false_gold":func(f map[string]any){f["text_status"]="ACCEPTED"},
 "diagram":func(f map[string]any){f["diagrams_status"]="APPROVED"},
 "roles":func(f map[string]any){f["physical_motion"]="OBSERVED"},
 "no_cues":func(f map[string]any){f["phrases"]=[]any{}},
 "cue_claim":func(f map[string]any){f["phrases"].([]any)[1].(map[string]any)["interpretation_status"]="MEASURED_JOINTS"},
 }
 for name,change:=range checks{t.Run(name,func(t *testing.T){f,s:=fixture();change(f);a,b:=put(f,s);if _,e:=bridge(a,b);e==nil{t.Fatal("accepted overclaim")}})}
}
func TestNegativeScore(t *testing.T){
 checks:=map[string]func(map[string]any){
 "performed":func(s map[string]any){s["performed_audio_accepted"]=true},
 "waveform":func(s map[string]any){s["audio_verification"]="VERIFIED"},
 "drift":func(s map[string]any){s["events"].([]any)[0].(map[string]any)["exact_sample_position"]="23999"},
 "invalid_rat":func(s map[string]any){s["events"].([]any)[0].(map[string]any)["exact_seconds"]="NaN"},
 "actor":func(s map[string]any){s["events"].([]any)[0].(map[string]any)["actor_id"]="private-person"},
 "status":func(s map[string]any){s["events"].([]any)[0].(map[string]any)["evidence_status"]="OBSERVED"},
 "rate":func(s map[string]any){s["original_source_audio_rate"]=44100},
 "missing":func(s map[string]any){s["source_audio_project_sha256"]=""}}
 for name,change:=range checks{t.Run(name,func(t *testing.T){f,s:=fixture();change(s);a,b:=put(f,s);if _,e:=bridge(a,b);e==nil{t.Fatal("accepted overclaim")}})}
}
func TestDuplicateAndTrailingJSON(t *testing.T){f,s:=fixture();a,b:=put(f,s);duplicate:=strings.Replace(string(a), "\"physical_motion\":\"UNKNOWN_NOT_MEASURED\"", "\"physical_motion\":\"OBSERVED\",\"physical_motion\":\"UNKNOWN_NOT_MEASURED\"",1);if duplicate==string(a){t.Fatal("fixture key")};if _,e:=bridge([]byte(duplicate),b);e==nil{t.Fatal("duplicate JSON key accepted")};if _,e:=bridge(append(a,[]byte("{}")...),b);e==nil{t.Fatal("trailing value accepted")}}
