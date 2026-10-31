# SOURCE-SAFE synthetic-only runtime qualification. Protected R009 sources NOT admitted.
# Base manifest digest observed on exact public GHA 41215531781 (amd64).
# Debian apt and pip dependency bytes remain unlocked: NOT APPROVED FOR RELEASE.
FROM python:3.11-slim-bookworm@sha256:94a8fee35252d06ab75856f15f12c7bae67b10e8a6da93c7fded82b2610926cd
ENV PYTHONDONTWRITEBYTECODE=1 PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HOME=/tmp XDG_CONFIG_HOME=/tmp/config XDG_CACHE_HOME=/tmp/cache \
    LIBGL_ALWAYS_SOFTWARE=1 OMP_NUM_THREADS=2
RUN apt-get update -qq && \
    DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
      ffmpeg xvfb xauth libegl1 libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 \
      libxi6 libxkbcommon0 libxfixes3 libxxf86vm1 libasound2 libfontconfig1 \
      libgomp1 && \
    python -m pip install --no-cache-dir --only-binary=:all: "bpy==4.5.0" && \
    apt-get clean && rm -rf /var/lib/apt/lists/*
WORKDIR /src
USER 65532:65532
ENTRYPOINT ["python"]
CMD ["-c", "import bpy; print('SCP_CPU_BPY_VERSION',bpy.app.version_string)"]
