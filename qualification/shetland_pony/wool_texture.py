"""Original repeatable short-fiber wool texture, real glTF UV/PNG, not shader-only.

Portable glTF 2.0 requires actual image and TEXCOORD_0 attributes. This
source-generated texture overlays 11k+ skinned 3D fibers and cannot substitute
for a real hair simulation or breed-accurate physical coat evidence.
"""
import math
from pathlib import Path

WIDTH=512
HEIGHT=512
SEED=20261106

def shade(u,v,seed=SEED):
    if not 0<=u<=1 or not 0<=v<=1:raise ValueError("texel outside UV")
    # Several crossed anisotropic fine-fiber fields; repeatable across runners.
    directional=math.sin(2*math.pi*(v*110.0+math.sin(u*64.0)*.16))
    secondary=math.sin(2*math.pi*(v*211.0-u*8.0+seed*.000001))
    tufts=math.sin(2*math.pi*(u*7.5+v*14.5+seed*.0000003))
    grain=math.sin(2*math.pi*(u*273.0+v*259.0))
    value=.88+.06*directional+.037*secondary+.03*tufts+.022*grain
    return min(1.04,max(.72,value))

def render_pixels(color,width=WIDTH,height=HEIGHT):
    if width<32 or width>1024 or height<32 or height>1024:
        raise ValueError("unsafe image size")
    if len(color)!=4 or any(not 0<=v<=1 for v in color):
        raise ValueError("bad color")
    out=[]
    for j in range(height):
        v=j/max(1,height-1)
        for i in range(width):
            u=i/max(1,width-1)
            q=shade(u,v)
            out.extend((min(1.,color[0]*q),min(1.,color[1]*q),
                        min(1.,color[2]*q),1.))
    return out

def apply_to_material(mat,color,out_dir,name):
    import bpy
    out_dir=Path(out_dir)
    out_dir.mkdir(parents=True,exist_ok=True)
    image=bpy.data.images.new(name="wool_fiber_"+name,width=WIDTH,height=HEIGHT,
                              alpha=False,float_buffer=False)
    image.pixels.foreach_set(render_pixels(color))
    image.filepath_raw=str(out_dir/("wool_fiber_"+name+".png"))
    image.file_format="PNG"
    image.save()
    image.pack()
    mat.use_nodes=True
    nodes=mat.node_tree.nodes
    principled=nodes.get("Principled BSDF")
    if principled is None:raise ValueError("no principled material")
    img=nodes.new("ShaderNodeTexImage")
    img.name="GLTF_PORTABLE_WOOL_BASECOLOR"
    img.image=image
    img.interpolation="Linear"
    mat.node_tree.links.new(img.outputs["Color"],principled.inputs["Base Color"])
    return {"schema":"equine.wool.texture.v1","texture":image.name,
            "width":WIDTH,"height":HEIGHT,"glb_requirement":"TEXCOORD_0+baseColorTexture",
            "mode":"source_original_streaked_fiber_pbr_albedo","photoreal":"UNACCEPTED"}

def assign_uv(mesh,sides):
    """UV unwrap an original closed swept mesh with separate 2 cap vertices."""
    rings=(len(mesh.vertices)-2)//sides
    if rings<3 or rings*sides+2!=len(mesh.vertices):
        raise ValueError("unexpected structured manifold mesh")
    uv=mesh.uv_layers.get("Wool_0") or mesh.uv_layers.new(name="Wool_0")
    for face in mesh.polygons:
        vertices=[mesh.loops[k].vertex_index for k in face.loop_indices]
        circum=[v%sides for v in vertices if v<rings*sides]
        seam=bool(circum and max(circum)-min(circum)>sides//2)
        for li in face.loop_indices:
            vid=mesh.loops[li].vertex_index
            if vid>=rings*sides:
                u=0. if vid==rings*sides else 1.;v=.5
            else:
                u=(vid//sides)/(rings-1)
                circum_id=vid%sides
                if seam and circum_id==0:circum_id=sides
                v=circum_id/sides
            uv.data[li].uv=(u,v)
    return {"rings":rings,"sides":sides,"uv_layers":len(mesh.uv_layers)}

def assign_fiber_uv(mesh):
    if (len(mesh.vertices)%6)!=0:
        raise ValueError("fiber mesh must have six vertices per strand")
    uv=mesh.uv_layers.get("Wool_0") or mesh.uv_layers.new(name="Wool_0")
    for poly in mesh.polygons:
        for li in poly.loop_indices:
            index=mesh.loops[li].vertex_index%6
            uv.data[li].uv=(0. if index%2==0 else 1.,(index//2)/2.)
    return {"fibers":len(mesh.vertices)//6,"uv_layers":len(mesh.uv_layers)}
