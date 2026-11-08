// Virtual source merge qualification never mutates Git refs or grants owner authority.
package main

import (
	"crypto/sha256"
	"encoding/hex"
	"errors"
	"fmt"
	"sort"
	"strings"
	"unicode/utf8"
)

const virtualTreeMaxItems = 20000
const virtualTreeVerdict = "VIRTUAL_TREE_DISJOINT_NO_LOSS_CANDIDATE_REVIEW_HOLD"

type VirtualGitEntry struct {
	Path string `json:"path"`
	Mode string `json:"mode"`
	Type string `json:"type"`
	SHA  string `json:"sha"`
}
type VirtualGitTree struct {
	SHA       string            `json:"sha"`
	Truncated bool              `json:"truncated"`
	Tree      []VirtualGitEntry `json:"tree"`
}
type VirtualTreeTriplet struct {
	Repo                 string         `json:"repo"`
	HistoricalBaseCommit string         `json:"historical_base_commit"`
	CurrentParentCommit  string         `json:"current_parent_commit"`
	CurrentChildCommit   string         `json:"current_child_commit"`
	HistoricalBaseTree   VirtualGitTree `json:"historical_base_tree"`
	CurrentParentTree    VirtualGitTree `json:"current_parent_tree"`
	CurrentChildTree     VirtualGitTree `json:"current_child_tree"`
}
type VirtualTreeReport struct {
	Schema               string   `json:"schema"`
	Repo                 string   `json:"repo"`
	HistoricalBaseCommit string   `json:"historical_base_commit"`
	CurrentParentCommit  string   `json:"current_parent_commit"`
	CurrentChildCommit   string   `json:"current_child_commit"`
	ParentChangedPaths   []string `json:"parent_changed_paths"`
	ChildChangedPaths    []string `json:"child_changed_paths"`
	CombinedLeafFiles    int      `json:"combined_leaf_files"`
	VirtualSourceSHA256  string   `json:"virtual_source_sha256"`
	Verdict              string   `json:"verdict"`
	Action               string   `json:"action"`
	Mutations            int      `json:"mutations"`
	OwnerApproval        bool     `json:"owner_approval"`
}

