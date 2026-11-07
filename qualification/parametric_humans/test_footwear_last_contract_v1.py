"""Stdlib-only source-policy checks for CI without the private original-only corpus.

Does not assert actual shoe motion, Blender, or anatomy; those require the exact
source GLB, VTK/SciPy, and independent visual/physical validation.
"""
import ast,hashlib,re,unittest
from pathlib import Path
SOURCE=Path(__file__).with_name('footwear_last_v1.py')

class SourceContract(unittest.TestCase):
    def test_source_pinned(self):
        source=SOURCE.read_text()
        tree=ast.parse(source)
        assignments={t.targets[0].id:t.value for t in tree.body if isinstance(t,ast.Assign) and len(t.targets)==1 and isinstance(t.targets[0],ast.Name)}
        self.assertRegex(ast.literal_eval(assignments['SOURCE_SHA256']),r'^[a-f0-9]{64}$')
        self.assertEqual(ast.literal_eval(assignments['SOURCE_SHA256']),'366fc2964e0e156988b0207735d89b8dbba18d6b92d0ac453e0d4fc7846fe99f')
        self.assertEqual(ast.literal_eval(assignments['SCHEMA']),'scp.r009.synthetic_footwear_cross_section_last.v1')
    def test_preservation_guards_present(self):
        root=ast.parse(SOURCE.read_text())
        defs={x.name for x in root.body if isinstance(x,(ast.FunctionDef,ast.AsyncFunctionDef))}
        self.assertTrue({'derive','main','last_geometry','transfer_foot_weights'}<=defs)
        src=SOURCE.read_text()
        for term in ['SOURCE_SHA_MISMATCH','RIG_MISMATCH','SOURCE_PREFIX_MUTATED','NO_OVERWRITE','SHOE_OPENING_DEGENERACY']:
            self.assertIn(term,src)
    def test_non_approval_contract(self):
        src=SOURCE.read_text()
        self.assertIn("'release_approved':False",src)
        self.assertIn("'native_blender_evaluated':False",src)
        self.assertIn("'72_frame_native_contact_qualified':False",src)

if __name__=='__main__':unittest.main()
