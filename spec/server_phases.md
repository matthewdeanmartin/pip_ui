# Server Integration Phases — pypiserver & devpi

This document describes the phased roadmap for integrating **pypiserver** and **devpi**
into pip-ui as first-class tool plugins, with particular focus on using them for
end-to-end testing of the full publish→install workflow.

______________________________________________________________________

## Phase 1 — Plugin Infrastructure *(current)*

**Goal**: Add pypiserver and devpi to the tool switcher with full UI panels.

### Deliverables

- `pip_ui/tools/pypiserver_tool.py` — ToolPlugin with command specs (run, update, version)
- `pip_ui/tools/devpi_tool.py` — ToolPlugin with command specs (use, login, upload, index, etc.)
- `pip_ui/ui/pypiserver_panel.py` — Panel with package list table + CommandForm
- `pip_ui/ui/devpi_panel.py` — Panel with index list table + CommandForm
- Registry wiring in `pip_ui/tools/__init__.py`
- Optional deps in `pyproject.toml`
- Unit tests for both plugins
- Panel smoke tests for both panels

### Acceptance criteria

- Both tools appear in the tool switcher (greyed out if not installed)
- Clicking an installed tool loads its panel with the data table and command form
- All existing tests continue to pass
- Mypy and ruff pass clean

______________________________________________________________________

## Phase 2 — Server Lifecycle Management

**Goal**: Start, stop, and monitor pypiserver/devpi from within the UI.

### Deliverables

- **Server manager module** (`pip_ui/server_manager.py`):
  - `start_server(plugin, args) → ServerHandle`
  - `stop_server(handle)`
  - `health_check(url) → bool`
  - Manage server subprocess lifecycle (background process, not blocking the UI)
- **Panel enhancements**:
  - Start/Stop toggle button with status indicator (green dot / red dot)
  - Health check polling (every 5s) to update status
  - Log viewer sub-tab showing server stdout/stderr
  - Port conflict detection (check if port is already in use)
- **Settings persistence**:
  - Save last-used server configuration per tool
  - Auto-start option in settings

### Design notes

Both pypiserver and devpi-server are long-running processes. Unlike other tools in
pip-ui that run a command and finish, server commands need special handling:

- The PipRunner is designed for one-shot commands. Server management needs its own
  subprocess tracking, separate from the runner's `is_running()` gate.
- Server processes should survive between command executions — the user might start
  a server, then switch to twine to upload, then back to pip to install.
- Graceful shutdown should use SIGTERM with a timeout, then SIGKILL.

______________________________________________________________________

## Phase 3 — End-to-End Tests with pypiserver

**Goal**: Prove the full publish→install cycle works against a real local index.

### Test scenario

```
1. Start pypiserver on a temp directory (port auto-assigned)
2. Build the project using `python -m build`
3. Upload via twine to the local pypiserver
4. Install the package from the local index via pip
5. Verify the installed package is importable
6. Tear down pypiserver
```

### Deliverables

- **`tests/conftest.py` fixture**: `pypiserver_instance` — starts a pypiserver on a
  random free port, yields the URL, and tears down on cleanup.
  ```python
  @pytest.fixture(scope="session")
  def pypiserver_instance(tmp_path_factory):
      packages_dir = tmp_path_factory.mktemp("packages")
      port = find_free_port()
      proc = subprocess.Popen(
          ["pypi-server", "run", "-p", str(port), str(packages_dir)],
          ...
      )
      wait_for_server(f"http://localhost:{port}")
      yield ServerInstance(url=f"http://localhost:{port}", packages_dir=packages_dir)
      proc.terminate()
      proc.wait(timeout=5)
  ```
- **`tests/test_e2e_pypiserver.py`**:
  - `test_build_and_upload_to_pypiserver` — builds sdist/wheel, uploads with twine
  - `test_install_from_pypiserver` — pip install from local index
  - `test_full_round_trip` — combined build → upload → install → import

### Markers

All tests in this file should be marked `@pytest.mark.integration` and
`@pytest.mark.slow` since they start real servers and run real subprocesses.

### CI considerations

- pypiserver must be installed in the test environment
- Tests need network-free localhost access only
- Port conflicts: use `find_free_port()` to avoid collisions with parallel tests

______________________________________________________________________

## Phase 4 — End-to-End Tests with devpi

**Goal**: Prove the full devpi workflow (server + client) works.

### Test scenario

