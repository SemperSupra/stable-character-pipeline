// Strict, bounded public GitHub compare-response decoding.
// First-failure preservation: duplicate keys, trailing values and truncated bodies
// must never become source-equivalence evidence or merge/closure authorization.
package main

import (
    "bytes"
    "encoding/json"
    "errors"
    "fmt"
    "io"
)

const compareJSONMaxBytes = 8 << 20
const compareJSONMaxDepth = 64

func walkUniqueCompareJSON(d *json.Decoder, depth int) error {
    if depth > compareJSONMaxDepth { return errors.New("COMPARE_JSON_TOO_DEEP") }
    tok, err := d.Token()
    if err != nil { return err }
    delim, isDelim := tok.(json.Delim)
    if !isDelim { return nil }
    switch delim {
    case '{':
        seen := make(map[string]struct{})
        for d.More() {
            rawKey, err := d.Token()
            if err != nil { return err }
            key, ok := rawKey.(string)
            if !ok { return errors.New("COMPARE_JSON_INVALID_KEY") }
            if _, duplicate := seen[key]; duplicate {
                return fmt.Errorf("COMPARE_JSON_DUPLICATE_KEY:%s", key)
            }
            seen[key] = struct{}{}
            if err := walkUniqueCompareJSON(d, depth+1); err != nil { return err }
        }
        end, err := d.Token()
        if err != nil { return err }
        if end != json.Delim('}') { return errors.New("COMPARE_JSON_UNCLOSED_OBJECT") }
    case '[':
        for d.More() {
            if err := walkUniqueCompareJSON(d, depth+1); err != nil { return err }
        }
        end, err := d.Token()
        if err != nil { return err }
        if end != json.Delim(']') { return errors.New("COMPARE_JSON_UNCLOSED_ARRAY") }
    default:
        return errors.New("COMPARE_JSON_UNEXPECTED_DELIMITER")
    }
    return nil
}

func decodeCompareJSON(r io.Reader) (CompareResponse, error) {
    raw, err := io.ReadAll(io.LimitReader(r, compareJSONMaxBytes+1))
    if err != nil { return CompareResponse{}, err }
    if len(raw) > compareJSONMaxBytes { return CompareResponse{}, errors.New("COMPARE_JSON_BODY_LIMIT") }
    trimmed := bytes.TrimSpace(raw)
    if len(trimmed)==0 || trimmed[0]!='{' { return CompareResponse{}, errors.New("COMPARE_JSON_EXPECT_OBJECT") }
    proof := json.NewDecoder(bytes.NewReader(raw))
    if err := walkUniqueCompareJSON(proof, 0); err != nil { return CompareResponse{}, err }
    if _, err := proof.Token(); !errors.Is(err, io.EOF) {
        if err == nil { return CompareResponse{}, errors.New("COMPARE_JSON_TRAILING_VALUE") }
        return CompareResponse{}, fmt.Errorf("COMPARE_JSON_TRAILING_INVALID: %w", err)
    }
    var out CompareResponse
    if err := json.NewDecoder(bytes.NewReader(raw)).Decode(&out); err != nil {
        return CompareResponse{}, err
    }
    return out, nil
}
