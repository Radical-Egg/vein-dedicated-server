#!/usr/bin/env python3
"""Regression tests for the line-preserving Unreal ini editor."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "bin"))

from unreal_ini import MissingSectionError
from unreal_ini import UnrealIniDocument
from unreal_ini import managed_block_lines
from unreal_ini import option_name
from unreal_ini import section_name


def test_section_and_option_parsers_accept_unreal_spacing_and_comments():
    """Section and option detection allows Unreal-style whitespace and comments."""
    assert section_name("  [URL]  ; trailing comment\n") == "URL"
    assert section_name("NotASection = true\n") is None
    assert option_name("  Port : 7777\n") == "Port"
    assert option_name("; Port = 7777\n") is None


def test_set_options_collapses_managed_values_across_duplicate_sections():
    """Managed scalar values are authoritative in only the first matching section."""
    document = UnrealIniDocument(
        "Game.ini",
        [
            "[URL]\n",
            "port = 27015\n",
            "Port = 27016\n",
            "Custom = keep\n",
            "\n",
            "[Other]\n",
            "Port = unrelated\n",
            "\n",
            "[URL]\n",
            "Port = 27017\n",
            "CustomTwo = keep\n",
        ],
    )

    document.set_options("URL", {"Port": 7777})

    assert document.lines == [
        "[URL]\n",
        "Port = 7777\n",
        "Custom = keep\n",
        "\n",
        "[Other]\n",
        "Port = unrelated\n",
        "\n",
        "[URL]\n",
        "CustomTwo = keep\n",
    ]


def test_set_options_appends_missing_values_after_existing_section_body():
    """Missing managed values are added without moving unrelated section content."""
    document = UnrealIniDocument(
        "Game.ini",
        [
            "[/Script/Vein.VeinGameSession]\n",
            "; keep this comment\n",
            "ServerName = Existing\n",
        ],
    )

    document.set_options(
        "/Script/Vein.VeinGameSession",
        {
            "ServerName": "Updated",
            "Password": "secret",
        },
    )

    assert document.lines == [
        "[/Script/Vein.VeinGameSession]\n",
        "; keep this comment\n",
        "ServerName = Updated\n",
        "Password = secret\n",
    ]


def test_set_repeated_option_block_replaces_existing_marker_block_once():
    """Existing managed repeated-key blocks are replaced in place."""
    document = UnrealIniDocument(
        "Game.ini",
        [
            "[/Script/Vein.VeinGameSession]\n",
            "; keep before block\n",
            "##Start:AdminSteamIDs:injections##\n",
            "AdminSteamIDs=111\n",
            "##End:AdminSteamIDs:injections##\n",
            "ServerName = keep\n",
        ],
    )

    document.set_repeated_option_block(
        "/Script/Vein.VeinGameSession",
        "AdminSteamIDs",
        ["222", "333"],
    )

    assert document.lines == [
        "[/Script/Vein.VeinGameSession]\n",
        "; keep before block\n",
        "##Start:AdminSteamIDs:injections##\n",
        "AdminSteamIDs=222\n",
        "AdminSteamIDs=333\n",
        "##End:AdminSteamIDs:injections##\n",
        "ServerName = keep\n",
    ]


def test_set_repeated_option_block_removes_unmarked_stale_values_before_insert():
    """Unmarked stale repeated keys are removed before adding the managed block."""
    document = UnrealIniDocument(
        "Game.ini",
        [
            "[/Script/Vein.VeinGameSession]\n",
            "AdminSteamIDs=111\n",
            "AdminSteamIDs = 222\n",
            "ServerName = keep\n",
        ],
    )

    document.set_repeated_option_block(
        "/Script/Vein.VeinGameSession",
        "AdminSteamIDs",
        ["333"],
    )

    assert document.lines == [
        "[/Script/Vein.VeinGameSession]\n",
        "##Start:AdminSteamIDs:injections##\n",
        "AdminSteamIDs=333\n",
        "##End:AdminSteamIDs:injections##\n",
        "ServerName = keep\n",
    ]


def test_set_repeated_option_block_repairs_partial_marker_block():
    """Partial managed blocks are repaired without preserving orphan markers."""
    document = UnrealIniDocument(
        "Game.ini",
        [
            "[/Script/Vein.VeinGameSession]\n",
            "##Start:AdminSteamIDs:injections##\n",
            "AdminSteamIDs=111\n",
            "ServerName = keep\n",
        ],
    )

    document.set_repeated_option_block(
        "/Script/Vein.VeinGameSession",
        "AdminSteamIDs",
        ["222"],
    )

    assert document.lines == [
        "[/Script/Vein.VeinGameSession]\n",
        "##Start:AdminSteamIDs:injections##\n",
        "AdminSteamIDs=222\n",
        "##End:AdminSteamIDs:injections##\n",
        "ServerName = keep\n",
    ]


def test_set_repeated_option_block_requires_existing_section_by_default():
    """Callers must opt in when they want missing sections created."""
    document = UnrealIniDocument("Game.ini", [])

    with pytest.raises(MissingSectionError):
        document.set_repeated_option_block(
            "/Script/Vein.VeinGameSession",
            "AdminSteamIDs",
            ["111"],
        )


def test_remove_repeated_option_preserves_next_section_after_malformed_block():
    """Malformed blocks do not cause later sections to be dropped."""
    document = UnrealIniDocument(
        "Game.ini",
        [
            "[/Script/Vein.VeinGameSession]\n",
            "##Start:AdminSteamIDs:injections##\n",
            "AdminSteamIDs=111\n",
            "[Custom.Section]\n",
            "Foo = keep\n",
        ],
    )

    document.remove_repeated_option(
        "/Script/Vein.VeinGameSession",
        "AdminSteamIDs",
    )

    assert document.lines == [
        "[/Script/Vein.VeinGameSession]\n",
        "[Custom.Section]\n",
        "Foo = keep\n",
    ]


def test_remove_repeated_option_drops_orphan_end_marker():
    """A stray end marker for a disabled option is removed with that option."""
    document = UnrealIniDocument(
        "Game.ini",
        [
            "[/Script/Vein.VeinGameSession]\n",
            "AdminSteamIDs=111\n",
            "##End:AdminSteamIDs:injections##\n",
            "ServerName = keep\n",
        ],
    )

    document.remove_repeated_option(
        "/Script/Vein.VeinGameSession",
        "AdminSteamIDs",
    )

    assert document.lines == [
        "[/Script/Vein.VeinGameSession]\n",
        "ServerName = keep\n",
    ]


def test_managed_block_lines_accepts_quoted_multiline_values():
    """Quoted multiline values are normalized into repeated-key lines."""
    assert managed_block_lines("AdminSteamIDs", '"111"\n"222"\n') == [
        "##Start:AdminSteamIDs:injections##\n",
        "AdminSteamIDs=111\n",
        "AdminSteamIDs=222\n",
        "##End:AdminSteamIDs:injections##\n",
    ]