func virtualValidPath(p string) bool {
	if p == "" || !utf8.ValidString(p) || strings.HasPrefix(p, "/") || strings.ContainsAny(p, "\\\n\r\x00") {
		return false
	}
	for _, s := range strings.Split(p, "/") {
		if s == "" || s == "." || s == ".." {
			return false
		}
	}
	return true
}
func virtualTreeFiles(t VirtualGitTree) (map[string]VirtualGitEntry, error) {
	if !shaPattern.MatchString(t.SHA) || t.Truncated || len(t.Tree) == 0 || len(t.Tree) > virtualTreeMaxItems {
		return nil, errors.New("VIRTUAL_TREE_TRUNCATED_OR_UNTRUSTED")
	}
	all := map[string]bool{}
	files := map[string]VirtualGitEntry{}
	for _, e := range t.Tree {
		if !virtualValidPath(e.Path) || !shaPattern.MatchString(e.SHA) || all[e.Path] {
			return nil, errors.New("VIRTUAL_TREE_INVALID_OR_DUPLICATE_ENTRY")
		}
		all[e.Path] = true
		switch e.Type {
		case "tree":
			if e.Mode != "040000" {
				return nil, errors.New("VIRTUAL_TREE_MODE_INVALID")
			}
		case "blob":
			if e.Mode != "100644" && e.Mode != "100755" && e.Mode != "120000" {
				return nil, errors.New("VIRTUAL_BLOB_MODE_INVALID")
			}
			files[e.Path] = e
		case "commit":
			if e.Mode != "160000" {
				return nil, errors.New("VIRTUAL_SUBMODULE_MODE_INVALID")
			}
			files[e.Path] = e
		default:
			return nil, errors.New("VIRTUAL_ENTRY_TYPE_INVALID")
		}
	}
	return files, nil
}
func virtualSame(a VirtualGitEntry, aok bool, b VirtualGitEntry, bok bool) bool {
	if aok != bok {
		return false
	}
	if !aok {
		return true
	}
	return a.Mode == b.Mode && a.Type == b.Type && a.SHA == b.SHA
}
func virtualChanges(base, tip map[string]VirtualGitEntry) []string {
	seen := map[string]bool{}
	out := []string{}
	for k := range base {
		seen[k] = true
	}
	for k := range tip {
		seen[k] = true
	}
	for k := range seen {
		a, okA := base[k]
		b, okB := tip[k]
		if !virtualSame(a, okA, b, okB) {
			out = append(out, k)
		}
	}
	sort.Strings(out)
	return out
}
func virtualCheckPaths(files map[string]VirtualGitEntry) error {
	lower := map[string]string{}
	for p := range files {
		caseKey := strings.ToLower(p)
		if prev, ok := lower[caseKey]; ok && prev != p {
			return fmt.Errorf("VIRTUAL_CASE_COLLISION:%s", p)
		}
		lower[caseKey] = p
		parts := strings.Split(p, "/")
		for i := 1; i < len(parts); i++ {
			prefix := strings.Join(parts[:i], "/")
			if _, exists := files[prefix]; exists {
				return fmt.Errorf("VIRTUAL_FILE_DIRECTORY_COLLISION:%s", p)
			}
		}
	}
	return nil
}
func InspectVirtualTreeTriplet(t VirtualTreeTriplet) (VirtualTreeReport, error) {
	if t.Repo != allowedRepo || !shaPattern.MatchString(t.HistoricalBaseCommit) || !shaPattern.MatchString(t.CurrentParentCommit) || !shaPattern.MatchString(t.CurrentChildCommit) ||
		t.HistoricalBaseCommit == t.CurrentParentCommit || t.HistoricalBaseCommit == t.CurrentChildCommit || t.CurrentParentCommit == t.CurrentChildCommit {
		return VirtualTreeReport{}, errors.New("VIRTUAL_TREE_INVALID_SOURCE_HEADS")
	}
	base, err := virtualTreeFiles(t.HistoricalBaseTree)
	if err != nil {
		return VirtualTreeReport{}, err
	}
	parent, err := virtualTreeFiles(t.CurrentParentTree)
	if err != nil {
		return VirtualTreeReport{}, err
	}
	child, err := virtualTreeFiles(t.CurrentChildTree)
	if err != nil {
		return VirtualTreeReport{}, err
	}
	for _, files := range []map[string]VirtualGitEntry{base, parent, child} {
		if err := virtualCheckPaths(files); err != nil {
			return VirtualTreeReport{}, err
		}
	}
	pc := virtualChanges(base, parent)
	cc := virtualChanges(base, child)
	modified := map[string]bool{}
	for _, p := range pc {
		modified[p] = true
	}
	for _, p := range cc {
		if modified[p] {
			return VirtualTreeReport{}, fmt.Errorf("VIRTUAL_OVERLAPPING_CHANGE:%s", p)
		}
	}
	merged := make(map[string]VirtualGitEntry, len(base)+len(pc)+len(cc))
	for k, v := range base {
		merged[k] = v
	}
	for _, set := range []struct {
		files map[string]VirtualGitEntry
		paths []string
	}{{parent, pc}, {child, cc}} {
		for _, p := range set.paths {
			if v, ok := set.files[p]; ok {
				if v.Mode == "120000" || v.Type == "commit" {
					return VirtualTreeReport{}, fmt.Errorf("VIRTUAL_UNREVIEWED_SYMLINK_OR_SUBMODULE:%s", p)
				}
				merged[p] = v
			} else {
				delete(merged, p)
			}
		}
	}
	if err := virtualCheckPaths(merged); err != nil {
		return VirtualTreeReport{}, err
	}
	for _, set := range []struct {
		files map[string]VirtualGitEntry
		paths []string
	}{{parent, pc}, {child, cc}} {
		for _, p := range set.paths {
			a, okA := set.files[p]
			b, okB := merged[p]
			if !virtualSame(a, okA, b, okB) {
				return VirtualTreeReport{}, fmt.Errorf("VIRTUAL_LOSS_OF_SOURCE:%s", p)
			}
		}
	}
	paths := make([]string, 0, len(merged))
	for path := range merged {
		paths = append(paths, path)
	}
	sort.Strings(paths)
	digest := sha256.New()
	for _, path := range paths {
		e := merged[path]
		fmt.Fprintf(digest, "%s\x00%s\x00%s\x00%s\n", path, e.Mode, e.Type, e.SHA)
	}
	return VirtualTreeReport{Schema: "scp.r009.virtual_tree_no_loss_review.v1", Repo: allowedRepo,
		HistoricalBaseCommit: t.HistoricalBaseCommit, CurrentParentCommit: t.CurrentParentCommit, CurrentChildCommit: t.CurrentChildCommit,
		ParentChangedPaths: pc, ChildChangedPaths: cc, CombinedLeafFiles: len(merged), VirtualSourceSHA256: hex.EncodeToString(digest.Sum(nil)),
		Verdict: virtualTreeVerdict, Action: "RETAIN_UNMERGED_UNTIL_SOURCE_OWNER_AND_INDEPENDENT_CI_REVIEW",
		Mutations: 0, OwnerApproval: false}, nil
}
