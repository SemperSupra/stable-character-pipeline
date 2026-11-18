import sys, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent))
from compare import run
def clip(mode,sha="a"*64):
 return {"schema":"scp.r090.72f-real-shoe-contact.v1","mode":mode,"wardrobe_base_sha256":sha,"fps":12,"frames":72,
 "actors":[{"actor":"AsterOriginal","shoe":"CC0shoe","rest_local_x_partitions":{k:{"penetration_m":0.07,"maximum_contact_slip_m_per_s":.35,"contact_frames":10,"flags":["PENETRATION"]} for k in ("rest_local_x_negative","rest_local_x_positive")}}]}
class Contract(unittest.TestCase):
 def test_valid(self):self.assertEqual(len(run(clip("authored"),clip("recorded"))["actors"]),1)
 def test_wrong_clock(self):
  x=clip("recorded");x["fps"]=24
  with self.assertRaisesRegex(ValueError,"CLOCK"):run(clip("authored"),x)
 def test_wrong_wardrobe(self):
  with self.assertRaisesRegex(ValueError,"SOURCE"):run(clip("authored"),clip("recorded","b"*64))
 def test_no_source_pair(self):
  with self.assertRaisesRegex(ValueError,"ORDER"):run(clip("recorded"),clip("recorded"))
 def test_mismatched_shoes(self):
  x=clip("recorded");x["actors"][0]["shoe"]="FAKE"
  with self.assertRaisesRegex(ValueError,"SHOE"):run(clip("authored"),x)
if __name__=="__main__":unittest.main()
