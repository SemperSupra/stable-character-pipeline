import copy
import json
import pathlib
import re
import unittest

ROOT = pathlib.Path(__file__).resolve().parent
CATALOG = ROOT / "historical_dance_matches.v1.json"


def validate_catalog(value):
    if value.get("schema_version") != "scp.historical_dance_evidence.v1":
        raise ValueError("invalid catalog schema")
    records = value.get("records")
    if not isinstance(records, list) or not records:
        raise ValueError("empty catalog")
    ids = set()
    for item in records:
        rid = item.get("id")
        if not isinstance(rid, str) or not rid or rid in ids:
            raise ValueError("missing or duplicate source id")
        ids.add(rid)
        if not item.get("video_catalog", "").startswith("https://"):
            raise ValueError("untrusted catalog locator")
        if not item.get("rights_state"):
            raise ValueError("source rights unknown")
        if not item.get("source_page_verified"):
            raise ValueError("unsupported source-page claim")
        if item.get("music", {}).get("original_era_audio") is not False:
            raise ValueError("historical soundtrack authenticity incorrectly asserted")
        if item.get("actual_media_acquired"):
            digest = item.get("media_sha256")
            if not isinstance(digest, str) or not re.fullmatch(r"[a-f0-9]{64}", digest):
                raise ValueError("acquired bytes without source digest")
            if not item.get("direct_video_url", "").startswith("https://"):
                raise ValueError("acquired source without direct locator")
        elif item.get("media_sha256") is not None:
            raise ValueError("unacquired media carries digest")
        if item["kind"] == "modern_reconstruction":
            if not (item.get("filmed_year", 0) > item.get("original_choreography_year", 9999)):
                raise ValueError("reconstruction conflated with period")
            if item.get("actual_media_acquired"):
                raise ValueError("unexpected reconstructed video as acquired")
            if not item.get("choreography_source"):
                raise ValueError("unattributed choreography")
        elif item["kind"] == "period_film":
            if item.get("filmed_year", 9999) > 1920:
                raise ValueError("impossible period-film classification")
        else:
            raise ValueError("unknown evidence kind")
    return True


class CatalogTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.valid = json.loads(CATALOG.read_text(encoding="utf-8"))

    def test_accepts_exact_catalog(self):
        self.assertTrue(validate_catalog(self.valid))
        self.assertEqual(len(self.valid["records"]), 5)

    def test_rejects_duplicate_id(self):
        d = copy.deepcopy(self.valid)
        d["records"][1]["id"] = d["records"][0]["id"]
        with self.assertRaises(ValueError):
            validate_catalog(d)

    def test_rejects_unverified_download_digest(self):
        d = copy.deepcopy(self.valid)
        d["records"][0]["media_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            validate_catalog(d)

    def test_rejects_missing_acquired_digest(self):
        d = copy.deepcopy(self.valid)
        d["records"][-1]["media_sha256"] = None
        with self.assertRaises(ValueError):
            validate_catalog(d)

    def test_rejects_false_original_soundtrack(self):
        d = copy.deepcopy(self.valid)
        d["records"][-1]["music"]["original_era_audio"] = True
        with self.assertRaises(ValueError):
            validate_catalog(d)

    def test_rejects_period_reconstruction_conflation(self):
        d = copy.deepcopy(self.valid)
        d["records"][0]["filmed_year"] = 1697
        with self.assertRaises(ValueError):
            validate_catalog(d)


if __name__ == "__main__":
    unittest.main()
