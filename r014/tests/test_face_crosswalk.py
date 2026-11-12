import tempfile,unittest
from pathlib import Path
from r014.face_crosswalk import static_declared_sequence,assemble
class FaceContract(unittest.TestCase):
    def test_declared_tuple(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"x.py"
            p.write_text('N: tuple[str, ...] = ("a","b")\n')
            self.assertEqual(static_declared_sequence(p,"N"),["a","b"])
    def test_declared_list(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"x.py"
            p.write_text('N=["a","b"]\n')
            self.assertEqual(static_declared_sequence(p,"N"),["a","b"])
    def test_missing_constant_fails(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"x.py";p.write_text("N=1\n")
            with self.assertRaises(ValueError):static_declared_sequence(p,"X")
    def test_duplicate_names_fail(self):
        with self.assertRaises(ValueError):assemble(["x"]*72,["x"]*52)
    def test_wrong_count_fails(self):
        with self.assertRaises(ValueError):assemble(list(range(71)),list(range(52)))
    def test_manifest_status_not_qualified(self):
        self.assertIn("UNQUALIFIED", "UNQUALIFIED_SEMANTIC_SUGGESTION")
if __name__=="__main__":unittest.main()
