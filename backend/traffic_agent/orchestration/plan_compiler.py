"""Compile bounded tool proposals into deterministic executable DAG plans."""
from __future__ import annotations

from collections import deque
from typing import Any, Dict, Iterable, Mapping


PLAN_VERSION = "tool-dag-plan-v1"
ALLOWED_FAILURE_POLICIES = {"FAIL", "DEGRADE"}
ALLOWED_DEPENDENCY_MODES = {"ALL_SUCCESS", "ALL_DONE"}
ALLOWED_SIDE_EFFECTS = {"NONE", "EXTERNAL_BILLABLE", "STATE_MUTATION"}
PROPOSAL_FIELDS = {"name", "tool"}


class PlanCompilationError(ValueError):
    def __init__(self, code: str, message: str, *, details: Dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.details = details or {}


class PlanCompiler:
    """Treat the model as a proposer and the server registry as the authority."""

    def __init__(self, registry: Mapping[str, Mapping[str, Any]], max_steps: int = 50) -> None:
        if max_steps < 1:
            raise ValueError("max_steps must be positive")
        self.registry = {str(name): dict(spec) for name, spec in registry.items()}
        self.max_steps = max_steps
        self._registry_order = {name: index for index, name in enumerate(self.registry)}
        self._validate_registry()

    def _validate_registry(self) -> None:
        for name, spec in self.registry.items():
            requires = spec.get("requires", [])
            if not isinstance(requires, list) or any(not isinstance(item, str) for item in requires):
                raise PlanCompilationError("INVALID_REGISTRY", f"invalid dependencies for {name}")
            unknown = [dependency for dependency in requires if dependency not in self.registry]
            if unknown:
                raise PlanCompilationError("INVALID_REGISTRY", f"unknown registry dependency for {name}",
                                           details={"tool": name, "unknownDependencies": unknown})
            if spec.get("failurePolicy", "FAIL") not in ALLOWED_FAILURE_POLICIES:
                raise PlanCompilationError("INVALID_REGISTRY", f"invalid failure policy for {name}")
            if spec.get("dependencyMode", "ALL_SUCCESS") not in ALLOWED_DEPENDENCY_MODES:
                raise PlanCompilationError("INVALID_REGISTRY", f"invalid dependency mode for {name}")
            if spec.get("sideEffect", "NONE") not in ALLOWED_SIDE_EFFECTS:
                raise PlanCompilationError("INVALID_REGISTRY", f"invalid side effect for {name}")

    @staticmethod
    def _parse_proposal(proposal: Iterable[str | Mapping[str, Any]]) -> tuple[list[str], list[Dict[str, Any]]]:
        names, ignored = [], []
        for item in proposal:
            if isinstance(item, str):
                name = item
            elif isinstance(item, Mapping):
                name = str(item.get("name") or item.get("tool") or "")
                ignored_fields = sorted(str(key) for key in item if key not in PROPOSAL_FIELDS)
                if ignored_fields:
                    ignored.append({"tool": name[:100], "fields": ignored_fields[:20]})
            else:
                raise PlanCompilationError("INVALID_PROPOSAL", "tool proposal entries must be names or objects")
            name = name.strip()[:100]
            if not name:
                raise PlanCompilationError("INVALID_PROPOSAL", "tool proposal contains a blank name")
            if name in names:
                raise PlanCompilationError("DUPLICATE_TOOL", f"tool requested more than once: {name}",
                                           details={"tool": name})
            names.append(name)
        if not names:
            raise PlanCompilationError("EMPTY_PROPOSAL", "tool proposal must not be empty")
        return names, ignored

    def _dependency_closure(self, requested: list[str]) -> set[str]:
        selected: set[str] = set()

        def visit(name: str) -> None:
            if name not in self.registry:
                raise PlanCompilationError("UNKNOWN_TOOL", f"tool is not registered: {name}",
                                           details={"tool": name})
            if name in selected:
                return
            selected.add(name)
            if len(selected) > self.max_steps:
                raise PlanCompilationError("PLAN_TOO_LARGE", f"compiled plan exceeds {self.max_steps} steps",
                                           details={"maxSteps": self.max_steps})
            for dependency in self.registry[name].get("requires", []):
                visit(dependency)

        for name in requested:
            visit(name)
        return selected

    def _ordered(self, names: Iterable[str]) -> list[str]:
        return sorted(names, key=lambda name: (self._registry_order.get(name, 10**9), name))

    def _topological_waves(self, selected: set[str]) -> list[list[str]]:
        dependencies = {name: set(self.registry[name].get("requires", [])) & selected for name in selected}
        dependents = {name: set() for name in selected}
        for name, requires in dependencies.items():
            for dependency in requires:
                dependents[dependency].add(name)
        indegree = {name: len(requires) for name, requires in dependencies.items()}
        ready = deque(self._ordered(name for name, count in indegree.items() if count == 0))
        waves, visited = [], 0
        while ready:
            wave = list(ready)
            ready.clear()
            waves.append(wave)
            visited += len(wave)
            next_ready = []
            for name in wave:
                for dependent in dependents[name]:
                    indegree[dependent] -= 1
                    if indegree[dependent] == 0:
                        next_ready.append(dependent)
            ready.extend(self._ordered(next_ready))
        if visited != len(selected):
            cyclic = self._ordered(name for name, count in indegree.items() if count > 0)
            raise PlanCompilationError("DEPENDENCY_CYCLE", "tool registry dependency cycle detected",
                                       details={"tools": cyclic})
        return waves

    def _split_wave(self, wave: list[str]) -> list[list[str]]:
        remaining, groups = list(wave), []
        while remaining:
            first = remaining.pop(0)
            first_spec = self.registry[first]
            if first_spec.get("sideEffect", "NONE") != "NONE":
                groups.append([first])
                continue
            group = [first]
            used_keys = {first_spec.get("concurrencyKey")} - {None, ""}
            deferred = []
            for name in remaining:
                spec = self.registry[name]
                key = spec.get("concurrencyKey")
                if spec.get("sideEffect", "NONE") != "NONE" or (key and key in used_keys):
                    deferred.append(name)
                else:
                    group.append(name)
                    if key:
                        used_keys.add(key)
            groups.append(group)
            remaining = deferred
        return groups

    def compile(self, *, intent: str, proposal: Iterable[str | Mapping[str, Any]],
                granted_permissions: Iterable[str]) -> Dict[str, Any]:
        requested, ignored_fields = self._parse_proposal(proposal)
        selected = self._dependency_closure(requested)
        normalized_intent = str(intent or "").upper()
        unsupported = [name for name in requested
                       if normalized_intent not in self.registry[name].get("supportedIntents", [])]
        if unsupported:
            raise PlanCompilationError("INTENT_NOT_SUPPORTED", "tool does not support the resolved intent",
                                       details={"intent": normalized_intent, "tools": unsupported})
        granted = set(granted_permissions)
        missing = {name: sorted(set(self.registry[name].get("requiredPermissions", [])) - granted)
                   for name in self._ordered(selected)}
        missing = {name: values for name, values in missing.items() if values}
        if missing:
            raise PlanCompilationError("PERMISSION_DENIED", "principal lacks required permissions",
                                       details={"missingPermissions": missing})

        waves = self._topological_waves(selected)
        names = [name for wave in waves for name in wave]
        step_ids = {name: f"step-{index:03d}" for index, name in enumerate(names, start=1)}
        steps, stages = [], []
        for wave in waves:
            for group in self._split_wave(wave):
                stages.append({"stageId": f"stage-{len(stages) + 1:03d}",
                               "executionMode": "PARALLEL" if len(group) > 1 else "SERIAL",
                               "stepIds": [step_ids[name] for name in group]})
                for name in group:
                    spec = self.registry[name]
                    requires = list(spec.get("requires", []))
                    steps.append({
                        "stepId": step_ids[name], "tool": name,
                        "toolVersion": str(spec.get("version", "1.0")),
                        "dependsOn": [step_ids[dependency] for dependency in requires],
                        "dependsOnTools": requires,
                        "dependencyMode": spec.get("dependencyMode", "ALL_SUCCESS"),
                        "failurePolicy": spec.get("failurePolicy", "FAIL"),
                        "readOnly": bool(spec.get("readOnly", False)),
                        "idempotent": bool(spec.get("idempotent", False)),
                        "sideEffect": spec.get("sideEffect", "NONE"),
                        "concurrencyKey": spec.get("concurrencyKey"),
                    })
        steps.sort(key=lambda step: int(step["stepId"].split("-")[-1]))
        return {
            "planVersion": PLAN_VERSION, "status": "COMPILED", "intent": normalized_intent,
            "executable": True, "requestedTools": requested,
            "dependencyExpandedTools": [name for name in names if name not in requested],
            "steps": steps, "stages": stages,
            "audit": {"authority": "SERVER_TOOL_REGISTRY", "proposalMetadataTrusted": False,
                      "ignoredProposalFields": ignored_fields, "stepCount": len(steps),
                      "stageCount": len(stages),
                      "parallelStageCount": sum(stage["executionMode"] == "PARALLEL" for stage in stages)},
        }
