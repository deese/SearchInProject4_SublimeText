"""Base search engine for Search In Project."""

from __future__ import annotations

import os
import re
import shlex
import shutil
import subprocess
import traceback
from typing import List, Tuple


class Base:
    """Base search engine. Subclass to define new search engines."""

    SETTINGS = [
        "path_to_executable",
        "mandatory_options",
        "common_options",
    ]
    PARSER_RE = re.compile(r"^((?:\w:[\\|/]|\/)[^:]+):([\d:]+):(.*)")

    def __init__(self, settings) -> None:
        self.settings = settings
        for setting_name in self.SETTINGS:
            value = self.settings.get(self._full_settings_name(setting_name), "")
            setattr(self, setting_name, value)

        # Resolve executable path on Windows when explicitly configured.
        if (
            os.path.sep in self.path_to_executable
            and not os.path.exists(self.path_to_executable)
            and os.name == "nt"
        ):
            self._resolve_windows_path_to_executable()

    def dprint(self, msg: str) -> None:
        if self.settings.get("debug", False):
            print(msg)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def commonpath(self, paths: List[str]) -> str:
        """Return the longest common sub-path."""
        if not paths:
            raise ValueError("commonpath() arg is an empty sequence")
        return os.path.commonpath(paths)

    def run(self, query: str, folders: List[str]) -> List[Tuple[str, ...]]:
        """Run the search engine.

        Returns a list of tuples where the first element is the file path
        (optionally with row info separated by ``:``), and subsequent
        elements contain result metadata.
        """
        cleaned_folders = self._remove_subfolders(folders)
        arguments = self._arguments(query, cleaned_folders)
        cwd = self.commonpath(folders)

        self.dprint("[SearchInProject] folders: %s" % folders)
        self.dprint("[SearchInProject] cwd: %s" % cwd)
        self.dprint("[SearchInProject] cmd: %s" % " ".join(arguments))

        try:
            startupinfo = None
            if os.name == "nt":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            pipe = subprocess.Popen(
                arguments,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=cwd,
                startupinfo=startupinfo,
            )
        except OSError as exc:
            self.dprint("Found exception: {}".format(exc))
            self.dprint(traceback.format_exc())
            raise RuntimeError(
                "Could not find executable %s" % self.path_to_executable
            ) from exc

        output, error = pipe.communicate()

        self.dprint("[SearchInProject] returncode: %d" % pipe.returncode)
        self.dprint("[SearchInProject] raw output: %r" % output[:500])
        self.dprint("[SearchInProject] raw error: %r" % error[:200])

        if self._is_search_error(pipe.returncode, output, error):
            raise RuntimeError(self._sanitize_output(error))

        return self._parse_output(self._sanitize_output(output))

    # ------------------------------------------------------------------
    # Hooks for subclasses
    # ------------------------------------------------------------------

    def _arguments(self, query: str, folders: List[str]) -> List[str]:
        args: List[str] = [self.path_to_executable]
        args.extend(shlex.split(self.mandatory_options))
        args.extend(shlex.split(self.common_options))
        args.append(query)
        args.extend(folders)
        return args

    def _sanitize_output(self, output):
        if isinstance(output, bytes):
            output = output.decode("utf-8", "ignore")
        return output.replace("\r\n", "\n").replace("\r", "\n").strip()

    def _parse_output(self, output: str) -> List[Tuple[str, ...]]:
        lines = output.split("\n")
        line_parts = []
        for line in lines:
            if not line.strip():
                continue
            matches = Base.PARSER_RE.findall(line)
            if matches:
                line_parts.append(matches[0])
        return line_parts

    def _is_search_error(self, returncode: int, output, error) -> bool:
        return returncode != 0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _remove_subfolders(self, folders: List[str]) -> List[str]:
        unique: List[str] = []
        for folder in sorted(folders):
            if not unique or not folder.startswith(unique[-1]):
                unique.append(folder)
        return unique

    def _full_settings_name(self, name: str) -> str:
        return "search_in_project_%s_%s" % (self.__class__.__name__, name)

    def _resolve_windows_path_to_executable(self) -> None:
        resolved = shutil.which(self.path_to_executable)
        if resolved:
            self.path_to_executable = resolved
