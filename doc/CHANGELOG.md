## [0.3.0] - 2026-04-26

### 🐛 Bug Fixes

- Rework `Game.ini` and `Engine.ini` updates around a new line-preserving Unreal ini editor (`bin/unreal_ini.py`) instead of writing files back through `ConfigParser`
- Preserve user-managed comments, duplicate keys, duplicate sections, custom repeated values, existing section ordering, percent characters, and files that do not end with a final newline
- Update scalar config writes so managed options are matched case-insensitively, emitted once with canonical casing, and removed from duplicate sections while unrelated values remain untouched
- Replace repeated-key injection handling for `AdminSteamIDs`, `SuperAdminSteamIDs`, and `WhitelistedPlayers` with managed start/end marker blocks that can be updated idempotently
- Fix disabled repeated-key values so stale marked blocks and stale unmarked keys are removed without rewriting unrelated ini content
- Repair partial or orphaned repeated-key injection markers when updating or removing managed values
- Fix `run_injections` to respect the provided config path instead of always writing to the default `Game.ini`
- Allow injection sections to be created directly when needed, removing the old retry/repair loop while keeping the `max_attempts` argument for compatibility
- Reload the supplied `ConfigParser` objects from disk after config writes and injection updates so callers see the final saved file state
- Keep HTTP API configuration opt-in by writing `HTTPPort = False` unless `VEIN_SERVER_ENABLE_HTTP_API` is enabled, including support for `1` as a truthy flag value

### 📚 Documentation

- Document the new Unreal ini editing helpers with module, class, method, and helper docstrings
- Document `update_config.py` so the environment-to-ini mapping, repeated-key injection path, and HTTP API default behavior are easier to maintain
- Document the config regression tests with helper and per-test docstrings that explain which behavior each test protects
- Update this changelog entry with detailed release notes for the 0.3.0 config-writing rework

### ⚙️ Miscellaneous Tasks

- Copy `bin/unreal_ini.py` into the Docker image so `update_config` can import the new helper at runtime
- Add `.dockerignore` to reduce Docker build context size by excluding repository metadata, local data, tests, docs, cache files, and other non-runtime assets
- Add `requirements-test.txt` with `pytest` as the test dependency entry point
- Add a lightweight GitHub Actions CI workflow for shell syntax checks, Python compile checks, and pytest
- Expand `Dependabot` to track GitHub Actions updates
- Add regression coverage for environment overrides, environment boolean parsing, config path handling, explicit `False` config values, lowercase managed keys, percent values, parentless relative paths, final-newline handling, line preservation, injection add/update/remove/repair behavior, legacy helper behavior, healthcheck response parsing, and A2S challenge retries

## [0.2.10]

### 🐛 Bug Fixes

- Recover from SteamCMD app state `0x6` by deleting only the affected app manifest and retrying once
- Improve healthcheck validation by parsing the `A2S_INFO` query response

## [0.2.9] - 2026-03-29

### 🐛 Bug Fixes

- Remove + from multiorder configs, the + prefix no longer works

### 📚 Documentation

- Update README and add some basic tests
- Update README and add some basic tests (#12)
- Update README

### ⚙️ Miscellaneous Tasks

- Add Dependabot configuration file (#13)
## [0.2.8] - 2026-02-02

### 🚀 Features

- Add support for HTTP API server

### 📚 Documentation

- Update CHANGELOG
## [0.2.7] - 2026-02-02

### 🐛 Bug Fixes

- Update build to account for Server.vns moving to ~/.config on the exp branch
- Update permissions and make backups more specific
- Fix permissions bug for backup dirs
- Fix readme typo
- More README fixes
- Add debug statements and add missing Game.ini configs
- Do not push attestations to registry to cleanup images in ghcr for now

### 📚 Documentation

- Update docker compose examples
- Update changelog
## [0.2.6] - 2026-01-10

### 🐛 Bug Fixes

- Update VEIN_INSTALL_ARGS to conditionally use validate per steamcmd docs
- Add HTTPPort to game_ini_map to be optionally set

### 📚 Documentation

- Update docs to reflect minor changes to httport and workflow names
- Start using git-cliff
