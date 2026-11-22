package control

// Descriptor is a read-only capability discovery result. A capability
// description is NOT an authorization grant and this R0 has no audio devices.
type Descriptor struct {
 SchemaVersion string `json:"schema_version"`
 CapabilityID string `json:"capability_id"`
 Implementation string `json:"implementation"`
 SupportedActions []Action `json:"supported_actions"`
 HostObservationEvents []Action `json:"host_observation_events"`
 SupportsIdempotentCommands bool `json:"supports_idempotent_commands"`
 IsProduction bool `json:"is_production"`
 CanPlayPhysicalAudio bool `json:"can_play_physical_audio"`
 RequiresTrustedHostForEffects bool `json:"requires_trusted_host_for_effects"`
}

func Describe() Descriptor {
 return Descriptor{
  SchemaVersion:ProtocolVersion,
  CapabilityID:"audio.control.session",
  Implementation:"go.pure.reducer.synthetic.r0",
  SupportedActions:[]Action{Configure,RequestStart,Stop,Close},
  HostObservationEvents:[]Action{HostStarted,HostStopped,HostCompleted,HostFailed},
  SupportsIdempotentCommands:true,
  IsProduction:false,
  CanPlayPhysicalAudio:false,
  RequiresTrustedHostForEffects:true,
 }
}
