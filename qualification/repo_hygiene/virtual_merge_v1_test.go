package main

import (
	"strings"
	"testing"
)

func makeTree(files map[string]VirtualGitEntry) VirtualGitTree {
	entries := []VirtualGitEntry{}
	for p, e := range files {
		e.Path = p
		entries = append(entries, e)
	}
	return VirtualGitTree{SHA: strings.Repeat("d", 40), Tree: entries}
}
func blob(c string) VirtualGitEntry {
	return VirtualGitEntry{Mode: "100644", Type: "blob", SHA: strings.Repeat(c, 40)}
}
func fixtureTriplet() VirtualTreeTriplet {
	base := map[string]VirtualGitEntry{"baseline.go": blob("a"), "docs/plan.md": blob("b")}
	parent := map[string]VirtualGitEntry{"baseline.go": blob("a"), "docs/plan.md": blob("c")}
	child := map[string]VirtualGitEntry{"baseline.go": blob("a"), "docs/plan.md": blob("b"), "new/qa.go": blob("e")}
	return VirtualTreeTriplet{Repo: allowedRepo, HistoricalBaseCommit: strings.Repeat("1", 40), CurrentParentCommit: strings.Repeat("2", 40), CurrentChildCommit: strings.Repeat("3", 40), HistoricalBaseTree: makeTree(base), CurrentParentTree: makeTree(parent), CurrentChildTree: makeTree(child)}
}
func TestVirtualTreeThreeWayDisjointNoLossAndDeterminism(t *testing.T) {
	x := fixtureTriplet()
	r, e := InspectVirtualTreeTriplet(x)
	if e != nil {
		t.Fatal(e)
	}
	if r.Verdict != virtualTreeVerdict || r.Mutations != 0 || r.OwnerApproval || r.CombinedLeafFiles != 3 || len(r.ParentChangedPaths) != 1 || len(r.ChildChangedPaths) != 1 || r.Action != "RETAIN_UNMERGED_UNTIL_SOURCE_OWNER_AND_INDEPENDENT_CI_REVIEW" {
		t.Fatalf("unsafe result: %+v", r)
	}
	r2, e := InspectVirtualTreeTriplet(x)
	if e != nil || r.VirtualSourceSHA256 != r2.VirtualSourceSHA256 {
		t.Fatal("non-deterministic source digest")
	}
}
func TestVirtualTreeHostileEvidenceFailsClosed(t *testing.T) {
	tests := []struct {
		name   string
		change func(*VirtualTreeTriplet)
	}{
		{"duplicate parent and child changed path", func(x *VirtualTreeTriplet) {
			found := false
			for i := range x.CurrentChildTree.Tree {
				if x.CurrentChildTree.Tree[i].Path == "docs/plan.md" {
					x.CurrentChildTree.Tree[i].SHA = strings.Repeat("f", 40)
					found = true
				}
			}
			if !found {
				panic("negative fixture path not found")
			}
		}},
		{"truncated tree", func(x *VirtualTreeTriplet) { x.CurrentParentTree.Truncated = true }},
		{"invalid head", func(x *VirtualTreeTriplet) { x.CurrentParentCommit = "bad" }},
		{"wrong private repo", func(x *VirtualTreeTriplet) { x.Repo = "SemperSupra/stable-character-pipeline-private" }},
		{"duplicate entry", func(x *VirtualTreeTriplet) {
			x.CurrentParentTree.Tree = append(x.CurrentParentTree.Tree, x.CurrentParentTree.Tree[0])
		}},
		{"changed symlink", func(x *VirtualTreeTriplet) {
			for i := range x.CurrentChildTree.Tree {
				if x.CurrentChildTree.Tree[i].Path == "new/qa.go" {
					x.CurrentChildTree.Tree[i].Mode = "120000"
				}
			}
		}},
		{"changed submodule", func(x *VirtualTreeTriplet) {
			for i := range x.CurrentChildTree.Tree {
				if x.CurrentChildTree.Tree[i].Path == "new/qa.go" {
					x.CurrentChildTree.Tree[i].Mode = "160000"
					x.CurrentChildTree.Tree[i].Type = "commit"
				}
			}
		}},
		{"wrong SHA", func(x *VirtualTreeTriplet) { x.CurrentParentTree.Tree[0].SHA = "unknown" }},
		{"path traversal", func(x *VirtualTreeTriplet) { x.CurrentParentTree.Tree[0].Path = "../secret" }},
		{"invalid blob mode", func(x *VirtualTreeTriplet) { x.CurrentParentTree.Tree[0].Mode = "040000" }},
		{"bad tree sha", func(x *VirtualTreeTriplet) { x.CurrentParentTree.SHA = "bad" }},
	}
	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			x := fixtureTriplet()
			tc.change(&x)
			if _, e := InspectVirtualTreeTriplet(x); e == nil {
				t.Fatal("forged virtual source accepted")
			}
		})
	}
}
func TestVirtualTreeCaseFoldAndFileDirectoryCollision(t *testing.T) {
	t.Run("case collision", func(t *testing.T) {
		x := fixtureTriplet()
		x.CurrentParentTree.Tree = append(x.CurrentParentTree.Tree, VirtualGitEntry{Path: "Foo.go", Mode: "100644", Type: "blob", SHA: strings.Repeat("4", 40)})
		x.CurrentChildTree.Tree = append(x.CurrentChildTree.Tree, VirtualGitEntry{Path: "foo.go", Mode: "100644", Type: "blob", SHA: strings.Repeat("5", 40)})
		if _, e := InspectVirtualTreeTriplet(x); e == nil {
			t.Fatal("case collision admitted")
		}
	})
	t.Run("file directory", func(t *testing.T) {
		x := fixtureTriplet()
		x.CurrentParentTree.Tree = append(x.CurrentParentTree.Tree, VirtualGitEntry{Path: "research", Mode: "100644", Type: "blob", SHA: strings.Repeat("4", 40)})
		x.CurrentChildTree.Tree = append(x.CurrentChildTree.Tree, VirtualGitEntry{Path: "research/foo.go", Mode: "100644", Type: "blob", SHA: strings.Repeat("5", 40)})
		if _, e := InspectVirtualTreeTriplet(x); e == nil {
			t.Fatal("file directory collision admitted")
		}
	})
}
func TestVirtualTreeHistoricalSourceMayOnlyBeReviewed(t *testing.T) {
	x := fixtureTriplet()
	x.CurrentChildTree.Tree = append(x.CurrentChildTree.Tree, VirtualGitEntry{Path: "README", Mode: "100644", Type: "blob", SHA: strings.Repeat("a", 40)})
	report, err := InspectVirtualTreeTriplet(x)
	if err != nil {
		t.Fatal(err)
	}
	if report.Verdict == "MERGED" || report.OwnerApproval || report.Mutations != 0 {
		t.Fatal("source gate promoted merge")
	}
}
