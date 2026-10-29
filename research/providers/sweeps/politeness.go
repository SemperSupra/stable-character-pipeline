package sweeps

import (
 "errors"
 "fmt"
 "math"
 "strings"
)
type AccessPolicy struct {
 ProviderID string `json:"provider_id"`
 PolicyRef string `json:"policy_ref"`
 Verified bool `json:"verified"`
 TermsPermit bool `json:"terms_permit"`
 Operation string `json:"operation"`
 Method string `json:"method"`
 RobotsChecked bool `json:"robots_checked"`
 RobotsAllow bool `json:"robots_allow"`
 UserAgent string `json:"user_agent"`
 VisibleAttribution bool `json:"visible_attribution"`
 MaxPerMinute int `json:"max_per_minute"`
 MaxPerDay int `json:"max_per_day"`
 MinGapMS int64 `json:"min_gap_ms"`
 MaxConcurrency int `json:"max_concurrency"`
 MaxPages int `json:"max_pages"`
 MaxResponseBytes int64 `json:"max_response_bytes"`
 CacheTTLSeconds int `json:"cache_ttl_seconds"`
}
type RequestState struct {
 AttemptTimesMS []int64 `json:"attempt_times_ms"`
 LastAttemptMS int64 `json:"last_attempt_ms"`
 HasAttempt bool `json:"has_attempt"`
 RecentStatus int `json:"recent_status"`
 CooldownUntilMS int64 `json:"cooldown_until_ms"`
 Active int `json:"active"`
 Pages int `json:"pages"`
}
type Permit struct {
 Status string `json:"status"`
 Explanation string `json:"explanation"`
 NextEligibleMS int64 `json:"next_eligible_ms"`
}
func ValidatePolicy(p AccessPolicy) error {
 if p.ProviderID==""||p.PolicyRef==""||!p.Verified||!p.TermsPermit {return errors.New("policy unverified or automation disallowed")}
 if p.Operation!="search_only"&&p.Operation!="read_metadata" {return errors.New("operation not permitted in this workcell")}
 if p.Method!="documented_api"&&p.Method!="crawler"&&p.Method!="self_hosted_search" {return errors.New("invalid access method")}
 if p.Method=="crawler" && (!p.RobotsChecked||!p.RobotsAllow) {return errors.New("robots policy unavailable or disallowed")}
 if p.UserAgent==""||strings.TrimSpace(p.UserAgent)==""||len(p.UserAgent)>180 {return errors.New("meaningful identifying User-Agent required")}
 if p.MaxPerMinute<1||p.MaxPerMinute>30||p.MaxPerDay<1||p.MaxPerDay>200||
  p.MaxConcurrency!=1||p.MinGapMS<1500||p.MaxPages<1||p.MaxPages>3||
  p.MaxResponseBytes<1||p.MaxResponseBytes>131072||p.CacheTTLSeconds<60||
  p.CacheTTLSeconds>86400 {return errors.New("budget beyond conservative research ceiling")}
 if p.ProviderID=="polyhaven"&&!p.VisibleAttribution{return errors.New("live Poly Haven API use must visibly credit source")}
 return nil
}
func CheckPermit(p AccessPolicy,s RequestState,nowMS int64) Permit {
 deny:=func(code,why string, next int64)Permit{return Permit{code,why,next}}
 if err:=ValidatePolicy(p);err!=nil{return deny("POLICY_HOLD",err.Error(),0)}
 if nowMS<0||s.Active<0||s.Pages<0{return deny("INVALID_CLOCK_OR_STATE","negative state",0)}
 if s.RecentStatus==401 {return deny("AUTH_HOLD","401 requires provider authorization, no retry",0)}
 if s.RecentStatus==403 {return deny("ACCESS_HOLD","403 is not permission to rotate identities, no retry",0)}
 if s.RecentStatus==429&&s.CooldownUntilMS==0 {return deny("RATE_HOLD","429 without Retry-After => operator review",0)}
 if s.RecentStatus>=500&&s.RecentStatus<=599&&s.CooldownUntilMS==0 {return deny("SERVER_HOLD","server failure: no automatic retry",0)}
 if s.Active>=p.MaxConcurrency{return deny("CONCURRENCY_HOLD","one active request per provider only",0)}
 if s.Pages>=p.MaxPages {return deny("PAGE_BUDGET_HOLD","paging ceiling reached",0)}
 if nowMS<s.CooldownUntilMS {return deny("RETRY_AFTER_HOLD","provider requested cooldown",s.CooldownUntilMS)}
 if s.HasAttempt&&nowMS<s.LastAttemptMS+p.MinGapMS{return deny("PACE_HOLD","minimum inter-request spacing",s.LastAttemptMS+p.MinGapMS)}
 minuteCount,dayCount:=0,0
 for _,t:=range s.AttemptTimesMS {
  if t>nowMS{return deny("INVALID_CLOCK_OR_STATE","future attempt in history",0)}
  if nowMS-t<60000 {minuteCount++}
  if nowMS-t<86400000 {dayCount++}
 }
 if minuteCount>=p.MaxPerMinute||dayCount>=p.MaxPerDay {return deny("QUOTA_HOLD","conservative provider budget exhausted",0)}
 return deny("PLAN_PERMITTED","Only offline admission: no network or session is exercised",nowMS)
}
func AfterResponse(s RequestState,status int,retryAfterSeconds int,nowMS int64) (RequestState,error){
 if nowMS<0||retryAfterSeconds<0||retryAfterSeconds>86400||status<0||status>599 {return s,errors.New("invalid response record")}
 s.RecentStatus=status
 s.LastAttemptMS=nowMS;s.HasAttempt=true
 s.AttemptTimesMS=append(s.AttemptTimesMS,nowMS);s.Pages++
 if status==429 {
  if retryAfterSeconds==0 {s.CooldownUntilMS=0}else if int64(retryAfterSeconds)>math.MaxInt64/1000-nowMS/1000 {return s,errors.New("cooldown overflow")} else {s.CooldownUntilMS=nowMS+int64(retryAfterSeconds)*1000}
 }
 if status>=500&&status<600 {
  if retryAfterSeconds>0 {s.CooldownUntilMS=nowMS+int64(retryAfterSeconds)*1000}
 }
 return s,nil
}
func CanShareObservedLineage(a,b string)error{
 if a==""||b=="" {return errors.New("unknown ancestry cannot be counted as independent")}
 if a==b{return fmt.Errorf("common upstream ancestry %s",a)}
 return nil
}
