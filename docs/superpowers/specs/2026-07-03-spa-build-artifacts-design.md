# SPA Build Artifacts Design

## Goal

Stop tracking `web/static/spa` build outputs in git while keeping the TradingAgents web UI deployable through Docker and explicit to operate in local source checkouts.

## Scope

This design covers the repository and runtime changes needed to treat the Vue SPA bundle as a generated artifact rather than checked-in source.

In scope:

- Remove `web/static/spa` from git-tracked package data and source control expectations.
- Ignore generated SPA outputs in local development so they do not block `git pull`.
- Preserve Docker image builds that compile the frontend and copy the bundle into the runtime image.
- Preserve a clear local failure mode when the frontend bundle is missing.
- Update tests and docs to reflect the new build contract.

Out of scope:

- Auto-building frontend assets during `uvicorn web.app:app` startup.
- Rewriting git history to purge previously committed bundle files.
- Changing the frontend toolchain, output path, or Vite build semantics.

## Current-State Constraints

The repo currently mixes source and generated SPA outputs:

- `web/app.py` mounts `web/static` directly for runtime asset serving.
- `web/routes.py` already contains a clear 503 error when `web/static/spa/index.html` is missing.
- `Dockerfile` builds the Vue app in a Node stage and copies the bundle into `web/static/spa` for the final image.
- `pyproject.toml` currently includes `web/static/spa/**/*` in Python package data, which makes the repository behave as if generated assets are part of the package source.
- The checked-in bundle files can conflict with local generated files during `git pull`, which is the failure mode that triggered this change.

These constraints mean the lowest-risk design is to keep runtime asset serving and Docker bundling behavior, but stop treating generated SPA files as versioned source files.

## Requirements

### 1. Generated SPA files are not tracked

The repository must ignore generated SPA outputs under `web/static/spa/` so local builds do not appear as untracked or conflicting source files.

### 2. Docker remains the production build path

The Docker build must continue to:

- install frontend dependencies
- build the SPA
- copy the build output into `web/static/spa`

This keeps containerized deployment self-contained.

### 3. Local source checkouts require an explicit frontend build

Running the backend directly from a source checkout must require the operator to build the SPA first with:

```bash
npm --prefix frontend run build
```

If the bundle is absent, the app must fail clearly rather than silently serving a broken UI or building assets implicitly.

### 4. Python packaging stops declaring the SPA bundle as source package data

The Python package metadata must no longer claim `web/static/spa/**/*` as tracked package content from the repo source tree.

### 5. Tests reflect the new contract

Tests must verify:

- the app serves the SPA when assets exist
- the app returns the existing explicit error when assets are missing
- Docker still performs the frontend build-and-copy workflow
- the repo configuration ignores generated SPA outputs

## Proposed Design

### A. Source-Control Contract

Add `web/static/spa/` to `.gitignore` and remove the tracked build outputs from the repository index.

This is a one-time repository cleanup, not a history rewrite. Existing commits will still contain historical bundles, but the current tree will no longer track them.

### B. Runtime Contract

Keep the current FastAPI static mounting and SPA fallback behavior unchanged.

The existing `_serve_spa_index()` 503 response is already the right behavior for missing local assets because it:

- fails early
- tells the operator exactly what to run
- avoids hidden build steps during app startup

No runtime auto-build hook should be added.

### C. Packaging Contract

Update `pyproject.toml` so Python package data still includes stable static files such as the manifest and icons, but no longer includes `web/static/spa/**/*`.

This makes the package metadata match the intended development model: the SPA bundle is generated during deploy/build workflows, not carried as repo source.

### D. Documentation Contract

Update the Web UI setup docs so they explicitly distinguish:

- Docker usage, where the image builds the SPA automatically
- local source usage, where the developer must run `npm --prefix frontend run build` before launching `uvicorn`
- Vite dev-server usage, where `npm run dev:docker` remains the hot-reload path for frontend iteration

### E. Test Contract

Adjust tests to stop asserting that SPA bundle files are package-data source content.

Replace that expectation with repo-level checks that align to the new model:

- `.gitignore` ignores `web/static/spa/`
- the backend emits the explicit missing-build error when the bundle is absent
- Docker still contains the frontend build pipeline

## Error Handling

The failure mode for a missing local SPA bundle should remain explicit and synchronous:

- return HTTP 503
- keep the current error message instructing the operator to run `npm --prefix frontend run build`

This is preferable to runtime compilation because startup-time builds would introduce hidden Node/npm dependencies into the Python runtime path and make failures slower and less predictable.

## Testing Strategy

The change should be verified with targeted tests and one source-control check:

- backend tests for SPA shell serving when assets exist
- backend tests for the missing-bundle 503 path
- static repository tests for Docker frontend build steps
- static repository tests for `.gitignore` coverage and removal of `web/static/spa/**/*` from package-data declarations

## Migration Notes

After this change lands, developers who run the backend directly from source will need to do one of the following:

- run `npm --prefix frontend run build` before starting `uvicorn`
- use the documented Vite development flow for frontend work
- use Docker, which continues to build the bundle automatically

This is an intentional tradeoff: slightly more explicit local setup in exchange for removing generated-file churn and `git pull` conflicts from the repository.
