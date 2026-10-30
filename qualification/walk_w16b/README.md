# W16-B bounded W13-A / W13-B numerical join

This isolated original-source workcell compares pinned public W13-A PR #95 at 1967886686d008f8db33e5c90328928d5fe944ed with public W13-B PR #98 at 743055edfbfa744b093b9f7a9014891ea83e43d0. Exact self-authored original solver bodies (CLI removed) and Python independent oracle have been preserved at these source pins.

W13-A pole is an absolute world POINT; W13-B pole is a hip-relative VECTOR. Explicitly subtract the hip to normalize. Four reachable cases must agree on knee XYZ within frozen 1e-8. The fifth is deliberately NOT equivalent: A softens a geometrically unreachable target; B rejects it. Never report this as general solver equivalence.

B's so-called local quaternions are world-aligned segment rotations, not valid hierarchical child-local rotations. A numerical hostile control measures the deformation that results from incorrectly applying the lower as child-local. The five pinned W13-A cases have no measured timestamps; output clock is an openly synthetic 12/1 annotation and must never be treated as source time.

This is a source-compare gate, not a fully admitted W16-A schema conversion (the original W13 rights enum differs from W16-A) or a 3D walking/skin/physical-foot test. The W14/W15 5e-4 indexed vertex gate remains independent. Reproduction inside qualification/walk_w16b: GO111MODULE=off go vet ./... ; go test -race ./... ; go run . fixtures_w13a_pinned.json receipt.json ; python3 independent_check.py fixtures_w13a_pinned.json receipt.json.

No public/private identity data, licensed upstream reuse, merge, release, deploy, paid resource or CPE promotion.
