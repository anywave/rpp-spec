"""Opt-in native wheel hook; ordinary builds stay pure Python."""
from __future__ import annotations

import os
import runpy
import tempfile
from pathlib import Path

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    def initialize(self, version, build_data):
        self._native_directory = None
        if self.target_name != "wheel" or os.environ.get("RPP_BUILD_HEDERA_NATIVE") != "true":
            return
        self._native_directory = tempfile.TemporaryDirectory(prefix="rpp-hedera-wheel-")
        builder = runpy.run_path(str(Path(self.root) / "scripts" / "build_hedera_native.py"))
        artifact = builder["build_native"](Path(self._native_directory.name))
        build_data["force_include"][str(artifact)] = "rpp/adapters/" + artifact.name
        build_data["pure_python"] = False
        build_data["infer_tag"] = True

    def finalize(self, version, build_data, artifact_path):
        if self._native_directory is not None:
            self._native_directory.cleanup()
