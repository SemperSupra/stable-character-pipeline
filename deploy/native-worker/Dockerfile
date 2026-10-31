# SOURCE-SAFE synthetic-only runtime qualification. Protected R009 sources NOT admitted.
# Research image base tag is mutable until a separately qualified digest is pinned;
# therefore this image is expressly NOT APPROVED FOR RELEASE/PUBLICATION.
FROM python:3.11-slim-bookworm
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
