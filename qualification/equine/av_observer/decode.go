package avobserver

import (
	"bytes"
	"context"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"time"
)

type limitedWriter struct {
	bytes.Buffer
	Limit int
}

func (w *limitedWriter) Write(p []byte) (int, error) {
	if w.Len()+len(p) > w.Limit {
		return 0, errors.New("decoded audio too large")
	}
	return w.Buffer.Write(p)
}

// Decode uses the already-installed disposable FFmpeg executable and does not
// interpret user media as shell commands. Public-safe, duration-bounded fixtures.
func Decode(audioPath string, maxSeconds int) ([]int16, error) {
	if maxSeconds < 1 || maxSeconds > 30 {
		return nil, errors.New("invalid decode duration")
	}
	st, err := os.Stat(audioPath)
	if err != nil {
		return nil, err
	}
	if st.Size() > 32*1024*1024 {
		return nil, errors.New("encoded media input too large")
	}
	ctx, cancel := context.WithTimeout(context.Background(), 20*time.Second)
	defer cancel()
	cmd := exec.CommandContext(ctx, "ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin", "-i", audioPath,
		"-map", "0:a:0", "-ar", "48000", "-ac", "1", "-f", "s16le", "-acodec", "pcm_s16le", "-")
	out := &limitedWriter{Limit: (maxSeconds*Rate + 2400) * 2}
	var stderr bytes.Buffer
	cmd.Stdout = out
	cmd.Stderr = &stderr
	if err = cmd.Run(); err != nil {
		return nil, fmt.Errorf("ffmpeg decode: %w: %s", err, stderr.String())
	}
	buf := out.Bytes()
	if len(buf)%2 != 0 {
		return nil, errors.New("truncated PCM sample")
	}
	pcm := make([]int16, len(buf)/2)
	for i := range pcm {
		pcm[i] = int16(uint16(buf[2*i]) | uint16(buf[2*i+1])<<8)
	}
	return pcm, nil
}
