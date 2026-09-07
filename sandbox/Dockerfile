# Disposable container the Critic node uses to validate a candidate patch.
# Kept minimal on purpose: the target repo brings its own toolchain via its
# own CI config; this image just needs git + the language runtimes to `git apply`
# and re-run the originally failing command.
FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace
