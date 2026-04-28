#!/usr/bin/env python3
"""Line-preserving helpers for Unreal Engine ini files.

The standard ``configparser`` module is useful for reading the final result,
but it cannot safely round-trip Unreal files because they may contain repeated
sections, repeated keys, comments, and hand-edited formatting. This module
keeps the file as lines and edits only the values managed by the container
configuration script.
"""

import os
import re


SECTION_HEADER_RE = re.compile(r"^\s*\[([^\]]+)\]\s*(?:[;#].*)?$")
OPTION_RE = re.compile(r"^\s*([^=:#;\s][^=:#]*?)\s*[:=]")


class MissingSectionError(Exception):
    """Raised when an edit requires an existing section that is not present."""

    pass


class UnrealIniDocument:
    """Line-oriented editor for Unreal ini files.

    Unreal ini files may contain repeated keys, repeated sections, and comments.
    Generic ini parsers cannot safely round-trip that shape, so this class only
    edits the keys it owns and leaves every unrelated line intact.
    """

    def __init__(self, path, lines=None):
        """Create a document for ``path`` with optional preloaded ``lines``."""
        self.path = path
        self.lines = list(lines or [])

    @classmethod
    def load(cls, path):
        """Load an ini file if it exists, otherwise return an empty document."""
        if not os.path.isfile(path):
            return cls(path)

        with open(path, "r") as config_file:
            return cls(path, config_file.readlines())

    def save(self):
        """Write the current document lines, creating the parent directory."""
        config_dir = os.path.dirname(self.path)
        if config_dir:
            os.makedirs(config_dir, exist_ok=True)

        with open(self.path, "w") as config_file:
            config_file.writelines(self.lines)

    def has_section(self, section):
        """Return whether ``section`` appears anywhere in the document."""
        return any(section_name(line) == section for line in self.lines)

    def ensure_section(self, section):
        """Append ``section`` when it is not already present."""
        if not self.has_section(section):
            self._append_section(section)

    def set_options(self, section, options):
        """Set scalar options in ``section`` while preserving unrelated lines.

        Unreal configs can repeat a section. The first matching section keeps
        the managed values; later duplicate sections have those same managed
        values removed so the resulting file has one authoritative value while
        preserving unrelated user settings.
        """
        managed_options = {
            option.lower(): (option, str(value))
            for option, value in options.items()
        }
        spans = self._section_spans(section)

        if not spans:
            self._append_section(section, options)
            return

        lines = self.lines
        for span_index, (start, end) in reversed(list(enumerate(spans))):
            body = lines[start + 1 : end]
            if span_index == 0:
                body = replace_options(body, managed_options)
            else:
                body = drop_options(body, managed_options)

            lines = replace_line_range(lines, start + 1, end, body)

        self.lines = lines

    def set_repeated_option_block(self, section, option, values, create_section=False):
        """Replace the managed repeated-key block for ``option`` in ``section``.

        Repeated options such as Steam IDs are wrapped in explicit start/end
        markers. On later runs the marked block can be replaced cleanly, while
        stale unmarked copies of the same option are removed from the target
        section.
        """
        if create_section:
            self.ensure_section(section)

        bounds = self._first_section_bounds(section)
        if bounds is None:
            raise MissingSectionError(section)

        section_start, section_end = bounds
        block_start, block_end = self._managed_block_bounds(
            section_start,
            section_end,
            option,
        )

        block_lines = managed_block_lines(option, values)

        if (
            block_start is not None
            and block_end is not None
            and block_start < block_end
        ):
            self.lines = replace_line_range(
                self.lines,
                block_start,
                block_end + 1,
                block_lines,
            )
            return

        preserved_body = []
        body = self.lines[section_start + 1 : section_end]
        start_marker = managed_start_marker(option).strip()
        end_marker = managed_end_marker(option).strip()
        for line in body:
            if line.strip() in {start_marker, end_marker}:
                continue

            current_option = option_name(line)
            if current_option and current_option.lower() == option.lower():
                continue
            preserved_body.append(line)

        self.lines = replace_line_range(
            self.lines,
            section_start + 1,
            section_end,
            block_lines + preserved_body,
        )

    def remove_repeated_option(self, section, option):
        """Remove both marked and unmarked copies of ``option`` from ``section``."""
        self.lines = remove_section_option(self.lines, section, option)

    def _append_section(self, section, options=None):
        """Append a new section and optional scalar options to the document."""
        ensure_final_newline(self.lines)

        if self.lines and self.lines[-1].strip():
            self.lines.append("\n")

        self.lines.append(f"[{section}]\n")

        if options:
            for option, value in options.items():
                self.lines.append(f"{option} = {value}\n")

    def _first_section_bounds(self, section):
        """Return ``(start, end)`` for the first matching section, if present."""
        spans = self._section_spans(section)
        if not spans:
            return None

        return spans[0]

    def _section_spans(self, section):
        """Return all ``(start, end)`` ranges for repeated ``section`` headers."""
        spans = []
        current_name = None
        current_start = None

        for index, line in enumerate(self.lines):
            next_name = section_name(line)
            if next_name is None:
                continue

            if current_name == section:
                spans.append((current_start, index))

            current_name = next_name
            current_start = index

        if current_name == section:
            spans.append((current_start, len(self.lines)))

        return spans

    def _managed_block_bounds(self, section_start, section_end, option):
        """Find the start and end line indexes for an existing managed block."""
        start_marker = managed_start_marker(option).strip()
        end_marker = managed_end_marker(option).strip()
        block_start = None
        block_end = None

        for index in range(section_start + 1, section_end):
            stripped = self.lines[index].strip()
            if stripped == start_marker:
                block_start = index
            elif stripped == end_marker:
                block_end = index

        return block_start, block_end


