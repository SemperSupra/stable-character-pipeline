"""Independent W2B original synthetic camera/image falsifiers."""
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from projection import project, verify, sha


CAM={"projection":"ORTHOGRAPHIC","width":128,"height":72,"ortho_scale":4.0,
     "matrix_world":[[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]],
     "pixel_aspect":[1,1]}


class CameraPixelTests(unittest.TestCase):
    def movie(self,root,shade):
        video=root/"video.mp4"
        subprocess.run(["ffmpeg","-nostdin","-v","error","-y","-f","lavfi","-i",
                        f"color=c={shade}:s=128x72:r=12:d=6",
                        "-pix_fmt","yuv420p","-c:v","libx264",str(video)],
                       check=True,timeout=40)
        return video

    def fixtures(self,root,shade):
        video=self.movie(root,shade)
        native=root/"source.json";manifest=root/"project.json"
        data={"source_rights":"ORIGINAL_SELF_AUTHORED_SYNTHETIC",
              "video_sha256":sha(video),"blend_sha256":"a"*64}
        native.write_text(json.dumps(data))
        points=[]
        for name in ("CobaltOriginal","MarigoldOriginal"):
            for idx in range(56):
                points.append({"actor":name,"vertex":idx,
                               "world_xyz":[0,0,-1],"native_xy":[.5,.5],
                               "native_depth":1})
        scene={"schema":"scp.visualqa.w2b_scene_projection.v1",
               "rights":data["source_rights"],"blend_sha256":data["blend_sha256"],
               "video_sha256":sha(video),"camera":CAM,
               "frames":[{"tick":tick,"mesh_points":points} for tick in (0,12,24,36,48,60,71)]}
        manifest.write_text(json.dumps(scene))
        return manifest,video,native

    def test_project_exact_ortho(self):
        self.assertEqual(project([0,0,-1],CAM),(.5,.5,1))
        u,v,d=project([1,0,-2],CAM)
        self.assertEqual(round(u,5),.75)
        self.assertEqual(round(v,5),.5)
        self.assertEqual(d,2)
        self.assertEqual(round(project([0,1,-2],CAM)[1],5),.94444)

    def test_actual_gray_h264_image_support_is_observation_only(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);manifest,video,native=self.fixtures(root,"gray")
            result=verify(manifest,video,native,root/"receipt.json")
            self.assertEqual(result["status"],"OBSERVED_UNQUALIFIED")
            self.assertEqual(result["anatomical_quality"],"UNKNOWN_NO_SOURCE_APPROVED_ANATOMY")
            self.assertEqual(len(result["frames"]),7)
            self.assertEqual(result["minimum_observed_source_vertex_pixel_support"],1)

    def test_actual_black_video_abstains(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);manifest,video,native=self.fixtures(root,"black")
            self.assertEqual(verify(manifest,video,native,root/"receipt.json")["status"],"UNKNOWN_MISSING_FOREGROUND")

    def test_camera_changed_with_original_native_projection_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);manifest,video,native=self.fixtures(root,"gray")
            scene=json.loads(manifest.read_text())
            scene["frames"][2]["mesh_points"][0]["native_xy"]=[.9,.5]
            manifest.write_text(json.dumps(scene))
            with self.assertRaisesRegex(ValueError,"CAMERA_NATIVE_PROJECTION"):
                verify(manifest,video,native,root/"receipt.json")

    def test_video_substitution_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);manifest,video,native=self.fixtures(root,"gray")
            result=json.loads(native.read_text());result["video_sha256"]="0"*64
            native.write_text(json.dumps(result))
            with self.assertRaisesRegex(ValueError,"CUSTODY"):
                verify(manifest,video,native,root/"receipt.json")

if __name__=="__main__":
    unittest.main()
