// Package service exposes one synthetic anatomy state to humans, automation and agents.
// It is a research-only UI/API interface probe, not a real 3D or anatomy simulator.
package service

import (
 "encoding/json"
 "errors"
 "io"
 "net/http"
 "strings"
 "sync"

 anatomy "example.org/scp/anatomy-bakeoff"
)

type Server struct{mu sync.Mutex; scene anatomy.Scene}
type Change struct{
 Schema string `json:"schema"`
 Revision string `json:"revision"`
 System string `json:"system"`
 Visible bool `json:"visible"`
}
type APIError struct{Status string `json:"status"`;Code string `json:"code"`;Message string `json:"message"`}

func New() *Server{return &Server{scene:anatomy.SyntheticScene()}}
func jsonResponse(w http.ResponseWriter,status int,v any){
 w.Header().Set("Content-Type","application/json; charset=utf-8")
 w.Header().Set("Cache-Control","no-store")
 w.Header().Set("X-Content-Type-Options","nosniff")
 w.WriteHeader(status);_ = json.NewEncoder(w).Encode(v)
}
func failure(w http.ResponseWriter,status int,code,message string){
 jsonResponse(w,status,APIError{Status:"FAIL",Code:code,Message:message})
}
func only(w http.ResponseWriter,r *http.Request,method string)bool{
 if r.Method==method{return true}
 failure(w,http.StatusMethodNotAllowed,"METHOD_NOT_ALLOWED","requires "+method)
 return false
}
func (s *Server) ServeHTTP(w http.ResponseWriter,r *http.Request){
 switch r.URL.Path{
 case "/":
  if !only(w,r,"GET"){return}
  w.Header().Set("Content-Type","text/html; charset=utf-8")
  w.Header().Set("X-Content-Type-Options","nosniff")
  _,_=w.Write([]byte(indexHTML))
 case "/api/describe":
  if !only(w,r,"GET"){return}
  jsonResponse(w,200,map[string]any{"capability":"scp.anatomy.synthetic.viewer.v1",
   "source_schema":anatomy.Schema,"locales":anatomy.Locales,"systems":anatomy.Systems,
   "entrypoints":[]string{"GET /","GET /api/describe","GET /api/scene","POST /api/view"},
   "mutation":"rendering visibility ONLY, never physical simulation","license":"original research fixture",
   "scope":"synthetic only; no real 3D viewer, organ science or accessibility acceptance",
   "errors":[]string{"BAD_CONTENT_TYPE","INVALID_JSON","STALE_REVISION","UNKNOWN_SYSTEM","INVALID_SCENE"}})
 case "/api/scene":
  if !only(w,r,"GET"){return}
  s.mu.Lock(); defer s.mu.Unlock()
  jsonResponse(w,200,map[string]any{"status":"PASS_NARROW","scene":s.scene,
   "visible_ids":anatomy.VisibleIDs(s.scene)})
 case "/api/view":
  if !only(w,r,"POST"){return}
  if !strings.HasPrefix(strings.ToLower(r.Header.Get("Content-Type")),"application/json"){
   failure(w,415,"BAD_CONTENT_TYPE","application/json is required");return
  }
  if r.ContentLength>4096{failure(w,413,"PAYLOAD_TOO_LARGE","limit is 4096 bytes");return}
  dec:=json.NewDecoder(io.LimitReader(r.Body,4097));dec.DisallowUnknownFields()
  var c Change
  if err:=dec.Decode(&c);err!=nil{
   failure(w,400,"INVALID_JSON","malformed command");return
  }
  var tail any
  if err:=dec.Decode(&tail);!errors.Is(err,io.EOF){
   failure(w,400,"INVALID_JSON","multiple JSON values or oversized command");return
  }
  if c.Schema!=anatomy.Schema{failure(w,422,"INVALID_SCENE","source schema mismatch");return}
  s.mu.Lock();defer s.mu.Unlock()
  if c.Revision!=s.scene.Revision{
   failure(w,409,"STALE_REVISION","current scene revision differs");return
  }
  next,receipt,err:=anatomy.SetSystemVisibility(s.scene,c.System,c.Visible)
  if err!=nil{
   failure(w,422,"UNKNOWN_SYSTEM","unknown anatomical system or invalid scene");return
  }
  s.scene=next
  jsonResponse(w,200,map[string]any{"receipt":receipt,"view":s.scene.View,"visible_ids":anatomy.VisibleIDs(s.scene)})
 default:failure(w,404,"NOT_FOUND","unknown entrypoint")
 }
}