```
1. Start devpi-server with --init on a temp serverdir
2. devpi use http://localhost:<port>
3. devpi login root --password=""
4. devpi index -c root/testindex volatile=True
5. devpi use root/testindex
6. devpi upload (build & upload current project)
7. pip install <package> --index-url http://localhost:<port>/root/testindex/+simple/
8. Verify import
9. Tear down devpi-server
```

### Deliverables

- **`tests/conftest.py` fixture**: `devpi_server_instance` — starts devpi-server
  with `--init`, creates a test index, yields connection info.
- **`tests/test_e2e_devpi.py`**:
  - `test_devpi_server_starts` — basic health check
  - `test_devpi_login_and_create_index` — client operations
  - `test_devpi_upload` — upload packages
  - `test_install_from_devpi` — pip install from devpi index
  - `test_devpi_full_round_trip` — combined workflow

### Markers

Same as Phase 3: `@pytest.mark.integration` and `@pytest.mark.slow`.

### CI considerations

- devpi-server and devpi-client must both be installed
- devpi-server `--init` creates state in a temp directory (use `tmp_path_factory`)
- devpi-server startup can be slow (~5s), so use generous timeouts
- Tests should be fully hermetic — no shared state between tests

______________________________________________________________________

## Phase 5 — Index Selector Integration

**Goal**: Let users wire up pypiserver/devpi as package sources for pip install.

### Deliverables

- **Auto-detect running servers**: When pypiserver or devpi is started from the UI,
  automatically add their URL to the Index Selector dropdown.
- **Persistent custom indexes**: The IndexSelector already supports custom repos via
  settings. Extend it to:
  - Show server status indicator next to locally-running indexes
  - Add a "Test Connection" button (HTTP GET to the simple index)
  - Group indexes by source (well-known, local servers, custom)
- **One-click workflow**: User starts pypiserver → switches to twine → uploads →
  switches to pip → the local index is already selected → installs

### Design notes

The IndexSelector at `pip_ui/ui/index_selector.py` already has the infrastructure
for custom repos. The main additions are:

1. A new `WELL_KNOWN_INDEXES` entry template for localhost servers
1. A callback from the server manager that auto-adds the running server's URL
1. Health status indication (green/red/grey dot) next to each index entry

______________________________________________________________________

## Phase 6 — CI Integration & Fixtures

**Goal**: Make server-based e2e tests reliable and fast in CI.

### Deliverables

- **Pytest plugin** (`tests/pytest_servers.py`):
  - Reusable fixtures for pypiserver and devpi
  - Automatic port assignment and collision avoidance
  - Cleanup guarantees (even on test failure/timeout)
  - Health-check polling with backoff
- **Tox/CI configuration**:
  - New tox environment: `[testenv:e2e-servers]` that installs pypiserver + devpi
  - Makefile target: `make test-servers`
  - GitHub Actions workflow that runs server e2e tests separately from unit tests
- **Docker option**: Optional Dockerfile for running server e2e tests in isolation
  ```yaml
  # .github/workflows/e2e-servers.yml
  - name: Run server e2e tests
    run: |
      uv sync --all-extras
      uv run pytest tests/test_e2e_pypiserver.py tests/test_e2e_devpi.py -m integration -v
  ```

### Performance targets

- pypiserver fixture setup: < 2s
- devpi-server fixture setup: < 10s (including --init)
- Full round-trip test (build + upload + install): < 30s each
- Total e2e-servers CI job: < 3 minutes

______________________________________________________________________

## Dependency Summary

| Phase | New runtime deps | New dev/test deps |
|-------|-----------------|-------------------|
| 1 | pypiserver ≥ 2.0 (optional) | — |
| 1 | devpi-server ≥ 6.0, devpi-client ≥ 7.0 (optional) | — |
| 3 | — | pypiserver (in test env) |
| 4 | — | devpi-server, devpi-client (in test env) |
| 6 | — | — (uses existing deps) |

______________________________________________________________________

## Timeline Estimate

| Phase | Effort | Dependencies |
|-------|--------|--------------|
| 1 | 1–2 days | None |
| 2 | 2–3 days | Phase 1 |
| 3 | 1–2 days | Phase 2 (or standalone with manual server start) |
| 4 | 2–3 days | Phase 2 |
| 5 | 1–2 days | Phase 2 |
| 6 | 1 day | Phases 3 & 4 |

Total: ~8–13 days of development effort.
