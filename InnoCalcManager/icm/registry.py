"""Registry of calculation modules hosted by InnoCalc Manager.

A module is any Python package that exposes the headless contract described in
``docs/MODULE-SPECIFICATION.md``.  Modules are declared here by folder and entry
point only; nothing about a module's inputs, calculations or presentation is
known to the manager, which is what lets a design package be developed on its
own and dropped in without touching the front end.

Adding a module is one entry in :data:`SOURCES` - no other file changes.
"""

from __future__ import annotations

import importlib
import sys
import traceback
from pathlib import Path
from typing import Any

from . import SUITE_ROOT

# The discipline tree the New calculation chooser is grouped by. Many more
# modules are coming, so the branches are declared once here and a module simply
# names the one it belongs to.
CATEGORIES: list[str] = [
    "Load Calculations", "Timber", "Insitu Concrete", "Precast Concrete",
    "Temporary Works", "Steel", "Glass", "Fibres", "Composite", "Foundations",
    "Retaining wall", "Analysis", "General",
]

# folder relative to the suite root -> importable entry point, and the branch of
# the tree the module is filed under when it does not declare its own.
SOURCES: list[dict[str, str]] = [
    {"folder": "SteelMemberDesign", "entry": "smd.headless", "category": "Steel"},
    {"folder": "ConcreteColumnDesign", "entry": "ccd.headless", "category": "Insitu Concrete"},
    {"folder": "CalculationPad", "entry": "cpd.headless", "category": "General"},
]

REQUIRED = ("descriptor", "schema", "defaults", "compute", "render", "summarise", "identity")
OPTIONAL = ("exchange", "accepts", "apply_exchange", "run_action", "validate")


class Module:
    """One loaded calculation module."""

    def __init__(self, source: dict[str, str], adapter: Any, folder: Path):
        self.entry = source["entry"]
        self.folder = folder
        self.adapter = adapter
        self.descriptor = dict(adapter.descriptor())
        self.descriptor.setdefault("id", self.entry)
        # A module may declare its own branch; otherwise the registry files it.
        self.descriptor.setdefault("category", source.get("category", "General"))
        self.id = self.descriptor["id"]

    def has(self, name: str) -> bool:
        return callable(getattr(self.adapter, name, None))

    def call(self, name: str, *args, **kwargs) -> Any:
        function = getattr(self.adapter, name, None)
        if not callable(function):
            raise ValueError(f"{self.descriptor['name']} does not support '{name}'")
        return function(*args, **kwargs)

    def public(self) -> dict[str, Any]:
        return {**self.descriptor,
                "supports": [name for name in REQUIRED + OPTIONAL if self.has(name)]}


class Registry:
    """Loads every declared module once and reports any that fail to load."""

    def __init__(self, sources: list[dict[str, str]] | None = None,
                 root: Path | None = None):
        self.root = Path(root or SUITE_ROOT)
        self.sources = list(sources if sources is not None else SOURCES)
        self.modules: dict[str, Module] = {}
        self.problems: list[dict[str, str]] = []
        self.load()

    def load(self) -> None:
        self.modules, self.problems = {}, []
        for source in self.sources:
            folder = self.root / source["folder"]
            if not folder.is_dir():
                self.problems.append({"entry": source["entry"],
                                      "error": f"folder not found: {folder}"})
                continue
            if str(folder) not in sys.path:
                sys.path.insert(0, str(folder))
            try:
                adapter = importlib.import_module(source["entry"])
                missing = [name for name in REQUIRED if not callable(getattr(adapter, name, None))]
                if missing:
                    raise AttributeError("missing contract functions: " + ", ".join(missing))
                module = Module(source, adapter, folder)
            except Exception as exc:  # noqa: BLE001 - one bad module must not stop the app
                self.problems.append({"entry": source["entry"], "error": str(exc),
                                      "detail": traceback.format_exc(limit=3)})
                continue
            self.modules[module.id] = module

    def get(self, module_id: Any) -> Module:
        module = self.modules.get(str(module_id or "").strip())
        if not module:
            known = ", ".join(sorted(self.modules)) or "none"
            raise ValueError(f"Unknown calculation module '{module_id}'. Loaded: {known}")
        return module

    def catalogue(self) -> list[dict[str, Any]]:
        return sorted((module.public() for module in self.modules.values()),
                      key=lambda item: str(item.get("name", "")))

    def folder_for(self, module_id: Any) -> str:
        return str(self.get(module_id).descriptor.get("folder") or module_id)
