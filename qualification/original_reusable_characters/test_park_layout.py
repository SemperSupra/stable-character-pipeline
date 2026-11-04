"""Original source-only geometry negatives. Native pixel visibility is still NOT_RUN."""
import ast
import math
import unittest
from pathlib import Path

SCRIPT=Path(__file__).with_name('render_blender.py')

def parsed_layout():
    tree=ast.parse(SCRIPT.read_text(encoding='utf-8'))
    parks=[]
    views=[]
    for n in ast.walk(tree):
        if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='PARK_TREES' for t in n.targets):
            parks.append(ast.literal_eval(n.value))
        if isinstance(n,ast.For) and isinstance(n.target,ast.Tuple):
            names=[x.id for x in n.target.elts if isinstance(x,ast.Name)]
            if names==['view','loc']:
                try: v=ast.literal_eval(n.iter)
                except (ValueError,TypeError):continue
                if isinstance(v,list) and set(x[0] for x in v)=={'front','oblique'}:
                    views.append(v)
    if len(parks)!=1 or len(views)!=1:raise ValueError('SOURCE_SCENE_LITERAL_NOT_UNIQUE')
    return parks[0],views[0]

def background_only(trees,views):
    if len(trees)<4 or len(trees)>20 or len(views)!=2:return False
    if {name for name,_ in views}!={'front','oblique'}:return False
    if any(not all(isinstance(c,(int,float)) and math.isfinite(c) for c in (x,y)) or y<=1.8
           for x,y in trees):return False
    if any(not all(isinstance(c,(int,float)) and math.isfinite(c) for c in loc) or loc[1]>=-7.0
           for _,loc in views):return False
    return True

class ParkLayoutTest(unittest.TestCase):
    def test_authored_background_only(self):
        trees,views=parsed_layout()
        self.assertTrue(background_only(trees,views))
    def test_original_foreground_obstruction_rejected(self):
        trees,views=parsed_layout()
        self.assertFalse(background_only((*trees,(-.8,-2.5)),views))
    def test_foreground_boundary_rejected(self):
        trees,views=parsed_layout()
        self.assertFalse(background_only(((0,1.8),)+trees[1:],views))
    def test_oblique_camera_flipped_behind_trees_rejected(self):
        trees,views=parsed_layout()
        self.assertFalse(background_only(trees,[views[0],('oblique',(5.,9.5,4.))]))
    def test_nonfinite_park_geometry_rejected(self):
        trees,views=parsed_layout()
        self.assertFalse(background_only(((math.nan,2.5),)+trees[1:],views))

if __name__=='__main__':unittest.main()
