package main

import (
    "bytes"
    "context"
    "crypto/x509"
    "errors"
    "net"
    "sort"
    "crypto/sha256"
    "encoding/hex"
    "encoding/json"
    "flag"
    "fmt"
    "io"
    "net/http"
    "os"
    "strings"
    "time"
)

const maxBody = 128 * 1024
const userAgent = "StableCharacterPipeline-ProviderQualification/0.1 (+https://github.com/SemperSupra/stable-character-pipeline/issues/19)"

type Target struct {
    Provider string
    Lane string
    URL string
    Kind string
    Rights string
}

type Receipt struct {
    Provider string `json:"provider"`
    Lane string `json:"lane"`
    Endpoint string `json:"endpoint"`
    RightsGate string `json:"rights_gate"`
    Status int `json:"http_status"`
    ContentType string `json:"content_type,omitempty"`
    BodyBytesSampled int `json:"body_bytes_sampled"`
    SampleSHA256 string `json:"sample_sha256,omitempty"`
    Truncated bool `json:"truncated"`
    Result string `json:"result"`
    TransportKind string `json:"transport_kind,omitempty"`
    JSONTopKeys []string `json:"json_top_keys,omitempty"`
    ElapsedMS int64 `json:"elapsed_ms"`
}

var targets = []Target{
    {"polyhaven", "A", "https://api.polyhaven.com/files/dirty_football", "json", "cc0-metadata; download not admitted"},
    {"ambientcg", "A", "https://ambientcg.com/api/v3/assets?limit=1", "json", "cc0-claim; verify per-asset"},
    {"openverse", "A", "https://api.openverse.org/v1/images/?q=walking&page_size=1", "json", "license-per-result; no media ingress"},
    {"wikimedia", "A", "https://commons.wikimedia.org/w/api.php?action=query&meta=siteinfo&format=json", "json", "per-file-license; user-agent and rate limits"},
    {"khronos", "B", "https://raw.githubusercontent.com/KhronosGroup/glTF-Sample-Assets/main/README.md", "text", "per-model-license; metadata only"},
    {"cmu-mocap", "B", "https://mocap.cs.cmu.edu/faqs.php", "html", "do not crawl trials; official published archives only"},
    {"quaternius", "B", "https://quaternius.com/license.html", "html", "QAL license; standalone redistribution prohibited"},
    {"kenney", "B", "https://kenney.nl/assets", "html", "per-pack terms; no pack downloads in probe"},
    {"kaykit", "B", "https://kaylousberg.itch.io/kaykit-adventurers", "html", "per-pack terms; no pack downloads in probe"},
    {"open3dlab-feed", "C", "https://open3dlab.com/rss/", "xml", "source discovery only; no scraping/bypass"},
    {"open3dlab-project", "C", "https://open3dlab.com/project/e2a0830d-f166-4b1b-aabf-8ca735d0638c/", "html", "specific user URL; permission unknown"},
    {"sketchfab-data", "C", "https://api.sketchfab.com/v3/models?downloadable=true&count=1", "json", "download API requires OAuth; discovery only"},
    {"blenderkit", "C", "https://www.blenderkit.com/api/v1/search/?query=character&page_size=1", "json", "automation permission unverified"},
    {"poly-pizza", "C", "https://poly.pizza/", "html", "website only; API/rights unverified"},
    {"opengameart", "C", "https://opengameart.org/", "html", "per-item rights; API unverified"},
}

