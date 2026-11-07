# R009 — skirt 72-frame regression experiment, preserved first RED (2026-11-07)

This is source-original Aster/Juniper costume research. **The alternate hem flare is REJECTED.** Do not substitute it for the existing garment or claim actual cloth simulation, anatomical realism, male wardrobe correctness, native Blender contact, merge/release or CPE approval.

## What failed

The current source-bound 72-frame CPU vertex-contact observer (source shoe-last GLB SHA256 `a8b493eaba59c965713f4f70f0dccebebcfcc4f3d4ba9aa712d79915e1a05739`) measures skirt vertex penetration >5 mm as follows:

| Statistic | Aster baseline | Aster +17% hem | Juniper baseline | Juniper +17% hem |
|---|---:|---:|---:|---:|
| REST inclusion | 0% | 0.625% | 0% | 1.875% |
| Worst of 72 frames | 2.5% | 1.5625% | 1.875% | 2.1875% |
| Mean over 72 frames | 0.7726% | 0.8854% | 0.5773% | 1.1762% |
| Frames >1% inclusion | 20 | 34 | 22 | 45 |

The original Aster first worst source frame 16 includes 8/320 skirt vertices, and Juniper worst frame 12 includes 6/320, concentrated at the lower hem Y=0.68–0.75 m. A static 17% hem-only radial grade (zero waist change, 0 inverted faces, max edge stretch 1.106x) **did not** solve the problem: it reduced one worst-case value but introduced new intersections at REST, raised the mean and the number of affected frames. Its derivative GLB SHA256 is `8718a6361d46faaa31cf65a70791f05ece02cb66049abd5ef8a3e8fef60603be`. The geometric trial is retained in private Drive **only as failure evidence**.

## Corrective validator

`garment_motion_regression_gate_v1.py` is a pure Python standard-library Pareto/fail-closed regression gate comparing two `scp.r009.makehuman35.shoe_vertex_contact72.v1` receipts. It requires both actors, all four garment slots, 72-frame counts, finite bounded metrics, exact semantic keys, SHA/source differentiation and false-approval controls. It rejects any increase in REST inclusion, max, mean, or frames with more than 1% inclusion, even if another statistic improves. It does **not** claim that a relative improvement implies physical or visual acceptance.

The real source-bound comparison produced **`RED_REGRESSION`**: **7 worsened metrics, 1 improved**, process exit 12; 9/9 stdlib hostile tests PASS. Neither the original nor the rejected derivative is approved.

## Reproduce

```sh
python3 -m unittest -v test_garment_motion_regression_gate_v1
python3 garment_motion_regression_gate_v1.py --baseline footwear_last_72_cli_v1.json --candidate skirt_hem_clearance_v1_72frame_summary.json --out rejection.json
# expected: nonzero exit 12, written verdict RED_REGRESSION
```

The two JSON receipts and full source/negative derivative are retained in the research ZIP with exact SHA. Continue by measuring real cloth/fabric with native Blender evaluated body/gown BVH and local flexibility from the character rig. Aster's feminine skirt is not an approved masculine outfit; PR #337 owns character-specific morphology/wardrobe and remains separate. Do not use a global hem increase as a replacement for pose-dependent cloth deformation.

Repo hygiene: source/test/reusable gate/compact evidence in the existing public draft PR #336 and authoritative DLE #272. Large unaccepted GLBs, full 72-frame receipts and source failure evidence in the existing private Drive folder. No new PR, workflow, issue, merge/release or protected Naomi/Alison source.
