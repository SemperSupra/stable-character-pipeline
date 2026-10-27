// Package roadmap validates the durable, least-authority MMD qualification plan.
//
// It does not execute actors, authorize assets, merge, deploy or promote findings.
// It merely makes the public DLE state legible to humans, automation and agents.
package roadmap

import (
    "encoding/json"
    "errors"
    "fmt"
    "io"
    "sort"
    "strings"
)

type Authority struct {
    Repository string `json:"repository"`
    Issue int `json:"issue"`
    DraftPR int `json:"draft_pr"`
    WorkingBranch string `json:"working_branch"`
    Mode string `json:"mode"`
    Promotion string `json:"promotion"`
}

type Rules struct {
    Method string `json:"method"`
    BudgetUSDCeiling int `json:"budget_usd_ceiling"`
    ExecutorScope string `json:"executor_scope"`
    SourceRights string `json:"source_rights"`
    Privacy string `json:"privacy"`
    NoMerge bool `json:"no_merge"`
    NoRelease bool `json:"no_release"`
    NoDeploy bool `json:"no_deploy"`
    NoAutomaticCPEPromotion bool `json:"no_automatic_cpe_promotion"`
    Audiences []string `json:"audiences"`
    PassIsScopeLimited bool `json:"pass_is_scope_limited"`
    Results []string `json:"results"`
}

type Gate struct {
    ID string `json:"id"`
    Status string `json:"status"`
    Evidence string `json:"evidence"`
    Scope string `json:"scope"`
}

type Phase struct {
    ID string `json:"id"`
    Name string `json:"name"`
    Exit string `json:"exit"`
}

type Task struct {
    ID string `json:"id"`
    Phase string `json:"phase"`
    Title string `json:"title"`
    Status string `json:"status"`
    DependsOn []string `json:"depends_on"`
    Executor string `json:"executor"`
    BudgetUSDCeiling int `json:"budget_usd_ceiling"`
    Action string `json:"action"`
    Acceptance string `json:"acceptance"`
    Evidence string `json:"evidence"`
    Audiences []string `json:"audiences"`
    Risk string `json:"risk"`
    Blocker string `json:"blocker,omitempty"`
    CompletionEvidence string `json:"completion_evidence,omitempty"`
}
type Workplan struct {
    Schema string `json:"schema"`
    Updated string `json:"updated"`
    Authority Authority `json:"authority"`
    Rules Rules `json:"rules"`
    ReferenceGates []Gate `json:"reference_gates"`
    Phases []Phase `json:"phases"`
    Tasks []Task `json:"tasks"`
}

const Schema = "scp.mmd.workplan.v1"

func Decode(data []byte) (Workplan, error) {
    var w Workplan
    decoder := json.NewDecoder(strings.NewReader(string(data)))
    decoder.DisallowUnknownFields()
    if err := decoder.Decode(&w); err != nil { return w, fmt.Errorf("workplan JSON: %w", err) }
    var extra interface{}
    if err := decoder.Decode(&extra); !errors.Is(err, io.EOF) {
        return w, errors.New("trailing JSON object or data after workplan")
    }
    if err := Validate(w); err != nil { return w, err }
    return w, nil
}

func isAudienceSet(a []string) bool {
    if len(a) != 3 { return false }
    seen:=map[string]bool{}
    for _, v:=range a {
        if v!="human" && v!="automation" && v!="agent" || seen[v] { return false }
        seen[v]=true
    }
    return len(seen)==3
}

