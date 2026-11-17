import hashlib,json,struct,subprocess,sys,tempfile,unittest
from pathlib import Path
import source_capability as s
def fixture(frames=72,shift=2.56,duplicate=False,heel=False):
    nodes=[];roots=[];skins=[];views=[];acc=[];buf=bytearray()
    for actor in s.ACTORS:
        roots.append(len(nodes));nodes.append({"name":actor+"_SceneRoot"})
        joints=[]
        for bone in s.BONES:
            joints.append(len(nodes));nodes.append({"name":actor+"_"+bone})
        skins.append({"joints":joints})
    if heel:nodes.append({"name":s.ACTORS[0]+"_toe_L"})
    def put(vals,typ):
        while len(buf)%4:buf.append(0)
        off=len(buf)
        for x in vals:buf.extend(struct.pack("<f",x))
        i=len(views);views.append({"buffer":0,"byteOffset":off,"byteLength":len(vals)*4})
        j=len(acc);acc.append({"bufferView":i,"componentType":5126,"count":len(vals)//({"SCALAR":1,"VEC3":3}[typ]),"type":typ})
        return j
    t=put([i/12 for i in range(frames)],"SCALAR");chs=[];sms=[]
    for idx,root in enumerate(roots):
        start=-3.35 if idx==0 else 3.35;direction=1 if idx==0 else -1
        seq=[x for i in range(frames) for x in (start+direction*shift*i/max(1,frames-1),0.,0.)]
        sm=len(sms);sms.append({"input":t,"output":put(seq,"VEC3"),"interpolation":"LINEAR"})
        chs.append({"sampler":sm,"target":{"node":root,"path":"translation"}})
    if duplicate:nodes[2]["name"]=nodes[1]["name"]
    d={"asset":{"version":"2.0"},"extras":{"source_class":"ORIGINAL_SELF_AUTHORED_SYNTHETIC"},
       "nodes":nodes,"scenes":[{"nodes":roots}],"scene":0,"skins":skins,
       "animations":[{"channels":chs,"samplers":sms}],"bufferViews":views,"accessors":acc,
       "buffers":[{"byteLength":len(buf)}]}
    js=json.dumps(d,sort_keys=True).encode();js+=b" "*((-len(js))%4)
    binary=bytes(buf)+b"\0"*((-len(buf))%4)
    size=12+8+len(js)+8+len(binary)
    return struct.pack("<4sII",b"glTF",2,size)+struct.pack("<I4s",len(js),b"JSON")+js+struct.pack("<I4s",len(binary),b"BIN\0")+binary
class Critic(unittest.TestCase):
    def run_fixture(self,raw):
        d,b=s.decode_glb(raw)
        return s.evaluate(d,b,hashlib.sha256(raw).hexdigest())
    def test_original_remains_hold(self):
        r=self.run_fixture(fixture())
        self.assertEqual(r["status"],"HOLD_SOURCE_CONTACT_AND_GAIT")
        self.assertIn("NO_SOURCE_HEEL_TOE_ARTICULATION",r["reasons"])
        self.assertFalse(r["mvp_accepted"])
    def test_toe_name_not_contact(self):
        r=self.run_fixture(fixture(heel=True))
        self.assertFalse(r["foot_contact_qualified"])
    def test_source_clock_changed(self):
        with self.assertRaisesRegex(s.Hold,"CLOCK_72F_12FPS_MISMATCH"):self.run_fixture(fixture(frames=71))
    def test_reversed_approach(self):
        with self.assertRaisesRegex(s.Hold,"TWO_ACTOR_APPROACH_NOT_PROVEN"):self.run_fixture(fixture(shift=-.5))
    def test_duplicate_node(self):
        with self.assertRaisesRegex(s.Hold,"DUPLICATE_NODE_NAMES"):self.run_fixture(fixture(duplicate=True))
    def test_bad_magic(self):
        q=bytearray(fixture());q[0]=0
        with self.assertRaisesRegex(s.Hold,"NOT_GLB"):self.run_fixture(bytes(q))
    def test_truncated_glb(self):
        with self.assertRaisesRegex(s.Hold,"GLB_VERSION_OR_LENGTH"):self.run_fixture(fixture()[:-1])
    def test_duplicate_object_key(self):
        with self.assertRaisesRegex(s.Hold,"DUPLICATE_JSON_KEY"):s.unique([("x",1),("x",2)])
    def test_forged_source_type(self):
        d,b=s.decode_glb(fixture());d["extras"]["source_class"]="PROTECTED_REAL_PERSON"
        with self.assertRaisesRegex(s.Hold,"SOURCE_NOT_ORIGINAL_SYNTHETIC"):s.evaluate(d,b,"0"*64)
    def test_valid_source_cli_hold_returns_nonzero(self):
        with tempfile.TemporaryDirectory() as root:
            f=Path(root)/"actual.glb";f.write_bytes(fixture())
            out=Path(root)/"receipt.json"
            r=subprocess.run([sys.executable,s.__file__,"--glb",str(f),"--out",str(out)],capture_output=True,text=True)
            self.assertEqual(r.returncode,12)
            receipt=json.loads(out.read_text(encoding="utf8"))
            self.assertEqual(receipt["status"],"HOLD_SOURCE_CONTACT_AND_GAIT")
            self.assertFalse(receipt["mvp_accepted"])
    def test_no_source_overwrite(self):
        with tempfile.TemporaryDirectory() as root:
            file=Path(root)/"fixture.glb";file.write_bytes(fixture())
            r=subprocess.run([sys.executable,s.__file__,"--glb",str(file),"--out",str(file)],capture_output=True,text=True)
            self.assertEqual(r.returncode,12);self.assertEqual(file.read_bytes(),fixture())
if __name__=="__main__":unittest.main()
