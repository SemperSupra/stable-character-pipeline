//go:build linux

// Package broker is a synthetic-only local HTTP admission seam for the existing
// per-host quota ledger. It is NOT an Internet service or distributed global broker.
package broker

import (
 "crypto/subtle"
 "encoding/json"
 "errors"
 "net"
 "net/http"
 "strings"
 "time"

 "github.com/SemperSupra/stable-character-pipeline/research/providers/ledger"
 "github.com/SemperSupra/stable-character-pipeline/research/providers/sweeps"
)

type Config struct {
 Ledger ledger.Ledger
 Policies map[string]sweeps.AccessPolicy
 Origins map[string]string
 TestCredential string
 Clock func()time.Time
}
type Server struct { cfg Config }
type ReserveRequest struct { Provider string `json:"provider"`; Origin string `json:"origin"` }
type CompleteRequest struct { Ticket ledger.Ticket `json:"ticket"`; HTTPStatus int `json:"http_status"`; RetryAfterSeconds int `json:"retry_after_seconds"` }
type Response struct { Schema string `json:"schema"`; State string `json:"state"`; Ticket *ledger.Ticket `json:"ticket,omitempty"`; Reason string `json:"reason"` }
func New(cfg Config)(*Server,error){
 if cfg.Clock==nil||cfg.Ledger.Path==""||len(cfg.TestCredential)<32||len(cfg.Policies)==0{return nil,errors.New("missing trusted test broker configuration")}
 for id,p:=range cfg.Policies {if id!=p.ProviderID||cfg.Origins[id]=="" {return nil,errors.New("missing exact origin policy binding")}}
 return &Server{cfg:cfg},nil
}
func (s *Server) ServeHTTP(w http.ResponseWriter,r *http.Request){
 w.Header().Set("Cache-Control","no-store")
 w.Header().Set("Content-Type","application/json")
 resp:=Response{Schema:"scp.local_broker_response.v1",State:"HOLD",Reason:"request refused"}
 send:=func(code int, v Response){w.WriteHeader(code);_ = json.NewEncoder(w).Encode(v)}
 host,_,err:=net.SplitHostPort(r.RemoteAddr)
 ip:=net.ParseIP(host)
 if err!=nil||ip==nil||!ip.IsLoopback(){resp.Reason="loopback only";send(http.StatusForbidden,resp);return}
 if r.Method!="POST" {resp.Reason="POST only";send(http.StatusMethodNotAllowed,resp);return}
 auth:=strings.TrimPrefix(r.Header.Get("Authorization"),"Bearer ")
 if len(auth)!=len(s.cfg.TestCredential)||subtle.ConstantTimeCompare([]byte(auth),[]byte(s.cfg.TestCredential))!=1 {resp.Reason="test credential required";send(http.StatusUnauthorized,resp);return}
 if r.Header.Get("Content-Type")!="application/json" {resp.Reason="JSON only";send(http.StatusUnsupportedMediaType,resp);return}
 r.Body=http.MaxBytesReader(w,r.Body,2048)
 decoder:=json.NewDecoder(r.Body);decoder.DisallowUnknownFields()
 now:=s.cfg.Clock().UnixMilli()
 switch r.URL.Path {
 case "/v1/reserve":
  var req ReserveRequest
  if err:=decoder.Decode(&req);err!=nil {resp.Reason="invalid reserve packet";send(400,resp);return}
  p,ok:=s.cfg.Policies[req.Provider]
  if !ok||req.Origin!=s.cfg.Origins[req.Provider]{resp.Reason="unregistered provider/origin";send(403,resp);return}
  ticket,permit,err:=s.cfg.Ledger.Reserve(p,req.Origin,now)
  if err!=nil {resp.Reason="ledger unavailable";send(503,resp);return}
  if permit.Status!="PLAN_PERMITTED" {resp.Reason=permit.Status;send(409,resp);return}
  resp.State="RESERVED";resp.Reason="synthetic offline ticket only";resp.Ticket=&ticket
  send(200,resp);return
 case "/v1/complete":
  var req CompleteRequest
  if err:=decoder.Decode(&req);err!=nil{resp.Reason="invalid completion packet";send(400,resp);return}
  if req.Ticket.ProviderID==""||req.Ticket.Origin!=s.cfg.Origins[req.Ticket.ProviderID] {resp.Reason="unregistered origin";send(403,resp);return}
  if err:=s.cfg.Ledger.Complete(req.Ticket,req.HTTPStatus,req.RetryAfterSeconds,now);err!=nil{resp.Reason="stale or invalid ticket";send(409,resp);return}
  resp.State="COMPLETED";resp.Reason="local synthetic state persisted";send(200,resp);return
 default:
  resp.Reason="unknown operation";send(404,resp);return
 }
}
