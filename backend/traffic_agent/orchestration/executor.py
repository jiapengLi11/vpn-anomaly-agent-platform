"""Small deterministic executor for independent synchronous tool calls."""
from __future__ import annotations

import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, Iterable


ToolFunction = Callable[[], Any]


@dataclass(frozen=True)
class ToolCall:
    step_id: str
    tool_name: str
    function: ToolFunction
    failure_policy: str = "FAIL"

    def __post_init__(self) -> None:
        if self.failure_policy not in {"FAIL", "DEGRADE"}:
            raise ValueError(f"unsupported failure policy: {self.failure_policy}")


class ToolExecutionError(RuntimeError):
    def __init__(self, step_id: str, error_type: str) -> None:
        super().__init__(f"required tool failed: {step_id} ({error_type})")
        self.step_id = step_id
        self.error_type = error_type


class ParallelToolExecutor:
    def __init__(self, max_workers: int = 3) -> None:
        self.max_workers = max(1, max_workers)

    @staticmethod
    def _invoke(call: ToolCall) -> Dict[str, Any]:
        started_at = datetime.now(timezone.utc).isoformat()
        started = time.perf_counter()
        try:
            value = call.function()
            status, error_type = "SUCCEEDED", None
        except Exception as exc:
            value = None
            status, error_type = (
                "DEGRADED" if call.failure_policy == "DEGRADE" else "FAILED",
                type(exc).__name__,
            )
        return {
            "eventId": str(uuid.uuid4()), "stepId": call.step_id, "tool": call.tool_name,
            "status": status, "failurePolicy": call.failure_policy, "startedAt": started_at,
            "durationMs": round((time.perf_counter() - started) * 1000, 3),
            "errorType": error_type, "value": value,
        }

    def run_stage(self, stage_id: str, calls: Iterable[ToolCall]) -> Dict[str, Any]:
        ordered_calls = list(calls)
        if not ordered_calls:
            raise ValueError("parallel stage requires at least one tool")
        step_ids = [call.step_id for call in ordered_calls]
        if len(step_ids) != len(set(step_ids)):
            raise ValueError("parallel stage step IDs must be unique")
        stage_started_at = datetime.now(timezone.utc).isoformat()
        stage_started = time.perf_counter()
        with ThreadPoolExecutor(max_workers=min(self.max_workers, len(ordered_calls))) as pool:
            outcomes = [future.result() for future in [pool.submit(self._invoke, call) for call in ordered_calls]]
        duration_ms = round((time.perf_counter() - stage_started) * 1000, 3)
        serial_equivalent_ms = round(sum(item["durationMs"] for item in outcomes), 3)
        stage = {
            "stageId": stage_id,
            "executionMode": "PARALLEL" if len(ordered_calls) > 1 else "SERIAL",
            "startedAt": stage_started_at, "durationMs": duration_ms,
            "serialEquivalentMs": serial_equivalent_ms,
            "estimatedSavedMs": round(max(0.0, serial_equivalent_ms - duration_ms), 3),
            "tools": [{key: value for key, value in item.items() if key != "value"} for item in outcomes],
            "results": {item["stepId"]: item["value"] for item in outcomes},
        }
        required_failure = next((item for item in outcomes if item["status"] == "FAILED"), None)
        if required_failure:
            error = ToolExecutionError(required_failure["stepId"], required_failure["errorType"] or "UnknownError")
            error.stage = stage
            raise error
        return stage