const indexHTML = `<!doctype html>
<html lang="en">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Anatomy system visibility — synthetic research viewer</title>
<style>
body{font:1rem/1.5 system-ui,sans-serif;margin:0 auto;padding:1.5rem;max-width:58rem;color:#191919;background:#fafafa}
button,input,select{font:inherit}fieldset{border:1px solid #555;border-radius:.5rem;padding:1rem;margin:1rem 0}
label{display:block;padding:.35rem 0}input[type=checkbox]{margin-right:.7rem;width:1.25rem;height:1.25rem}
:focus-visible{outline:3px solid #1554b5;outline-offset:2px}
#status{padding:.75rem 0;min-height:2rem}#structures{max-height:22rem;overflow:auto}
@media(prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
</style></head>
<body>
<main>
<h1>Visible anatomical systems</h1>
<p>Original synthetic demonstration. No anatomical accuracy, WebGL, or screen-reader interoperability has been independently qualified. Hiding an organ never disables its synthetic physics.</p>
<label for="locale">Anatomical label language</label><select id="locale"><option value="en">English</option><option value="de">Deutsch</option><option value="th">ไทย</option><option value="la">Latin</option></select>
<label for="search">Find an anatomical structure</label><input id="search" type="search" autocomplete="off" placeholder="Search named structures">
<fieldset><legend>Major systems — show or hide</legend><div id="systems"></div></fieldset>
<fieldset><legend>Visible structures (readable without a 3D canvas)</legend><div id="structures"></div></fieldset>
<div id="status" role="status" aria-live="polite" aria-atomic="true"></div>
<p><a href="/api/describe">Machine-readable capability description</a> · <a href="/api/scene">Current machine-readable scene</a></p>
</main>
<script>
"use strict";
const systems=document.getElementById("systems"), structures=document.getElementById("structures");
const lang=document.getElementById("locale"), search=document.getElementById("search");
const status=document.getElementById("status");
let scene=null, catalogue=null;
async function refresh(){
 const [sr,cr]=await Promise.all([fetch("/api/scene"),fetch("/api/describe")]);
 if(!sr.ok||!cr.ok)throw Error("Unable to inspect anatomy state");
 scene=(await sr.json()).scene;catalogue=await cr.json();draw();
}
function nameOf(s){return s.labels[lang.value]||s.labels.en||s.id;}
function draw(){
 systems.replaceChildren();structures.replaceChildren();
 for(const key of catalogue.systems){
   const all=scene.structures.filter(s=>s.systems.includes(key));
   const count=all.filter(s=>scene.view.visible[s.id]).length;
   const label=document.createElement("label");
   const box=document.createElement("input");box.type="checkbox";box.checked=count===all.length&&count>0;
   box.indeterminate=count>0&&count<all.length;box.disabled=all.length===0;
   box.addEventListener("change",async()=>{
     try{status.textContent="Applying view change";
       const rsp=await fetch("/api/view",{method:"POST",headers:{"Content-Type":"application/json"},
         body:JSON.stringify({schema:scene.schema,revision:scene.revision,system:key,visible:box.checked})});
       if(!rsp.ok)throw Error((await rsp.json()).code||"Unable to change view");
       await refresh();status.textContent=key+" visibility updated";box.focus();
     }catch(e){status.textContent=e.message;await refresh();}
   });
   label.append(box,document.createTextNode(key+" ("+count+"/"+all.length+" shown)"));
   systems.appendChild(label);
 }
 const q=search.value.trim().toLocaleLowerCase();
 for(const s of scene.structures){
   if(q&&!Object.values(s.labels).some(t=>t.toLocaleLowerCase().includes(q))&&!s.id.toLowerCase().includes(q))continue;
   const p=document.createElement("p");
   p.textContent=nameOf(s)+" — "+s.systems.join(", ")+" — "+(scene.view.visible[s.id]?"visible":"hidden");
   structures.appendChild(p);
 }
 if(!structures.children.length)structures.textContent="No matching anatomical structures";
}
lang.addEventListener("change",draw);search.addEventListener("input",draw);
refresh().catch(e=>{status.textContent=e.message;});
</script></body></html>`
