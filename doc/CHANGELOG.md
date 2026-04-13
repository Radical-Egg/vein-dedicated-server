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
