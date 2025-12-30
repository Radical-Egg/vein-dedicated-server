[0.2.4]
* Fix bug in bin/healthcheck.py to cast VEIN_QUERY_PORT and VEIN_GAME_PORT to int
* Fixed chmod path in backup.Dockerfile
* update backup script to use trap for graceful shutdown

[0.2.3]

* Added support to use S3 to backup Game.ini and Server.vns
* Update heartbeat script (healthcheck.py) to check both game and query port
* Update doc examples
