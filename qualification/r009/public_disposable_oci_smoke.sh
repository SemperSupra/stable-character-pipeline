#!/usr/bin/env bash
set -euo pipefail
# PUBLIC SYNTHETIC ONLY: producer uploads external receipt, consumer is a fresh GHA job.
phase="$(printenv R009_PHASE || printf producer)"
case "$phase" in producer|consumer) ;; *) echo INVALID_PHASE >&2; exit 2;; esac
work="$(mktemp -d)"
name="r009-oci-test-$phase-$"
image_tag="r009-public-synthetic-oci:$phase"
mkdir -p "$work/build" synthetic-oci-evidence
cid=""
cleanup() {
 if [[ -n "$cid" ]]; then docker stop "$cid" >/dev/null 2>&1 || true; fi
 docker rm -f "$name" >/dev/null 2>&1 || true
 docker image rm -f "$image_tag" >/dev/null 2>&1 || true
 rm -rf "$work"
}
trap cleanup EXIT
printf '%s\n' '<!doctype html><html lang="en"><title>PUBLIC SYNTHETIC</title><h1>Disposable QA venue</h1></html>' > "$work/build/index.html"
cat > "$work/build/Containerfile" <<'EOF'
ARG PYTHON_BASE
FROM $PYTHON_BASE
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /opt/synthetic
COPY --chown=65532:65532 index.html .
USER 65532:65532
EXPOSE 8765
CMD ["python", "-m", "http.server", "8765", "--bind", "0.0.0.0", "--directory", "/opt/synthetic"]
EOF
base_tag=python:3.12.12-slim-bookworm
docker pull "$base_tag"
base_ref="$(docker image inspect --format '{{index .RepoDigests 0}}' "$base_tag")"
[[ "$base_ref" == *@sha256:* ]] || { echo 'BASE_DIGEST_NOT_RESOLVED' >&2; exit 12; }
docker build --build-arg "PYTHON_BASE=$base_ref" -f "$work/build/Containerfile" -t "$image_tag" "$work/build"
image_id="$(docker image inspect --format '{{.Id}}' "$image_tag")"
# Positive contrast: root can write /tmp without --read-only.
docker run --rm --user 0 --network none --entrypoint /bin/sh "$image_tag" -ec 'touch /tmp/r009-public-writable-control && test -e /tmp/r009-public-writable-control' >/dev/null
if [[ "$phase" == consumer ]]; then
 export BASE_REF="$base_ref" SOURCE_HASH="$(sha256sum "$work/build/index.html" | cut -d' ' -f1)"
 export RECEIPT_HASH="$(sha256sum synthetic-oci-evidence/external-receipt.json | cut -d' ' -f1)"
 python3 - synthetic-oci-evidence/producer-receipt.json <<'PY'
import json,os,sys
from pathlib import Path
p=json.loads(Path(sys.argv[1]).read_text(encoding='utf8'))
for key,env in [('base_ref','BASE_REF'),('source_sha256','SOURCE_HASH'),('external_receipt_sha256','RECEIPT_HASH'),('git_sha','GITHUB_SHA'),('run_id','GITHUB_RUN_ID')]:
 if p.get(key)!=os.getenv(env): raise SystemExit('CROSS_WORKER_MISMATCH_'+key.upper())
if not p.get('same_worker_two_container_starts') or not p.get('job_id') or p['job_id']==os.getenv('GITHUB_JOB'):
 raise SystemExit('NOT_AN_INDEPENDENT_WORKER_JOB')
print('CROSS_WORKER_RECEIPT_AND_PINS_VERIFIED')
PY
fi
if [[ "$phase" == producer ]]; then
 printf '%s\n' '{"schema":"synthetic.review.v1","accepted":false,"scope":"PUBLIC_ONLY"}' > synthetic-oci-evidence/external-receipt.json
else
 [[ -s synthetic-oci-evidence/producer-receipt.json && -s synthetic-oci-evidence/external-receipt.json ]] || { echo EXTERNAL_RECEIPT_NOT_DOWNLOADED >&2; exit 21; }
