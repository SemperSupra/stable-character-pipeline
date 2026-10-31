package scenejob

import (
 "errors"
 "fmt"
 "os"
 "path/filepath"
 "regexp"
)

var attemptDirectory = regexp.MustCompile(`^attempt-[0-9]{4}$`)
const writerLockName = ".r10-writer.lock"

// acquireExclusiveWriter is a process-independent fail-closed lease. An unclean
// process exit deliberately leaves the directory in place, requiring operator
// inspection of retained original attempt evidence rather than blind stealing.
func acquireExclusiveWriter(root string) (func(), error) {
 path := filepath.Join(root, writerLockName)
 if err := os.Mkdir(path, 0700); err != nil {
  if os.IsExist(err) { return nil, errors.New("ROOT_WRITER_BUSY_OR_RECOVERY_REQUIRED") }
  return nil, err
 }
 return func() { _ = os.Remove(path) }, nil
}

// recoverVerifiedComplete never promotes an attempt by name, cached state,
// marker file, or engine exit code. Only original result bytes plus every
// source/GLB/blend/H264 byte digest and unchanged scientific FAIL/UNKNOWN/HELD
// labels accepted by readResult may be used as a durable completion.
func recoverVerifiedComplete(root, revision string) (*Result, string, error) {
 entries, err := os.ReadDir(root)
 if err != nil { return nil, "", err }
 var completed *Result
 var selected string
 for _, entry := range entries {
  if !attemptDirectory.MatchString(entry.Name()) { continue }
  path := filepath.Join(root, entry.Name())
  info, err := os.Lstat(path)
  if err != nil || !info.IsDir() || info.Mode()&os.ModeSymlink != 0 {
   return nil, "", fmt.Errorf("UNSAFE_ATTEMPT_DIRECTORY: %s",entry.Name())
  }
  resultPath := filepath.Join(path, "result.json")
  _, err = os.Lstat(resultPath)
  if os.IsNotExist(err) { continue } // first failure: preserve, never promote
  if err != nil { return nil, "", err }
  receipt, err := readResult(path, revision)
  if err != nil {
   return nil, "", fmt.Errorf("DURABLE_RESULT_FAIL_CLOSED: %s: %w",entry.Name(),err)
  }
  if completed != nil {
   return nil, "", errors.New("AMBIGUOUS_MULTIPLE_VERIFIED_COMPLETIONS")
  }
  copyOfReceipt := receipt
  completed, selected = &copyOfReceipt, path
 }
 return completed, selected, nil
}
