#!/usr/bin/env python3
import sys
import os
import configparser
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bin"))

from update_config import game_ini_map
from update_config import write_config

def test_write_config():
    config = configparser.ConfigParser(strict=False)
    game_ini = tempfile.mkstemp()[1]
    
    write_config(config, game_ini, game_ini_map)

    assert(os.path.isfile(game_ini))
    assert(config.read(game_ini))

    for c in game_ini_map:
        assert(c in config)
        for key, expected in game_ini_map[c].items():
            key = key.lower()
 
            assert(config[c].get(key))
            assert(str(expected) == str(config[c].get(key)))