fi
receipt_hash="$(sha256sum "synthetic-oci-evidence/external-receipt.json" | cut -d' ' -f1)"
source_hash="$(sha256sum "$work/build/index.html" | cut -d' ' -f1)"
port="$(python -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1",0)); print(s.getsockname()[1]); s.close()')"
starts=2
if [[ "$phase" == consumer ]]; then starts=1; fi
for rep in $(seq 1 "$starts"); do
 cid="$(docker run -d --rm --name "$name" --read-only --cap-drop=ALL --security-opt=no-new-privileges --pids-limit=64 --memory=128m --cpus=1 -p "127.0.0.1:$port:8765" "$image_tag")"
 ok=0
 for attempt in $(seq 1 40); do
  if curl --silent --fail "http://127.0.0.1:$port/" > "$work/readback.html"; then ok=1; break; fi
  sleep .25
 done
 [[ "$ok" -eq 1 ]] || { echo "HTTP_COLD_START_FAILED $rep" >&2; exit 13; }
 [[ "$(sha256sum "$work/readback.html" | cut -d' ' -f1)" == "$source_hash" ]] || { echo 'BYTES_CHANGED' >&2; exit 14; }
 [[ "$(docker exec "$cid" id -u)" == 65532 ]] || { echo 'ROOT_PROCESS' >&2; exit 15; }
 [[ "$(docker inspect --format '{{.HostConfig.ReadonlyRootfs}}' "$cid")" == true ]] || { echo 'READONLY_FLAG_MISSING' >&2; exit 23; }
 # Negative is discriminating because root could write /tmp in the positive control.
 if docker exec --user 0 "$cid" touch /tmp/r009-public-ro-negative >/dev/null 2>&1; then
  echo 'ROOT_CAN_WRITE_READONLY_ROOTFS' >&2; exit 24
 fi
 if docker exec "$cid" touch /opt/synthetic/write-must-fail >/dev/null 2>&1; then echo 'WRITE_NOT_DENIED' >&2; exit 16; fi
 post_code="$(curl --silent --output /dev/null --write-out '%{http_code}' --data 'x=1' "http://127.0.0.1:$port/")"
 [[ "$post_code" == 501 ]] || { echo "UPLOAD_NOT_DENIED: $post_code" >&2; exit 17; }
 [[ "$(sha256sum "synthetic-oci-evidence/external-receipt.json" | cut -d' ' -f1)" == "$receipt_hash" ]] || { echo 'EXTERNAL_DATA_CHANGED' >&2; exit 18; }
 docker stop "$cid" >/dev/null
 cid=""
done
export BASE_REF="$base_ref" IMAGE_ID="$image_id" SOURCE_HASH="$source_hash" RECEIPT_HASH="$receipt_hash" PHASE="$phase" STARTS="$starts"
python3 - <<'PY'
import json,os
from pathlib import Path
phase=os.environ['PHASE']
r={
 "scope":"PUBLIC_SYNTHETIC_ONLY_NOT_PRIVATE_QA",
 "phase":phase, "git_sha":os.getenv('GITHUB_SHA'),"run_id":os.getenv('GITHUB_RUN_ID'),"job_id":os.getenv('GITHUB_JOB'),
 "base_ref":os.environ['BASE_REF'],"image_id":os.environ['IMAGE_ID'],
 "source_sha256":os.environ['SOURCE_HASH'],"external_receipt_sha256":os.environ['RECEIPT_HASH'],
 "cold_starts":int(os.environ['STARTS']), "same_worker_two_container_starts":phase=='producer',
 "fresh_worker_rebuild_verified":phase=='consumer',
 "cross_worker_external_receipt_reimport_verified":phase=='consumer',
 "read_only_rootfs_inspected":True,"root_write_negative":True,"root_write_positive_control":True,
 "nonroot":True,"post_rejected":True,"host_bind":"127.0.0.1",
 "private_app_accepted":False,
}
name="producer-receipt.json" if phase=="producer" else "consumer-receipt.json"
Path("synthetic-oci-evidence",name).write_text(json.dumps(r,indent=2,sort_keys=True)+"\n",encoding="utf8")
print(json.dumps(r,sort_keys=True))
PY
