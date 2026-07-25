# AGENTS.md

Guidance for AI coding agents working in this repository.

## What this repo is

A demo/reference monorepo for a container build-and-promote pipeline. The application code is deliberately trivial: `app1/` and `app2/` are byte-identical single-route Flask apps (only the response string differs). The substance of the repo is in `.github/workflows/` — the CI is the artifact under development, not the apps.

## Commands

There is no test suite, linter, or formatter configured. Verification is done by building and running the images.

```bash
# Build an app image (build context is the app directory, not the repo root)
docker build -t app1 app1/

# Run it (Flask listens on 5000)
docker run --rm -p 5000:5000 app1

# Run an app directly without Docker
pip install -r app1/requirements.txt && python app1/api/app.py
```

## Image tag conventions

Tags are structured, and downstream tooling parses them. The format is `<env>-<7-char sha>-<commit unix timestamp>`, e.g. `dev-a1b2c3d-1740000000`. The trailing timestamp exists so Flux `ImagePolicy` can sort numerically — see the Flux image-update guide linked in `docker-build-push.yml`. Both the build workflow (which generates `dev-` tags) and `promote-images.yml` (which regex-matches and rewrites the env prefix) depend on this shape; changing it breaks promotion.

## Promotion model

`promote-images.yml` is `workflow_dispatch`-only and promotes by **retagging an existing image**, never rebuilding: it finds the newest `<from_env>-*` tag via the GitHub Packages REST API, pulls it, retags it with the `<to_env>` prefix, and pushes. Environments flow dev → test → prod.

The list of promotable images lives in one place: `on.workflow_dispatch.inputs.image.options` in `promote-images.yml`. When `image: all` is selected, the job reads that same list back out of its own workflow file with `yq` and uses it as the job matrix. **Adding a new app means adding it to that `options` list** — there is no other registry of apps. Note the list already contains `app3`, which has no directory in the repo; selecting it will fail at the registry lookup.

## Working with the workflows

- Every `uses:` is pinned to a full commit SHA with the human-readable version in a trailing comment (`# pin@v4.2.2`). Preserve this pattern; update both the SHA and the comment together.
- Base images in Dockerfiles are pinned by digest, with the readable tag kept as a comment above (`# FROM python:3.13.2-slim-bookworm`). Same rule: update both lines together.
- Builds are reproducible-mode: `SOURCE_DATE_EPOCH` is set from the commit timestamp, and provenance/SBOM attestations are enabled. Multi-platform (`linux/amd64,linux/arm64`) via QEMU.
- `docker-build-push.yml` builds both apps as a matrix regardless of what changed, but its `paths:` filters are asymmetric — the `push` trigger only lists `app1/**` paths and the `pull_request` trigger only lists `app2/**`. That is almost certainly unintended; if you touch those triggers, be aware changes to `app2` currently do not trigger a build on `main`.
- Pushes only happen on non-PR events (`push: ${{ github.event_name != 'pull_request' }}`), so PR builds validate the Dockerfile without publishing.
- The Dockerfiles carry commented-out scaffolding for private-registry Poetry installs via BuildKit secrets. Keep it unless asked otherwise — it documents the pattern for real apps derived from these.

## Claude Code workflows

`claude.yml` (tag mode, `@claude` mentions) and `claude-code-review.yml` (automatic PR review) are both pinned to `--model claude-opus-5 --effort xhigh`. Both files contain lengthy comments explaining *why* their permissions and tool allowlists are set the way they are — in particular that `claude-code-review.yml` must pass an explicit `--allowed-tools` list containing an `mcp__github_inline_comment__` entry or the job silently posts nothing, and that the code-review plugin is intentionally not used there. Read those comments before editing either file.
