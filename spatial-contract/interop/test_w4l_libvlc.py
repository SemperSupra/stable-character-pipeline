"""Independent hostile source/receipt oracle tests; no libVLC installation needed."""
import importlib.util
import json
import struct
import tempfile
import unittest
from pathlib import Path

P = Path(__file__).with_name("observe_w4l_libvlc.py")
S = importlib.util.spec_from_file_location("observer_w4l", P)
M = importlib.util.module_from_spec(S)
S.loader.exec_module(M)

def fixture(root):
    root = Path(root)
    pcm = M.source_original()
    (root/"source_s16le.raw").write_bytes(pcm)
    wav = b"RIFF" + struct.pack("<I", 36+len(pcm)) + b"WAVEfmt " + \
          struct.pack("<IHHIIHH", 16,1,1,48000,96000,2,16) + \
          b"data" + struct.pack("<I",len(pcm)) + pcm
    (root/"source.wav").write_bytes(wav)
    (root/"callback_s16le.raw").write_bytes(pcm)
    meta = dict(schema="scp.libvlc_callback_native.v1", engine="libVLC",
                status="ENDED",sample_rate=48000,channels=1,sample_format="S16N",
                input_frames=16384,callback_frames=16384,chunks=4,
                overflow=False,flushes=0,drains=1,pauses=0,resumes=0,
                first_pts=0,last_pts=100,exact_source_copy_claim=False,
                physical_latency_claim=False)
    (root/"native_observation.json").write_text(json.dumps(meta))
    (root/"native_libvlc_version.txt").write_text("3.0.fixture\n")
    return meta

class OriginalPCM(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.root = Path(self.t.name)
        self.meta = fixture(self.root)

    def fail(self,code):
        with self.assertRaisesRegex(ValueError,code):
            M.audit(self.root)

    def replace(self,path, data):
        (self.root/path).write_bytes(data)

    def alter(self, **changes):
        self.meta.update(changes)
        (self.root/"native_observation.json").write_text(json.dumps(self.meta))

    def test_clean_original_fixture(self):
        x=M.audit(self.root)
        self.assertEqual(x["status"],"PASS_FULL_EXACT_SOURCE_COPY_CALLBACK_ONLY")
        self.assertEqual(x["original_source_sha256"],M.EXPECTED_SHA)

    def test_frozen_digest(self):
        self.assertEqual(M.sha(M.source_original()),M.EXPECTED_SHA)

    def test_wrong_native_source(self):
        x=bytearray((self.root/"source_s16le.raw").read_bytes());x[5]=1
        self.replace("source_s16le.raw",x);self.fail("NATIVE_SOURCE")

    def test_wrong_wav_pcm(self):
        x=bytearray((self.root/"source.wav").read_bytes());x[-1]=1
        self.replace("source.wav",x);self.fail("WAV_PCM")

    def test_wrong_wav_rate(self):
        x=bytearray((self.root/"source.wav").read_bytes());x[24]=1
        self.replace("source.wav",x);self.fail("WAV_FORMAT")

    def test_truncated_callback(self):
        x=(self.root/"callback_s16le.raw").read_bytes()[:-2]
        self.replace("callback_s16le.raw",x);self.alter(callback_frames=16383)
        self.fail("CALLBACK_FULL_LENGTH")

    def test_extra_samples_not_trimmed(self):
        x=(self.root/"callback_s16le.raw").read_bytes()+b"\0\0"
        self.replace("callback_s16le.raw",x);self.alter(callback_frames=16385)
        self.fail("CALLBACK_FULL_LENGTH")

    def test_mutated_callback_impulse(self):
        x=bytearray((self.root/"callback_s16le.raw").read_bytes());x[8192*2]=0
        self.replace("callback_s16le.raw",x);self.fail("CALLBACK_PCM")

    def test_false_callback_count(self):
        self.alter(callback_frames=1);self.fail("CALLBACK_RECEIPT_COUNT")

    def test_fake_ended(self):
        self.alter(status="TIMEOUT_OR_ERROR");self.fail("NATIVE_PLAYBACK")

    def test_overflow(self):
        self.alter(overflow=True);self.fail("CALLBACK_OVERFLOW")

    def test_false_claim(self):
        self.alter(physical_latency_claim=True);self.fail("UNAUTHORIZED_NATIVE_CLAIM")

    def test_missing_version(self):
        self.replace("native_libvlc_version.txt",b"");self.fail("NO_LIBVLC_VERSION")

    def test_missing_chunks(self):
        self.alter(chunks=0);self.fail("NO_REAL_CALLBACK")

if __name__ == "__main__":
    unittest.main()
