"""Coordinate guarded plan preview, local execution and bounded run events."""
from __future__ import annotations

import copy
import threading
import uuid
from collections import OrderedDict
from datetime import datetime, timezone

from ..knowledge import search
from ..orchestration import DagExecutor, PlanCompilationError, PlanCompiler
from .intent_router import resolve_intent
from .planning_catalog import PLAN_TOOL_CATALOG

COORDINATOR_VERSION = "agent-run-coordinator-public-v1"
PREVIEW_PERMISSIONS = {"knowledge:read", "analysis:review", "ai:invoke"}
LOCAL_RUN_TOOLS = {"knowledge.search"}
TERMINAL_STATUSES = {"SUCCESS", "DEGRADED", "FAILED", "CANCELLED", "PREVIEW_ONLY",
                     "CLARIFICATION_REQUIRED", "POLICY_REJECTED", "NO_REGISTERED_TOOLS"}


def _now():
    return datetime.now(timezone.utc).isoformat()


def _knowledge_tool(context):
    query = str(context.get("input", {}).get("message") or "")[:500]
    return search(query, limit=5)


class AgentRunCoordinator:
    """Process-local runner for reproducible demos, not a distributed scheduler."""

    def __init__(self, registry=None, tool_functions=None, max_runs=50, max_events_per_run=100):
        if max_runs < 1 or max_events_per_run < 1:
            raise ValueError("run and event limits must be positive")
        self.registry = dict(registry or PLAN_TOOL_CATALOG)
        self.compiler = PlanCompiler(self.registry)
        self.executor = DagExecutor(max_workers=4)
        self.tool_functions = dict(tool_functions or {"knowledge.search": _knowledge_tool})
        self.max_runs, self.max_events_per_run = max_runs, max_events_per_run
        self._runs, self._lock = OrderedDict(), threading.RLock()

    def preview(self, message, context=None, requested_tools=None):
        intent = resolve_intent(message, context=context or {})
        response = {
            "coordinatorVersion": COORDINATOR_VERSION,
            "status": "CLARIFICATION_REQUIRED" if intent["status"] != "RESOLVED" else "DISCOVERED",
            "intent": intent, "plan": None,
            "runPolicy": {"allowed": False, "mode": "PREVIEW_ONLY",
                          "reason": "INTENT_REQUIRES_CLARIFICATION" if intent["status"] != "RESOLVED" else None,
                          "localExecutableTools": sorted(LOCAL_RUN_TOOLS)},
        }
        if intent["status"] != "RESOLVED":
            return response
        proposed = list(requested_tools or []) or [item["name"] for item in intent["toolCandidates"]]
        if not proposed:
            response["status"], response["runPolicy"]["reason"] = "NO_REGISTERED_TOOLS", "NO_REGISTERED_TOOLS_FOR_INTENT"
            return response
        try:
            plan = self.compiler.compile(intent=intent["intent"], proposal=proposed,
                                         granted_permissions=PREVIEW_PERMISSIONS)
        except PlanCompilationError as exc:
            response["status"] = "POLICY_REJECTED"
            response["compileError"] = {"code": exc.code, "details": exc.details}
            response["runPolicy"]["reason"] = exc.code
            return response
        tools = {step["tool"] for step in plan["steps"]}
        allowed = intent["intent"] == "KNOWLEDGE_QA" and tools <= LOCAL_RUN_TOOLS
        response.update({"status": "READY", "plan": plan})
        response["runPolicy"].update({
            "allowed": allowed, "mode": "LOCAL_READ_ONLY" if allowed else "PREVIEW_ONLY",
            "reason": None if allowed else "PLAN_CONTAINS_UNBOUND_OR_BILLABLE_TOOLS",
        })
        return response

    def create_run(self, message, context=None, requested_tools=None, request_id=None):
        preview = self.preview(message, context=context, requested_tools=requested_tools)
        run_id = str(uuid.uuid4())
        status = "PENDING" if preview["runPolicy"]["allowed"] else (
            "PREVIEW_ONLY" if preview["status"] == "READY" else preview["status"])
        run = {"runId": run_id, "requestId": request_id or str(uuid.uuid4()),
               "coordinatorVersion": COORDINATOR_VERSION, "status": status,
               "message": message, "context": dict(context or {}), "preview": preview,
               "events": [], "result": None, "cancelRequested": False,
               "createdAt": _now(), "updatedAt": _now()}
        with self._lock:
            self._runs[run_id] = run
            while len(self._runs) > self.max_runs:
                self._runs.popitem(last=False)
        self._event(run_id, "PLAN_COMPILED", {"status": preview["status"],
                    "intent": preview["intent"].get("intent"),
                    "stageCount": len((preview.get("plan") or {}).get("stages", [])),
                    "runAllowed": preview["runPolicy"]["allowed"]})
        if status == "PREVIEW_ONLY":
            self._event(run_id, "RUN_BLOCKED", {"reason": preview["runPolicy"]["reason"]})
        elif status != "PENDING":
            self._event(run_id, "RUN_NOT_STARTED", {"reason": preview["status"]})
        return self.get_run(run_id)

    def _event(self, run_id, event_type, data):
        with self._lock:
            run = self._runs[run_id]
            sequence = run["events"][-1]["sequence"] + 1 if run["events"] else 1
            run["events"].append({"sequence": sequence, "type": event_type,
                                  "timestamp": _now(), "data": data})
            run["events"] = run["events"][-self.max_events_per_run:]
            run["updatedAt"] = _now()

    def execute(self, run_id):
        with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                raise KeyError(run_id)
            if run["status"] != "PENDING":
                return self._public(run)
            if run["cancelRequested"]:
                run["status"] = "CANCELLED"
                self._event(run_id, "RUN_CANCELLED", {"reason": "CANCELLED_BEFORE_START"})
                return self._public(run)
            run["status"] = "RUNNING"
        self._event(run_id, "RUN_STARTED", {"executionMode": "LOCAL_READ_ONLY"})
        wrapped = {}
        for name, function in self.tool_functions.items():
            def invoke(context, tool_name=name, tool_function=function):
                step_id = context["step"]["stepId"]
                self._event(run_id, "STEP_STARTED", {"stepId": step_id, "tool": tool_name})
                try:
                    result = tool_function(context)
                    self._event(run_id, "STEP_COMPLETED", {"stepId": step_id, "tool": tool_name})
                    return result
                except Exception as exc:
                    self._event(run_id, "STEP_FAILED", {"stepId": step_id, "tool": tool_name,
                                                        "errorType": type(exc).__name__})
                    raise
            wrapped[name] = invoke
        try:
            result = self.executor.execute(run["preview"]["plan"], wrapped,
                                           input_data={"message": run["message"], "context": run["context"]})
            with self._lock:
                run["result"], run["status"] = result, result["status"]
            self._event(run_id, "RUN_FINISHED", {"status": result["status"]})
        except Exception as exc:
            with self._lock:
                run["status"], run["result"] = "FAILED", {"status": "FAILED", "errorType": type(exc).__name__}
            self._event(run_id, "RUN_FAILED", {"errorType": type(exc).__name__})
        return self.get_run(run_id)

    def cancel(self, run_id):
        with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                raise KeyError(run_id)
            run["cancelRequested"] = True
            if run["status"] == "PENDING":
                run["status"] = "CANCELLED"
                self._event(run_id, "RUN_CANCELLED", {"reason": "USER_REQUEST"})
            return self._public(run)

    def get_run(self, run_id):
        with self._lock:
            if run_id not in self._runs:
                raise KeyError(run_id)
            return self._public(self._runs[run_id])

    def events_after(self, run_id, after=0):
        return [event for event in self.get_run(run_id)["events"] if event["sequence"] > after]

    @staticmethod
    def _public(run):
        return copy.deepcopy({key: value for key, value in run.items()
                              if key not in {"message", "context", "cancelRequested"}})

    @staticmethod
    def is_terminal(status):
        return status in TERMINAL_STATUSES
