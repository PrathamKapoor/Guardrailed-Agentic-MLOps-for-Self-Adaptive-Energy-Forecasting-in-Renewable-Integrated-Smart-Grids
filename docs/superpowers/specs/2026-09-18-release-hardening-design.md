# Release Hardening Design

## Goal

Make the repository releasable as a reproducible offline research-evidence
application, while keeping optional local research experimentation outside the
production API boundary.

## Scope

This design addresses release provenance, deployment correctness, API safety,
non-mutating verification, CI coverage, and documentation consistency. It does
not rerun experiments, alter frozen Phase 19 evidence, change model selection,
or publish external services or container images.

## Architecture

### Production evidence API

The default FastAPI application will expose only the current read-only evidence
and advisory endpoints. The write-capable research dataset upload and local
experiment routes will be excluded unless an explicit research-console mode is
enabled. That mode will require a configured bearer token and will retain its
existing isolated `artifacts/research_ui/` storage boundary.

Production configuration will fail closed: production mode requires both an
explicit CORS allow-list and an API token. Development remains usable locally
with the documented defaults.

### Deployment package

The Docker image will contain every file read during API startup and normal
read-only request handling: frozen research tables, model registries, required
protocol/configuration files, processed dataset identity input, and necessary
audit/agent evidence. A container smoke test will build the image and probe the
health and evidence routes without creating research artifacts.

### Verification and CI

The recursive pytest call embedded in hackathon readiness will be replaced by
separate explicit verification commands. Tests that exercise dashboard building
will use a temporary output location or verify a pure builder interface so
repository dashboard snapshots are never rewritten during tests. CI will run
backend tests, frontend checks, frozen-artifact integrity verification, static
release consistency checks, and the container smoke test.

### Release provenance

A release-manifest generator will collect version, commit hash when available,
dependency-lock hashes, frozen artifact hashes, and the current test collection
count. It will never invent a commit hash: a repository with no commit will be
reported as unreleasable by the release check. Documentation will use generated
or single-source values rather than hard-coded conflicting test totals.

## Safety Constraints

- Never modify `artifacts/research_tables/final_*`, frozen protocols, model
  registries, Phase 19 reports, or final-test results.
- No lifecycle-mutation endpoint may be introduced.
- Research-console operations remain advisory/research-only and cannot mutate
  lifecycle state, policy, models, or frozen evidence.
- Production API authentication and CORS are mandatory, not advisory.
- Verification commands must not write to repository artifacts or dashboard
  snapshots.

## Test Strategy

Each changed behavior will follow test-first development. New tests cover:

1. production startup refusal without token or explicit origins;
2. absence of research write paths from default OpenAPI and their controlled
   availability in research-console mode;
3. Docker runtime completeness derived from the API dependency list;
4. release-manifest provenance and no-commit rejection;
5. checksum sidecar resolution and integrity verification;
6. non-recursive hackathon readiness and no dashboard-output mutation.

The final verification set includes targeted Python tests, the full backend
suite, frontend type-check/tests/build, release verification, and Docker smoke
testing where Docker is available.

## External Follow-ups

The local repository cannot publish a container image, deploy a hosted demo,
configure production credentials, obtain external peer review, or improve the
scientific evidence by collecting new datasets. The release guide will make
these required post-repository steps explicit.
