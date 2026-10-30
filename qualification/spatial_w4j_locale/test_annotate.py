import copy,unittest
from annotate import packets,check
class LanguageTest(unittest.TestCase):
 def test_all_three_source_labels(self):
  p=packets();self.assertEqual([check(x)["language"] for x in p],["en-US","de-DE","th-TH"])
 def test_timing(self):
  for x in packets():self.assertEqual(check(x)["video_frames"],[0,6,12])
 def test_mutations(self):
  mutate={
   "rights":lambda x:x.update(rights="UNKNOWN"),
   "inferred":lambda x:x.update(origin="inferred_unverified"),
   "unknown":lambda x:x.update(language="fr-FR"),
   "forged_label":lambda x:x.update(label="English"),
   "wrong_ipa":lambda x:x["segments"][1].update(ipa="u"),
   "wrong_time":lambda x:x["segments"][1].update(start_sample=13000),
   "wrong_end":lambda x:x["segments"][0].update(end_sample=16000),
   "wrong_fps":lambda x:x.update(fps_num=30),
   "wrong_hz":lambda x:x.update(audio_hz=44100),
   "inferred_viseme":lambda x:x["segments"][1].update(symbolic_viseme="UNVERIFIED_INFERRED_MOUTH_POSE"),
   "missing_ipa":lambda x:x["segments"][0].pop("ipa"),
   "missing_segment":lambda x:x["segments"].pop(),
  }
  for name,func in mutate.items():
   with self.subTest(name=name):
    x=copy.deepcopy(packets()[2]);func(x)
    with self.assertRaises(ValueError):check(x)
if __name__=="__main__":unittest.main()
