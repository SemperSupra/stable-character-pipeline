#!/usr/bin/env python3
"""Adversarial independent stdlib contract tests for synthetic morphology."""
import copy
import json
import math
import pathlib
import subprocess
import sys
import tempfile
import unittest

import parameters_v1 as p


class ParametersTests(unittest.TestCase):
    def setUp(self):
        self.state = p.sample(13)

    def test_deterministic_seed_and_canonical_hash(self):
        self.assertEqual(p.sample(13), self.state)
        self.assertEqual(p.sha256(p.sample(13)), p.sha256(self.state))
        self.assertNotEqual(p.sha256(p.sample(14)), p.sha256(self.state))

    def test_source_and_identity_holds(self):
        self.assertEqual(self.state["source_class"], p.SOURCE)
        self.assertEqual(self.state["character_id"], self.state["identity"]["stable_id"])
        for seed in range(150):
            self.assertTrue(p.validate(p.sample(seed)))

    def test_semantic_catalog_complete(self):
        present = {"%s.%s" % (g,k) for g in ("morphology","appearance")
                   for k in self.state[g]}
        self.assertEqual(present, p.ALL_PATHS)
        self.assertGreaterEqual(len(present), 25)

    def test_reject_unknown_control(self):
        self.state["morphology"]["unregistered"] = .5
        with self.assertRaisesRegex(p.ContractError, "CONTROL_SET_MISMATCH"):
            p.validate(self.state)

    def test_reject_nans_and_booleans(self):
        for value in (float("nan"), float("inf"), True, -1.0):
            s = copy.deepcopy(self.state)
            s["appearance"]["skin_melanin"] = value
            with self.assertRaises(p.ContractError):
                p.validate(s)

    def test_reject_anatomical_constraint_violation(self):
        self.state["morphology"]["shoulder_width_m"] = .65
        self.state["morphology"]["height_m"] = 1.2
        with self.assertRaisesRegex(p.ContractError, "SHOULDER_HEIGHT_RATIO"):
            p.validate(self.state)

    def test_time_indexed_reversible_identity(self):
        base = copy.deepcopy(self.state)
        dated = p.add_event(base,"2026-01-02","procedure","hypothesis",{
            "morphology.left_breast_volume":.8,
            "morphology.right_breast_volume":.79})
        dated = p.add_event(dated,"2026-02-03","styling","artist_authored",{
            "appearance.hair_length_m":.54})
        self.assertEqual(base, self.state)
        before = p.snapshot(dated,"2026-01-01")
        after = p.snapshot(dated,"2026-01-03")
        later = p.snapshot(dated,"2026-02-04")
        self.assertEqual(before["morphology"], base["morphology"])
        self.assertNotEqual(after["morphology"], base["morphology"])
        self.assertEqual(after["appearance"], before["appearance"])
        self.assertNotEqual(later["appearance"], before["appearance"])
        self.assertEqual(before["identity"], later["identity"])
        self.assertEqual(dated["identity"], base["identity"])

    def test_reject_identity_overwrite_event(self):
        with self.assertRaisesRegex(p.ContractError,"UNKNOWN_CONTROL"):
            p.add_event(self.state,"2026-03-01","procedure","synthetic",{
                "identity.stable_id":"DifferentPerson"})

    def test_reject_event_with_impossible_combination(self):
        with self.assertRaisesRegex(p.ContractError, "SHOULDER_HEIGHT_RATIO"):
            p.add_event(self.state,"2026-03-01","body_change","synthetic",{
                "morphology.height_m":1.2,"morphology.shoulder_width_m":.65})

    def test_reject_out_of_order_and_duplicate_dates(self):
        e = p.add_event(self.state,"2026-05-05","observation","synthetic",{
            "appearance.hair_length_m":.2})
        for when in ("2026-05-05","2026-04-05"):
            with self.assertRaisesRegex(p.ContractError,"EVENT_ORDER_OR_DUPLICATE_DATE"):
                p.add_event(e,when,"styling","synthetic",{"appearance.hair_length_m":.3})

    def test_reject_unsupported_cause_claim(self):
        with self.assertRaisesRegex(p.ContractError,"EVIDENCE_KIND"):
            p.add_event(self.state,"2026-01-01","procedure","clinically_proven",{
                "morphology.lip_fullness":.8})

    def test_unknown_visibility_must_be_explicit(self):
        self.state["uncertainty"]["morphology.left_breast_volume"] = "unknown"
        self.assertTrue(p.validate(self.state))
        self.assertEqual(self.state["uncertainty"]["morphology.left_breast_volume"],"unknown")
        self.state["uncertainty"]["morphology.left_breast_volume"] = "certain"
        with self.assertRaisesRegex(p.ContractError,"UNCERTAINTY_ENUM"):
            p.validate(self.state)

    def test_clis_and_refuse_existing_output(self):
        script = pathlib.Path(p.__file__)
        with tempfile.TemporaryDirectory() as td:
            target = pathlib.Path(td)/"character.json"
            command = [sys.executable,str(script),"generate","--seed","31","--out",str(target)]
            subprocess.run(command,check=True,capture_output=True,text=True)
            output = subprocess.run(command,capture_output=True,text=True)
            self.assertNotEqual(output.returncode,0)
            validation = subprocess.run([sys.executable,str(script),"validate",str(target)],
                                        check=True,capture_output=True,text=True)
            self.assertTrue(json.loads(validation.stdout)["valid"])
            self.assertEqual(json.loads(target.read_text())["seed"],31)


if __name__ == "__main__":
    unittest.main(verbosity=2)