def section_name(line):
    """Return the section name from an ini header line, or ``None``."""
    match = SECTION_HEADER_RE.match(line)
    if match:
        return match.group(1)

    return None


def option_name(line):
    """Return the option name from an assignment line, or ``None``."""
    match = OPTION_RE.match(line)
    if match:
        return match.group(1).strip()

    return None


def ensure_final_newline(lines):
    """Mutate ``lines`` so the final line ends with a newline."""
    if lines and not lines[-1].endswith("\n"):
        lines[-1] = lines[-1] + "\n"


def replace_line_range(lines, start, end, replacement):
    """Return ``lines`` with ``[start:end]`` replaced by ``replacement``."""
    prefix = lines[:start]
    if replacement:
        # Keep inserted content on its own line when replacing a body that was
        # previously attached to a section header without a trailing newline.
        ensure_final_newline(prefix)

    return prefix + replacement + lines[end:]


def replace_options(lines, managed_options):
    """Replace managed scalar options in a section body.

    Existing managed options are emitted once using the canonical casing from
    ``managed_options``. Missing managed options are appended after unrelated
    lines, preserving comments and custom repeated values.
    """
    output = []
    emitted_options = set()

    for line in lines:
        current_option = option_name(line)
        option_key = current_option.lower() if current_option else None

        if option_key in managed_options:
            if option_key not in emitted_options:
                option, value = managed_options[option_key]
                output.append(f"{option} = {value}\n")
                emitted_options.add(option_key)
            continue

        output.append(line)

    ensure_final_newline(output)
    for option_key, (option, value) in managed_options.items():
        if option_key not in emitted_options:
            output.append(f"{option} = {value}\n")

    return output


def drop_options(lines, managed_options):
    """Remove managed scalar options from a duplicate section body."""
    output = []

    for line in lines:
        current_option = option_name(line)
        option_key = current_option.lower() if current_option else None

        if option_key in managed_options:
            continue

        output.append(line)

    return output


def managed_start_marker(option):
    """Return the marker that starts a managed repeated-option block."""
    return f"##Start:{option}:injections##\n"


def managed_end_marker(option):
    """Return the marker that ends a managed repeated-option block."""
    return f"##End:{option}:injections##\n"


def managed_block_lines(option, values):
    """Build a marked repeated-option block for ``values``."""
    if isinstance(values, str):
        values = values.splitlines()

    repeated_lines = []
    for value in values:
        value = str(value).rstrip("\r\n").strip('"')
        repeated_lines.append(f"{option}={value}\n")

    return [
        managed_start_marker(option),
        *repeated_lines,
        managed_end_marker(option),
    ]


def remove_section_option(lines, section, option):
    """Remove a repeated option from a section without disturbing other lines."""
    output = []
    option_key = option.lower()
    start_marker = managed_start_marker(option).strip()
    end_marker = managed_end_marker(option).strip()
    in_target_section = False
    skipping_marker_block = False

    for line in lines:
        stripped = line.strip()
        current_section = section_name(line)

        if skipping_marker_block:
            if stripped == end_marker:
                skipping_marker_block = False
                continue
            if current_section is None:
                continue

            # A new section before the end marker means the old block was
            # malformed; stop skipping so unrelated sections are preserved.
            skipping_marker_block = False

        if current_section is not None:
            in_target_section = current_section == section
            output.append(line)
            continue

        if in_target_section and stripped == start_marker:
            skipping_marker_block = True
            continue

        if in_target_section and stripped == end_marker:
            continue

        current_option = option_name(line)
        current_option_key = current_option.lower() if current_option else None

        if in_target_section and current_option_key == option_key:
            continue

        output.append(line)

    return output