func Validate(w Workplan) error {
    if w.Schema != Schema || w.Updated == "" { return errors.New("incorrect schema or missing update date") }
    if w.Authority.Repository == "" || w.Authority.Issue<=0 || w.Authority.DraftPR<=0 ||
       w.Authority.WorkingBranch=="" || w.Authority.Mode=="" || w.Authority.Promotion=="" {
       return errors.New("missing authoritative DLE/PR/branch boundary")
    }
    r:=w.Rules
    if r.Method!="Discover->Observe->Plan->Apply->Verify" || r.BudgetUSDCeiling!=0 ||
       !r.NoMerge || !r.NoRelease || !r.NoDeploy || !r.NoAutomaticCPEPromotion ||
       !r.PassIsScopeLimited || !isAudienceSet(r.Audiences) || r.SourceRights=="" || r.Privacy=="" || r.ExecutorScope=="" {
       return errors.New("missing or weakened public zero-cost, rights, audience or authorization invariant")
    }
    statusAllowed:=map[string]bool{"DONE":true,"READY":true,"PLANNED":true,"BLOCKED":true}
    riskAllowed:=map[string]bool{"low":true,"medium":true,"high":true}
    executorAllowed:=map[string]bool{
       "gha-public-cpu":true, "local-actor-candidate":true,
       "research-direct":true, "cpe-authorized-private":true,
    }
    expectedResult:=map[string]bool{"PASS":true,"FAIL":true,"NOT_TESTED":true,"UNKNOWN":true,"BLOCKED":true}
    if len(r.Results)!=len(expectedResult){return errors.New("missing result-state distinctions")}
    resultSeen:=map[string]bool{}
    for _,result:=range r.Results {
       if !expectedResult[result] || resultSeen[result] { return errors.New("invalid result-state distinctions") }
       resultSeen[result]=true
    }
    if len(w.Phases)==0 || len(w.Tasks)==0 || len(w.ReferenceGates)==0 {
       return errors.New("missing phases, tasks or reference gates")
    }
    phases:=map[string]bool{}
    for _,p:=range w.Phases {
       if p.ID=="" || phases[p.ID] || p.Name=="" || p.Exit=="" { return errors.New("invalid phase") }
       phases[p.ID]=true
    }
    done:=map[string]bool{}
    present:=map[string]bool{}
    for _,g:=range w.ReferenceGates {
        if g.ID=="" || present[g.ID] || g.Status!="DONE" || !strings.HasPrefix(g.Evidence,"https://") || g.Scope=="" {
            return fmt.Errorf("invalid proven reference gate %q",g.ID)
        }
        present[g.ID],done[g.ID]=true,true
    }
    tasks:=map[string]Task{}
    for _, t:=range w.Tasks {
       if t.ID=="" || present[t.ID] || !phases[t.Phase] || !statusAllowed[t.Status] ||
          !executorAllowed[t.Executor] || !riskAllowed[t.Risk] || t.Title=="" || t.Action=="" ||
          t.Acceptance=="" || t.Evidence=="" || !isAudienceSet(t.Audiences) || t.BudgetUSDCeiling!=0 {
          return fmt.Errorf("invalid task identity, readiness or zero-cost/audience contract %q",t.ID)
       }
       if t.Status=="BLOCKED" && t.Blocker=="" { return fmt.Errorf("task %s BLOCKED without reason",t.ID) }
       if t.Status!="BLOCKED" && t.Blocker!="" { return fmt.Errorf("task %s has blocker but is %s",t.ID,t.Status) }
       if t.Status=="DONE" {
          if !strings.HasPrefix(t.CompletionEvidence,"https://") { return fmt.Errorf("task %s DONE without verified evidence",t.ID) }
          done[t.ID]=true
       } else if t.CompletionEvidence!="" {
          return fmt.Errorf("task %s has unearned completion evidence",t.ID)
       }
       present[t.ID]=true
       tasks[t.ID]=t
    }
    for _,t:=range w.Tasks {
       deps:=map[string]bool{}
       for _,dep:=range t.DependsOn {
          if !present[dep] || dep==t.ID || deps[dep] {
              return fmt.Errorf("task %s has missing/self/duplicate dependency %q",t.ID,dep)
          }
          deps[dep]=true
          if t.Status=="READY" || t.Status=="DONE" {
             if !done[dep] { return fmt.Errorf("task %s marked %s despite unmet prerequisite %s",t.ID,t.Status,dep) }
          }
       }
       if len(t.DependsOn)==0 { return fmt.Errorf("task %s missing baseline dependency",t.ID) }
    }
    // Cycle detection even for non-ready tasks: no false route around blocked work.
    colors:=map[string]int{}
    var visit func(string) error
    visit=func(id string) error {
       if colors[id]==1 { return fmt.Errorf("dependency cycle involving %s",id) }
       if colors[id]==2 { return nil }
       colors[id]=1
       for _,dep:=range tasks[id].DependsOn {
          if _,ok:=tasks[dep];ok {
             if err:=visit(dep);err!=nil{return err}
          }
       }
       colors[id]=2
       return nil
    }
    for _,t:=range w.Tasks {
       if err:=visit(t.ID);err!=nil{return err}
    }
    return nil
}

