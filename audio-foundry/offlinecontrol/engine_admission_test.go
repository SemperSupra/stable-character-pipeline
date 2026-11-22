package offlinecontrol

import (
	"fmt"
	"os"
	"os/exec"
	"testing"
)

// Public qualification requires the actual CPU engines. Local developers can
// retain the existing optional-tool skips when this explicit guard is unset.
func TestMain(m *testing.M) {
	if os.Getenv("AUDIO_CONTROL_REQUIRE_FFMPEG") == "1" {
		for _, tool := range []string{"ffmpeg", "ffprobe"} {
			if _, err := exec.LookPath(tool); err != nil {
				fmt.Fprintf(os.Stderr, "required offline qualification tool %s unavailable: %v\n", tool, err)
				os.Exit(1)
			}
		}
		fmt.Fprintln(os.Stdout, "offline_control_required_engines_PASS ffmpeg ffprobe")
	}
	os.Exit(m.Run())
}
