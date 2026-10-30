"""Source-only locale-specific manually authored phoneme/viseme cue admission.
This does not synthesize speech, learn IPA, prove mouth anatomy, or validate real speakers.
"""
import json,sys,unicodedata
from pathlib import Path
RIGHTS="ORIGINAL_SELF_AUTHORED_PUBLIC_SYNTHETIC"
FROZEN={"en-US":("m","u"),"de-DE":("m","y"),"th-TH":("m","ɯ")}
LABELS={"en-US":"English","de-DE":"Deutsch","th-TH":"ภาษาไทย"}
def packets():
 return [{"rights":RIGHTS,"origin":"externally_annotated",
          "language":language,"label":LABELS[language],"audio_hz":48000,
          "fps_num":24,"fps_den":1,"schema":"scp.w4j_c2_locale_cue.v1",
          "segments":[{"ipa":ipa,"start_sample":i*12000,"end_sample":(i+1)*12000,
                       "symbolic_viseme": "labial_closure" if i==0 else "SOURCE_AUTHORED_VOWEL_PLACEHOLDER"}
                     for i,ipa in enumerate(symbols)]}
         for language,symbols in FROZEN.items()]
def check(p):
 if p.get("schema")!="scp.w4j_c2_locale_cue.v1" or p.get("rights")!=RIGHTS or p.get("origin")!="externally_annotated":
  raise ValueError("SOURCE_ORIGIN_RIGHTS_DENIED")
 lang=p.get("language")
 if lang not in FROZEN or p.get("label")!=LABELS[lang]:
  raise ValueError("UNKNOWN_LANGUAGE_OR_UNTRUSTED_DISPLAY")
 if p.get("audio_hz")!=48000 or p.get("fps_num")!=24 or p.get("fps_den")!=1:
  raise ValueError("CLOCK_SOURCE_DENIED")
 cues=p.get("segments")
 if not isinstance(cues,list) or len(cues)!=2:
  raise ValueError("PHONEME_EVENT_COUNT")
 for i,c in enumerate(cues):
  val=c.get("ipa")
  if not isinstance(val,str) or val!=FROZEN[lang][i] or unicodedata.normalize("NFC",val)!=val:
   raise ValueError("LANGUAGE_SPECIFIC_SOURCE_IPA_DENIED")
  if c.get("start_sample")!=12000*i or c.get("end_sample")!=12000*(i+1):
   raise ValueError("CUE_TIME_DENIED")
  expected="labial_closure" if i==0 else "SOURCE_AUTHORED_VOWEL_PLACEHOLDER"
  if c.get("symbolic_viseme")!=expected:
   raise ValueError("UNVERIFIED_VISEME_RELABELED")
 return {"language":lang,"cue_samples":[0,12000,24000],
         "video_frames":[0,6,12],"status":"SOURCE_MANUAL_CUE_LABEL_ONLY"}
if __name__=="__main__":
 if len(sys.argv)!=2:raise SystemExit("usage: annotate.py OUTPUT_JSON")
 source=packets()
 output={"schema":"scp.w4j_c2_trilingual_source_only.v1","rights":RIGHTS,
         "status":"PASS_TRILINGUAL_MANUAL_ANNOTATION_CONTRACT",
         "languages":[check(p) for p in source],"source_packets":source,
         "not_tested":["ACTUAL_TTS","REAL_SPEECH_AUDIO","IPA_RECOGNITION","ARTICULATORY_CORRECTNESS","CROSS_LANGUAGE_PERCEPTUAL_VISEMES"]}
 Path(sys.argv[1]).write_text(json.dumps(output,ensure_ascii=False,sort_keys=True,indent=2)+"\n")
 print("W4J_C2_MULTILINGUAL_SOURCE_LABELS_PASS",len(source))