func classify(status int, kind, mime string, body []byte, truncated bool) string {
    if status == 0 { return "TRANSPORT_HOLD" }
    if status >= 300 && status < 400 { return "REDIRECT_HOLD" }
    if status == 401 || status == 403 { return "ACCESS_HOLD" }
    if status == 429 { return "RATE_LIMIT_HOLD" }
    if status >= 500 { return "SERVER_HOLD" }
    if status != 200 { return "HTTP_HOLD" }
    lower := bytes.ToLower(body)
    for _, marker := range [][]byte{[]byte("anubis"), []byte("captcha"), []byte("proof-of-work"), []byte("cf-chl"), []byte("just a moment")} {
        if bytes.Contains(lower, marker) { return "CHALLENGE_HOLD" }
    }
    if truncated { return "TRUNCATED_REVIEW" }
    ctype := strings.ToLower(mime)
    switch kind {
    case "json":
        if !strings.Contains(ctype, "json") || !json.Valid(body) { return "CONTENT_MISMATCH_HOLD" }
        return "API_METADATA_OK"
    case "xml":
        if !(strings.Contains(ctype, "xml") || strings.Contains(ctype, "rss") || strings.Contains(ctype, "atom")) { return "CONTENT_MISMATCH_HOLD" }
        if !bytes.Contains(lower, []byte("<rss")) && !bytes.Contains(lower, []byte("<feed")) { return "CONTENT_MISMATCH_HOLD" }
        return "FEED_METADATA_OK"
    case "html":
        if !strings.Contains(ctype, "html") { return "CONTENT_MISMATCH_HOLD" }
        return "HTML_ONLY_REVIEW"
    case "text":
        if !strings.Contains(ctype, "text") && !strings.Contains(ctype, "markdown") { return "CONTENT_MISMATCH_HOLD" }
        return "TEXT_METADATA_OK"
    }
    return "UNSUPPORTED_KIND_HOLD"
}

func transportKind(err error) string {
    if errors.Is(err, context.DeadlineExceeded) { return "TIMEOUT" }
    var netErr net.Error
    if errors.As(err, &netErr) && netErr.Timeout() { return "TIMEOUT" }
    var dnsErr *net.DNSError
    if errors.As(err, &dnsErr) { return "DNS" }
    var certErr x509.UnknownAuthorityError
    if errors.As(err, &certErr) { return "TLS_CERT" }
    var opErr *net.OpError
    if errors.As(err, &opErr) { return "NETWORK" }
    return "OTHER"
}

func probe(t Target) (receipt Receipt) {
    receipt = Receipt{Provider:t.Provider, Lane:t.Lane, Endpoint:t.URL, RightsGate:t.Rights}
    start := time.Now()
    defer func(){ receipt.ElapsedMS = time.Since(start).Milliseconds() }()
    req, err := http.NewRequest(http.MethodGet, t.URL, nil)
    if err != nil { receipt.Result = "TRANSPORT_HOLD"; receipt.TransportKind = transportKind(err); return receipt }
    req.Header.Set("User-Agent", userAgent)
    req.Header.Set("Accept", "application/json, application/xml, text/html, text/plain;q=0.8")
    client := &http.Client{
        Timeout: 12*time.Second,
        CheckRedirect: func(_ *http.Request, _ []*http.Request) error { return http.ErrUseLastResponse },
    }
    response, err := client.Do(req)
    if err != nil { receipt.Result = "TRANSPORT_HOLD"; receipt.TransportKind = transportKind(err); return receipt }
    defer response.Body.Close()
    receipt.Status = response.StatusCode
    receipt.ContentType = response.Header.Get("Content-Type")
    buf, err := io.ReadAll(io.LimitReader(response.Body, maxBody+1))
    if err != nil { receipt.Result = "TRANSPORT_HOLD"; receipt.TransportKind = transportKind(err); return receipt }
    receipt.Truncated = len(buf) > maxBody
    if receipt.Truncated { buf = buf[:maxBody] }
    receipt.BodyBytesSampled = len(buf)
    sum := sha256.Sum256(buf)
    receipt.SampleSHA256 = hex.EncodeToString(sum[:])
    receipt.Result = classify(receipt.Status, t.Kind, receipt.ContentType, buf, receipt.Truncated)
    if receipt.Result == "API_METADATA_OK" {
        var fields map[string]json.RawMessage
        if err := json.Unmarshal(buf, &fields); err == nil {
            for k := range fields { receipt.JSONTopKeys = append(receipt.JSONTopKeys,k) }
            sort.Strings(receipt.JSONTopKeys)
            if len(receipt.JSONTopKeys)>12 { receipt.JSONTopKeys=receipt.JSONTopKeys[:12] }
        }
    }
    return receipt
}

func main() {
    batch := flag.String("batch", "", "One of A, B, or C; one bounded request per listed provider")
    flag.Parse()
    if *batch != "A" && *batch != "B" && *batch != "C" {
        fmt.Fprintln(os.Stderr, "-batch must be A, B or C")
        os.Exit(2)
    }
    enc := json.NewEncoder(os.Stdout)
    enc.SetEscapeHTML(true)
    for _, t := range targets {
        if t.Lane == *batch {
            if err := enc.Encode(probe(t)); err != nil { os.Exit(1) }
        }
    }
}
