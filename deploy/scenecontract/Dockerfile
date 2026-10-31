# This research OCI image contains only original public synthetic test material.
# The Go binary is built in a pinned public standard GHA job, outside Docker.
FROM scratch
COPY --chmod=0555 scenecontract-bin /scenecontract
COPY --chmod=0444 sample.synthetic.json /fixtures/scene.json
USER 65532:65532
WORKDIR /
ENTRYPOINT ["/scenecontract"]
CMD ["validate", "/fixtures/scene.json"]
