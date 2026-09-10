"""Public error-envelope regressions through the real MCP session dispatcher.

Requires only the client runtime and pytest; no FastAPI, application services,
DB, external HTTP, or paid calls.
"""
import asyncio
import json
import os
from unittest.mock import Mock

import pytest
from requests import HTTPError, Response
from mcp.shared.memory import create_connected_server_and_client_session

os.environ['PYTHON_DOTENV_DISABLED'] = '1'
os.environ.pop('CHART_LIBRARY_API_KEY', None)
os.environ.pop('CHART_LIBRARY_MCP_PROFILE', None)

import mcp_server as server


def http_failure(status, body):
    response = Response()
    response.status_code = status
    response._content = json.dumps(body).encode()
    response.headers['Content-Type'] = 'application/json'
    return HTTPError('private-fixture-exception', response=response)


async def wire_call(name, arguments):
    async with create_connected_server_and_client_session(server.mcp) as session:
        listed = await session.list_tools()
        tool = next(t for t in listed.tools if t.name == name)
        result = await session.call_tool(name, arguments)
        text = next(c.text for c in result.content if c.type == 'text')
        assert result.structuredContent == {'result': text}
        assert tool.outputSchema == {
            'properties': {'result': {'title': 'Result', 'type': 'string'}},
            'required': ['result'], 'title': name + 'Output', 'type': 'object',
        }
        return result, json.loads(text)


@pytest.mark.parametrize('status,body,word', [
    (409, {'detail': 'private-fixture-body'}, 'section=overview'),
    (422, {'detail': 'offset is beyond this document'}, 'offset'),
    (422, {'error': {'message': 'offset is beyond this document'}}, 'offset'),
    (400, {'detail': 'query must contain at most 200 characters'}, 'query'),
    (404, {'detail': 'private-fixture-body'}, 'unavailable'),
    (429, {'detail': 'private-fixture-body'}, 'wait'),
    (500, {'detail': 'private-fixture-body'}, 'unavailable'),
])
def test_http_errors_preserve_recovery_and_set_wire_flag(monkeypatch, status, body, word):
    read = Mock(side_effect=http_failure(status, body))
    monkeypatch.setattr(server, '_http_get', read)
    result, payload = asyncio.run(wire_call('read_research', {'research_id': 'study:100'}))
    assert result.isError is True
    assert payload['status'] == 'error' and payload['data'] == {}
    assert payload['meta']['http_status'] == status
    assert word in ' '.join(payload['meta']['warnings']).lower()
    assert 'private-fixture' not in result.model_dump_json()
    assert read.call_count == 1


@pytest.mark.parametrize('body', [
    {'detail': 'private-fixture-body'},
    {'error': {'message': 'private-fixture-body'}},
    {'detail': [{'loc': ['query', 'offset'], 'msg': 'private-fixture-body',
                 'input': 'private-fixture-input', 'ctx': {'error': 'private-fixture-context'}}]},
])
def test_unrecognized_validation_content_is_not_forwarded(monkeypatch, body):
    read = Mock(side_effect=http_failure(422, body))
    monkeypatch.setattr(server, '_http_get', read)
    result, payload = asyncio.run(wire_call('read_research', {'research_id': 'study:100'}))
    assert result.isError is True
    assert payload['meta']['http_status'] == 422
    assert 'private-fixture' not in result.model_dump_json()
    assert 'unavailable' not in ' '.join(payload['meta']['warnings']).lower()
    assert read.call_count == 1


@pytest.mark.parametrize('status', ['ok', 'partial', 'weak', 'abstain'])
def test_nonerror_statuses_and_success_schema_stay_unchanged(monkeypatch, status):
    payload = {'status': status, 'data': {'missing': None, 'n': 31},
               'meta': {'warnings': ['thin evidence']}}
    read = Mock(return_value=payload)
    monkeypatch.setattr(server, '_http_get', read)
    result, observed = asyncio.run(wire_call('search_research', {'query': 'fixture'}))
    assert result.isError is False
    assert observed == payload
    assert read.call_count == 1


def test_invalid_clock_sets_wire_error_without_http(monkeypatch):
    read = Mock()
    monkeypatch.setattr(server, '_http_get', read)
    result, payload = asyncio.run(wire_call('market_state', {
        'symbol': 'IONQ', 'date': '2026-05-12T12:00:00-04:00',
    }))
    assert result.isError is True
    assert 'date' in ' '.join(payload['meta']['warnings']).lower()
    read.assert_not_called()