type ReadyItem struct {
    ID string `json:"id"`
    Phase string `json:"phase"`
    Title string `json:"title"`
    Status string `json:"status"`
    DependsOn []string `json:"depends_on"`
    Blocker string `json:"blocker,omitempty"`
    Executor string `json:"executor"`
}

type Snapshot struct {
    Schema string `json:"schema"`
    Authority Authority `json:"authority"`
    Total int `json:"total"`
    Counts map[string]int `json:"counts"`
    Ready []ReadyItem `json:"ready"`
    Planned []ReadyItem `json:"planned"`
    Blocked []ReadyItem `json:"blocked"`
    Done []ReadyItem `json:"done"`
}

func Summarize(w Workplan) Snapshot {
    result:=Snapshot{
       Schema:Schema, Authority:w.Authority,Total:len(w.Tasks),
       Counts:map[string]int{"DONE":0,"READY":0,"PLANNED":0,"BLOCKED":0},
       Ready:[]ReadyItem{},Planned:[]ReadyItem{},Blocked:[]ReadyItem{},Done:[]ReadyItem{},
    }
    for _,t:=range w.Tasks {
       result.Counts[t.Status]++
       item:=ReadyItem{ID:t.ID,Phase:t.Phase,Title:t.Title,Status:t.Status,DependsOn:t.DependsOn,Blocker:t.Blocker,Executor:t.Executor}
       switch t.Status {
       case "READY":result.Ready=append(result.Ready,item)
       case "PLANNED":result.Planned=append(result.Planned,item)
       case "BLOCKED":result.Blocked=append(result.Blocked,item)
       case "DONE":result.Done=append(result.Done,item)
       }
    }
    less:=func(a []ReadyItem){sort.Slice(a,func(i,j int)bool{return a[i].ID<a[j].ID})}
    less(result.Ready);less(result.Planned);less(result.Blocked);less(result.Done)
    return result
}

func Markdown(w Workplan) string {
    s:=Summarize(w)
    var b strings.Builder
    fmt.Fprintf(&b,"# MMD qualification workset — %s\n\n",w.Updated)
    fmt.Fprintf(&b,"Authority: %s issue #%d; unmerged draft PR #%d; branch `%s`.\n\n",s.Authority.Repository,s.Authority.Issue,s.Authority.DraftPR,s.Authority.WorkingBranch)
    fmt.Fprintf(&b,"Tasks: %d; READY %d; PLANNED %d; BLOCKED %d; DONE %d.\n\n",s.Total,s.Counts["READY"],s.Counts["PLANNED"],s.Counts["BLOCKED"],s.Counts["DONE"])
    for _,group:=range []struct{name string;tasks []ReadyItem}{
       {"READY",s.Ready},{"PLANNED",s.Planned},{"BLOCKED",s.Blocked},{"DONE",s.Done}}{
       fmt.Fprintf(&b,"## %s\n\n",group.name)
       if len(group.tasks)==0 {b.WriteString("None.\n\n");continue}
       for _,t:=range group.tasks {
          fmt.Fprintf(&b,"- **%s** (%s) %s; dependencies: %s; executor: %s",t.ID,t.Phase,t.Title,strings.Join(t.DependsOn,", "),t.Executor)
          if t.Blocker!="" {fmt.Fprintf(&b,"; blocker: %s",t.Blocker)}
          b.WriteString(".\n")
       }
       b.WriteString("\n")
    }
    return b.String()
}
