"""Small JSON-RPC bridge for the registered read/review tools.

This is an application-local MCP-shaped adapter, not a hosted MCP server. It
keeps protocol concerns separate from the Agent workflow so a future stdio or
streamable-HTTP transport can reuse the same tool definitions and gates.
"""
from __future__ import annotations

import json
from typing import Any, Dict

from .agent.tool_router import ROUTER_VERSION, TOOL_CATALOG, TOOL_ORDER
from .demo import build_demo_workflow
from .knowledge import search


BRIDGE_VERSION = 'mcp-bridge-v1'


class McpBridgeError(Exception):
    def __init__(self, code: int, message: str, data: Dict[str, Any] | None = None):
        super().__init__(message)
        self.code = code
        self.data = data


def tool_definitions():
    return [{'name': name, 'description': TOOL_CATALOG[name]['purpose'],
             'inputSchema': TOOL_CATALOG[name]['inputSchema'],
             'metadata': {'version': TOOL_CATALOG[name]['version'],
                          'kind': TOOL_CATALOG[name]['kind'],
                          'requires': TOOL_CATALOG[name]['requires'],
                          'maxCalls': TOOL_CATALOG[name]['maxCalls']}}
            for name in TOOL_ORDER]


def tools_list():
    return {'bridgeVersion': BRIDGE_VERSION, 'routerVersion': ROUTER_VERSION,
            'transport': 'json-rpc-2.0', 'tools': tool_definitions()}


def _validate_arguments(name: str, arguments: Any) -> Dict[str, Any]:
    if not isinstance(arguments, dict):
        raise McpBridgeError(-32602, '工具参数必须是对象。')
    schema = TOOL_CATALOG[name]['inputSchema']
    unknown = sorted(set(arguments) - set(schema['properties']))
    if unknown:
        raise McpBridgeError(-32602, '工具包含未声明参数。', {'fields': unknown})
    for required in schema.get('required', []):
        if required not in arguments:
            raise McpBridgeError(-32602, f'缺少必填参数：{required}。')
    if name == 'knowledge.search':
        query = arguments['query']
        limit = arguments.get('limit', 6)
        if not isinstance(query, str) or not query.strip() or len(query) > 500:
            raise McpBridgeError(-32602, 'query 必须是 1-500 个字符。')
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 20:
            raise McpBridgeError(-32602, 'limit 必须是 1-20 的整数。')
    if name == 'analyst.review':
        candidates = arguments['candidates']
        if not isinstance(candidates, list) or len(candidates) > 20:
            raise McpBridgeError(-32602, 'candidates 必须是最多 20 条的数组。')
    return arguments


def call_tool(name: str, arguments: Any):
    if name not in TOOL_CATALOG:
        raise McpBridgeError(-32601, '工具未注册。', {'tool': str(name)[:100]})
    args = _validate_arguments(name, arguments)
    if name == 'knowledge.search':
        result = search(args['query'].strip(), args.get('limit', 6))
    else:
        workflow = build_demo_workflow()
        result = workflow.invoke({
            'taskId': args.get('taskId', 'MCP-DEMO-001'),
            'rawCandidates': args['candidates'],
            'featureEvidence': args.get('featureEvidence', {}),
            'modelEvidence': args.get('modelEvidence', {}),
            'reportSnapshot': {'riskLevel': 'UNKNOWN'},
            'requestedTools': args.get('requestedTools', []),
        })
    return {'content': [{'type': 'text', 'text': json.dumps(result, ensure_ascii=False)}],
            'structuredContent': result, 'isError': False}


def dispatch(method: str, params: Dict[str, Any] | None = None):
    params = params or {}
    if method == 'tools/list':
        return tools_list()
    if method == 'tools/call':
        return call_tool(params.get('name'), params.get('arguments', {}))
    raise McpBridgeError(-32601, '方法未实现。', {'method': method})
