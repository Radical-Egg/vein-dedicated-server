## [0.2.7] - 2026-02-01

### 🐛 Bug Fixes

- Update build to account for Server.vns moving to ~/.config on the exp branch
- Update permissions and make backups more specific
- Fix permissions bug for backup dirs
- Add QueryPort and Game Port configs to Game.ini. These are already specified in the run command but adding them to 
Game.ini to follow the example in their [docs](https://ramjet.notion.site/Config-279f9ec29f178011a909f8ea9525936d).

### 📚 Documentation

- Update docker compose examples
## [0.2.6] - 2026-01-10

### 🐛 Bug Fixes

- Update VEIN_INSTALL_ARGS to conditionally use validate per steamcmd docs
- Add HTTPPort to game_ini_map to be optionally set

### 📚 Documentation

- Update docs to reflect minor changes to httport and workflow names
- Start using git-cliff
