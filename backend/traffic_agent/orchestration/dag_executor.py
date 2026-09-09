"""Execute a compiled tool plan one dependency stage at a time."""
from __future__ import annotations

from typing import Any, Callable, Dict, Mapping

from .executor import ParallelToolExecutor, ToolCall


DagToolFunction = Callable[[Dict[str, Any]], Any]


class DagExecutor:
    def __init__(self, max_workers: int = 4) -> None:
        self.stage_executor = ParallelToolExecutor(max_workers=max_workers)

    def execute(self, plan: Mapping[str, Any], tools: Mapping[str, DagToolFunction], *,
                input_data: Dict[str, Any] | None = None) -> Dict[str, Any]:
        if plan.get("status") != "COMPILED" or not plan.get("executable"):
            raise ValueError("DAG executor requires an executable compiled plan")
        steps = {step["stepId"]: dict(step) for step in plan.get("steps", [])}
        results, statuses, public_stages = {}, {}, []
        for stage_spec in plan.get("stages", []):
            calls, skipped = [], []
            for step_id in stage_spec.get("stepIds", []):
                step = steps.get(step_id)
                if step is None:
                    raise ValueError(f"compiled stage references unknown step: {step_id}")
                dependencies = list(step.get("dependsOn", []))
                dependency_statuses = {dependency: statuses.get(dependency) for dependency in dependencies}
                if any(status is None for status in dependency_statuses.values()):
                    raise ValueError(f"compiled step references dependencies that have not completed: {step_id}")
                if step.get("dependencyMode", "ALL_SUCCESS") == "ALL_SUCCESS" and any(
                        status != "SUCCEEDED" for status in dependency_statuses.values()):
                    statuses[step_id], results[step_id] = "SKIPPED_DEPENDENCY", None
                    skipped.append({"stepId": step_id, "tool": step["tool"],
                                    "status": "SKIPPED_DEPENDENCY",
                                    "dependencyStatuses": dependency_statuses})
                    continue
                function = tools.get(step["tool"])
                if function is None:
                    raise ValueError(f"no executable registered for tool: {step['tool']}")

                def invoke(current_step=step, current_function=function):
                    return current_function({
                        "input": dict(input_data or {}),
                        "dependencies": {dependency: results.get(dependency)
                                         for dependency in current_step.get("dependsOn", [])},
                        "step": dict(current_step),
                    })

                calls.append(ToolCall(step_id, step["tool"], invoke, step.get("failurePolicy", "FAIL")))
            if calls:
                outcome = self.stage_executor.run_stage(stage_spec["stageId"], calls)
                results.update(outcome["results"])
                statuses.update({item["stepId"]: item["status"] for item in outcome["tools"]})
                public_stage = {key: value for key, value in outcome.items() if key != "results"}
                public_stage["tools"].extend(skipped)
                public_stages.append(public_stage)
            else:
                public_stages.append({"stageId": stage_spec["stageId"], "executionMode": "SKIPPED",
                                      "durationMs": 0.0, "serialEquivalentMs": 0.0,
                                      "estimatedSavedMs": 0.0, "tools": skipped})
        degraded = any(status in {"DEGRADED", "SKIPPED_DEPENDENCY"} for status in statuses.values())
        return {
            "planVersion": plan.get("planVersion"), "status": "DEGRADED" if degraded else "SUCCESS",
            "stepStatuses": statuses, "results": results,
            "audit": {"resultPayloadsIncluded": False, "stages": public_stages,
                      "completedStepCount": sum(status == "SUCCEEDED" for status in statuses.values()),
                      "degradedStepCount": sum(status == "DEGRADED" for status in statuses.values()),
                      "skippedStepCount": sum(status == "SKIPPED_DEPENDENCY" for status in statuses.values())},
        }
