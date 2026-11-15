# R63 R1 — real OpenCV weak-semantic segmentation vs object-first inverse fitting

**Source:** original synthetic RGB/depth living-room scenes, exact source camera/geometry **kept in independent evaluator**, from [R63 public numerical baseline](https://github.com/SemperSupra/stable-character-pipeline/pull/514). Scientific authority: [Oneirifact R63 #88](https://github.com/SemperSupra/oneirifact-private/issues/88#issuecomment-6899176131).

**Actual dependency / experiment:** `opencv-python-headless==4.11.0.86` **genuine upstream `cv2.kmeans`** with 4 color clusters and limited **human-provided style of weak supervision** (four known RGB exemplar colors including background), not pretrained SAM, SAM3D, general open-vocabulary detection, connected shape understanding or a semantic scene graph. The exemplar-to-cluster mapping is global minimum one-to-one color error across 4! assignments; no ground-truth class pixels/masks used for mapping. Source geometry, cameras, holdout masks and 3D parameters **never exposed to K-means**. Each 48×48 3-color+background RGB is original controlled rendered data, NOT real photographs.

## R63 protocol

Two synthetic couch/chair/mannequin scene arrangements × first two calibrated train cameras, with RGB rendering condition:
- **distinct:** highly separable source object colors. Optimistic oracle-friendly control, demonstrates feasibility of a weak-color segmentation with a palette known in advance.
- **shared_furniture_material:** identical RGB couch+chair surfaces. A pixel-color cluster is **not an object instance detector**; the same visual material makes identity ambiguous even with ideal source cameras, while geometry/occlusion may still separate components via other methods.
- **illumination_noise:** spatially varying brightness and independent Gaussian RGB noise (source original), K=4. Tests model-independent learned-saliency weakness to lighting domain shift.

Each masked train view is fed as per-object observations to the **same 15 continuous parameter, 121-objective** object-first numerical inverse fitting method from R0. The optical-axis metric depth remains independently measured/true, as might happen with a calibrated RGB-D device; no other mask oracle is passed. **Heldout source viewpoints 2 and 3** evaluate recovered model geometry, with source truth withheld from the fit. Exact oracle instance-mask model is run only as the comparator. Record per-class and mean train segmentation IoU, confusion, actual OpenCV 4-center RGB cluster/prototype distances, full source independent geometry/heldout metrics, runtime and PNG evidence.

**Falsifiers:** no fabricated semantically correct furniture mask for visually identical colors, finite deterministic algorithm, 2 cases, 3 distinct nuisances, complete 121 numerical fitting objectives per method, all images original and public-safe. Missing predicted masks are meaningful negative evidence; do not mark as VLM/human-object success. This test is a known source stylized scene at 48×48; method performance **does not transfer to SAM3, real image texture, arbitrary classes, occluded person identity or photo/video segmentation**.

**Run:** standard **free public** Ubuntu GHA, 10 min ceiling, pinned real OpenCV+numpy+Pillow, no model checkpoints, protected assets or private Actions. `python3 research/inverse-scene-r0/opencv_masks.py`, emit `CV2_MASK_METHOD`, `CV2_MASK_FINAL`, `receipt.json`, original controlled PNGs. No production integration or preview release.

**Next candidate:** admitted open-vocabulary/instance segmentation checkpoint with source rights, declared GPU/VRAM and real synthetic + consent-cleared image source, same target labels, visibility, occlusion and material confounders. It is not enough to segment colored regions; instance IDs must persist across camera/time, and 3D scene pose/scale/contact must be independently validated.
