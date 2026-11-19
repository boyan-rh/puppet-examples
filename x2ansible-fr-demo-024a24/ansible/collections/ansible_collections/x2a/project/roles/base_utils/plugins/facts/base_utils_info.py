# GNU General Public License v3.0+
# (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)
"""Collect compatibility facts previously provided by the base_utils Facter fact."""

from __future__ import annotations

import os
import shutil


class FactModule:
    """Return installed utility package state and system uptime on Linux hosts."""

    def get_facts(self, module, collected_facts):
        if collected_facts.get("kernel") != "Linux":
            return {"ansible_facts": {"base_utils_info": {}}}

        package_info = {}
        for package_name in ("curl", "wget", "jq", "vim"):
            package_info[package_name] = self._package_installed(module, package_name)

        uptime_seconds = self._uptime_seconds()
        if uptime_seconds is not None:
            package_info["uptime_seconds"] = uptime_seconds

        return {"ansible_facts": {"base_utils_info": package_info}}

    @staticmethod
    def _package_installed(module, package_name):
        if shutil.which("rpm"):
            rc, _, _ = module.run_command(["rpm", "-q", package_name])
            if rc == 0:
                return True
        if shutil.which("dpkg-query"):
            rc, _, _ = module.run_command(
                ["dpkg-query", "--show", "--showformat=${db:Status-Status}", package_name]
            )
            return rc == 0
        return False

    @staticmethod
    def _uptime_seconds():
        try:
            with open("/proc/uptime", encoding="utf-8") as uptime_file:
                return int(float(uptime_file.read().split()[0]))
        except (OSError, ValueError, IndexError):
            return None
