#!/usr/bin/env bash
set -euo pipefail
work="$(mktemp -d)"
name="r009-oci-test-$$"
image_tag="r009-public-synthetic-oci:smoke"
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
printf '%s\n' '{"schema":"synthetic.review.v1","accepted":false}' > "$work/external-receipt.json"
receipt_hash="$(sha256sum "$work/external-receipt.json" | cut -d' ' -f1)"
source_hash="$(sha256sum "$work/build/index.html" | cut -d' ' -f1)"
port="$(python -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1",0)); print(s.getsockname()[1]); s.close()')"
for rep in 1 2; do
 cid="$(docker run -d --rm --name "$name" --read-only --cap-drop=ALL --security-opt=no-new-privileges --pids-limit=64 --memory=128m --cpus=1 -p "127.0.0.1:$port:8765" "$image_tag")"
 ok=0
 for attempt in $(seq 1 40); do
  if curl --silent --fail "http://127.0.0.1:$port/" > "$work/readback.html"; then ok=1; break; fi
  sleep .25
 done
 [[ "$ok" -eq 1 ]] || { echo "HTTP_COLD_START_FAILED $rep" >&2; exit 13; }
 [[ "$(sha256sum "$work/readback.html" | cut -d' ' -f1)" == "$source_hash" ]] || { echo 'BYTES_CHANGED' >&2; exit 14; }
 [[ "$(docker exec "$cid" id -u)" == 65532 ]] || { echo 'ROOT_PROCESS' >&2; exit 15; }
 if docker exec "$cid" touch /opt/synthetic/write-must-fail >/dev/null 2>&1; then echo 'WRITE_NOT_DENIED' >&2; exit 16; fi
 post_code="$(curl --silent --output /dev/null --write-out '%{http_code}' --data 'x=1' "http://127.0.0.1:$port/")"
 [[ "$post_code" == 501 ]] || { echo "UPLOAD_NOT_DENIED: $post_code" >&2; exit 17; }
 [[ "$(sha256sum "$work/external-receipt.json" | cut -d' ' -f1)" == "$receipt_hash" ]] || { echo 'EXTERNAL_DATA_CHANGED' >&2; exit 18; }
 docker stop "$cid" >/dev/null
 cid=""
done
export BASE_REF="$base_ref" IMAGE_ID="$image_id" SOURCE_HASH="$source_hash" RECEIPT_HASH="$receipt_hash"
python - <<'PY'
import json,os
r={"scope":"PUBLIC_SYNTHETIC_ONLY_NOT_PRIVATE_QA","base_ref":os.environ['BASE_REF'],"image_id":os.environ['IMAGE_ID'],"source_sha256":os.environ['SOURCE_HASH'],"external_receipt_sha256":os.environ['RECEIPT_HASH'],"cold_starts":2,"content_identical":True,"nonroot":True,"readonly":True,"post_rejected":True,"host_bind":"127.0.0.1","git_sha":os.getenv('GITHUB_SHA')}
open('synthetic-oci-evidence/receipt.json','w').write(json.dumps(r,indent=2,sort_keys=True))
print(json.dumps(r,sort_keys=True))
PY
