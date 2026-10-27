package contract

import (
 "errors"
 "fmt"
)

// SourceFrameAt maps a SCENE frame to its dry SOURCE frame, independent of
// sample activity. A muted scene frame has active=false and sourceFrame=-1.
// Empty/scene_locked means legacy absolute scene-to-file indexing.
// clip_relative means event-local transport with a source offset.
func SourceFrameAt(e Emitter,sceneFrame,totalFrames int)(sourceFrame int,active bool,err error){
 if totalFrames<=0||sceneFrame<0||sceneFrame>=totalFrames{return -1,false,errors.New("invalid scene frame")}
 stop:=e.SourceStopFrame
 if stop==0{stop=totalFrames}
 if e.SourceStartFrame<0||e.SourceStartFrame>=totalFrames||stop<=e.SourceStartFrame||stop>totalFrames {
  return -1,false,errors.New("invalid source activity window")
 }
 if sceneFrame<e.SourceStartFrame||sceneFrame>=stop{return -1,false,nil}
 switch e.SourceTransport{
 case "", "scene_locked":
  if e.SourceOffsetFrame!=0{return -1,false,errors.New("offset requires clip relative")}
  return sceneFrame,true,nil
 case "clip_relative":
  index:=sceneFrame-e.SourceStartFrame+e.SourceOffsetFrame
  if e.SourceOffsetFrame<0 || index<0||index>=totalFrames{return -1,false,fmt.Errorf("source transport out of bounds at scene frame %d",sceneFrame)}
  return index,true,nil
 default:return -1,false,errors.New("unsupported transport mode")
 }
}
