"""R043 adversarial original-synthetic-only EXR pixel contract controls.

Each test must prove a specific failure cannot pass as a meaningful render QA
result. No media, private data, GPU or network required to run these tests.
"""
import importlib.util
import math
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

import numpy as np


def load():
    path=Path(__file__).with_name("pixel_decode.py")
    spec=importlib.util.spec_from_file_location("r043_pixel_decode_under_test",path)
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

pd=load()
SIZE=pd.SIZE


def good():
    x={
        "beauty":{c:np.ones((SIZE,SIZE),dtype=np.float32) for c in "RGB"},
        "depth":{"Z":np.full((SIZE,SIZE),7,dtype=np.float32)},
        "object":{"X":np.ones((SIZE,SIZE),dtype=np.float32)},
    }
    y={group:{key:value.copy() for key,value in layer.items()}
       for group,layer in x.items()}
    y["beauty"]["R"][:,:]=.8
    return x,y


class TestPixelSemanticsRedControls(unittest.TestCase):
    def paired(self,x,y):
        with mock.patch.object(pd,"decode",side_effect=((x,{"tag":"baseline"}),(y,{"tag":"material"}))):
            return pd.paired_verify(Path("synthetic-a.exr"),Path("synthetic-b.exr"))

    def test_good_pair_baseline_proves_fixture_valid(self):
        a,b=good()
        receipt=self.paired(a,b)
        self.assertEqual(receipt["status"],"PASS_NARROW_DECODED_RENDER_PASS_SEMANTICS")
        self.assertEqual(receipt["actual_changed_beauty_pixels"],SIZE*SIZE)
        self.assertTrue(receipt["object_id_exact_equal"])
        self.assertEqual(receipt["max_paired_foreground_depth_delta"],0.0)

    def test_missing_beauty_change_fails(self):
        a,b=good()
        b["beauty"]["R"][:,:]=1
        with self.assertRaisesRegex(ValueError,"no material treatment change"):
            self.paired(a,b)

    def test_subthreshold_beauty_change_fails(self):
        a,b=good()
        b["beauty"]["R"][:,:]=1-5e-7
        with self.assertRaisesRegex(ValueError,"no material treatment change"):
            self.paired(a,b)

    def test_object_ids_must_match_exactly(self):
        a,b=good()
        b["object"]["X"][2,3]=2
        with self.assertRaisesRegex(ValueError,"object-index segmentation"):
            self.paired(a,b)

    def test_depth_drift_over_predeclared_100um_fails(self):
        a,b=good()
        b["depth"]["Z"][4,5]=7.01
        with self.assertRaisesRegex(ValueError,"depth changed"):
            self.paired(a,b)

    def test_too_few_valid_depth_pixels_fails(self):
        a,b=good()
        a["depth"]["Z"][:,:]=np.inf
        b["depth"]["Z"][:,:]=np.inf
        a["depth"]["Z"][0,0]=7
        b["depth"]["Z"][0,0]=7
        with self.assertRaisesRegex(ValueError,"not enough paired depth"):
            self.paired(a,b)

    def test_nonfinite_numeric_pass_rejected(self):
        with self.assertRaisesRegex(ValueError,"no finite pixels"):
            pd.analyze_numeric(np.full((SIZE,SIZE),np.nan,dtype=np.float32),"beauty.R")

    def test_wrong_dimension_rejected(self):
        with self.assertRaisesRegex(ValueError,"unexpected dtype or dimensions"):
            pd.analyze_numeric(np.zeros((SIZE-1,SIZE),dtype=np.float32),"depth.Z")

    def test_ambiguous_named_channel_rejected(self):
        names=["LayerA.Combined.R","LayerB.Combined.R"]
        with self.assertRaisesRegex(ValueError,"ambiguous"):
            pd.group_name(names,"combined","R")

    def test_missing_required_channel_rejected(self):
        with self.assertRaisesRegex(ValueError,"missing"):
            pd.group_name(["Layer.Combined.G"],"combined","R")

    def test_non_regular_missing_file_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError,"bounded, non-symlink"):
                pd.decode(Path(d)/"not-there.exr")

    def test_symlink_input_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"source"
            path.write_bytes(b"not an EXR")
            link=Path(d)/"shadow.exr"
            link.symlink_to(path)
            with self.assertRaisesRegex(ValueError,"bounded, non-symlink"):
                pd.decode(link)


if __name__=="__main__":
    unittest.main(verbosity=2)
