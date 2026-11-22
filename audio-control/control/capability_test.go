package control

import ("encoding/json";"strings";"testing")

func TestCapabilitiesAreDescriptiveNotPermissions(t *testing.T){
 d:=Describe()
 if d.SchemaVersion!=ProtocolVersion||d.IsProduction||d.CanPlayPhysicalAudio||
  !d.RequiresTrustedHostForEffects||!d.SupportsIdempotentCommands{t.Fatalf("unsafe discovery: %+v",d)}
 b,e:=json.Marshal(d);if e!=nil{t.Fatal(e)}
 if !strings.Contains(string(b),`"can_play_physical_audio":false`) ||
    !strings.Contains(string(b),`"host_observation_events"`){t.Fatalf("incomplete descriptor %s",b)}
}
