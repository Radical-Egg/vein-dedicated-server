#!/usr/bin/env python3

import os
import re


SECTION_HEADER_RE = re.compile(r"^\s*\[([^\]]+)\]\s*(?:[;#].*)?$")
OPTION_RE = re.compile(r"^\s*([^=:#;\s][^=:#]*?)\s*[:=]")


class MissingSectionError(Exception):
    pass


class UnrealIniDocument:
    """Line-oriented editor for Unreal ini files.

    Unreal ini files may contain repeated keys, repeated sections, and comments.
    Generic ini parsers cannot safely round-trip that shape, so this class only
    edits the keys it owns and leaves every unrelated line intact.
    """

    def __init__(self, path, lines=None):
        self.path = path
        self.lines = list(lines or [])

    @classmethod
    def load(cls, path):
        if not os.path.isfile(path):
            return cls(path)

        with open(path, "r") as config_file:
            return cls(path, config_file.readlines())

    def save(self):
        config_dir = os.path.dirname(self.path)
        if config_dir:
            os.makedirs(config_dir, exist_ok=True)

        with open(self.path, "w") as config_file:
            config_file.writelines(self.lines)

    def has_section(self, section):
        return any(section_name(line) == section for line in self.lines)

    def ensure_section(self, section):
        if not self.has_section(section):
            self._append_section(section)

    def set_options(self, section, options):
        """Set scalar options in a section while preserving unrelated lines."""
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
        """Replace a managed repeated-key block inside section."""
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

        if block_start is not None and block_end is not None:
            self.lines = replace_line_range(
                self.lines,
                block_start,
                block_end + 1,
                block_lines,
            )
            return

        preserved_body = []
        body = self.lines[section_start + 1 : section_end]
        for line in body:
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
        self.lines = remove_section_option(self.lines, section, option)

    def _append_section(self, section, options=None):
        ensure_final_newline(self.lines)

        if self.lines and self.lines[-1].strip():
            self.lines.append("\n")

        self.lines.append(f"[{section}]\n")

        if options:
            for option, value in options.items():
                self.lines.append(f"{option} = {value}\n")

    def _first_section_bounds(self, section):
        spans = self._section_spans(section)
        if not spans:
            return None

        return spans[0]

    def _section_spans(self, section):
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
    match = SECTION_HEADER_RE.match(line)
    if match:
        return match.group(1)

    return None


def option_name(line):
    match = OPTION_RE.match(line)
    if match:
        return match.group(1).strip()

    return None


def ensure_final_newline(lines):
    if lines and not lines[-1].endswith("\n"):
        lines[-1] = lines[-1] + "\n"


def replace_line_range(lines, start, end, replacement):
    prefix = lines[:start]
    if replacement:
        ensure_final_newline(prefix)

    return prefix + replacement + lines[end:]


def replace_options(lines, managed_options):
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
    output = []

    for line in lines:
        current_option = option_name(line)
        option_key = current_option.lower() if current_option else None

        if option_key in managed_options:
            continue

        output.append(line)

    return output


def managed_start_marker(option):
    return f"##Start:{option}:injections##\n"


def managed_end_marker(option):
    return f"##End:{option}:injections##\n"


def managed_block_lines(option, values):
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

            skipping_marker_block = False

        if current_section is not None:
            in_target_section = current_section == section
            output.append(line)
            continue

        if in_target_section and stripped == start_marker:
            skipping_marker_block = True
            continue

        current_option = option_name(line)
        current_option_key = current_option.lower() if current_option else None

        if in_target_section and current_option_key == option_key:
            continue

        output.append(line)

    return output
