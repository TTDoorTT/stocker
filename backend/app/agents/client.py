import json
from pathlib import Path

import httpx

from app.agents.tools import ToolArgumentsError

PROMPTS = Path(__file__).parent / 'prompts'


class ModelError(Exception):
    pass


class ModelClient:
    def __init__(self, settings):
        self.settings = settings
        self.calls = 0
        self.tokens = 0
        self.reserved_output_tokens = 0
        self.transmitted_context_bytes = 0
        self.usage = []
        self.response_format_with_tools = True

    def complete(self, stage, context, schema, tools):
        """Bounded tool loop. Raw provider errors never enter reports (may contain keys)."""
        if not self.settings.llm_model:
            raise ModelError('LLM_MODEL is not configured')
        messages = [
            {'role': 'system', 'content': (PROMPTS / 'common.md').read_text() + '\n' +
             (PROMPTS / f'{stage}.md').read_text() + '\nSchema: ' + json.dumps(schema)},
            {'role': 'user', 'content': json.dumps(context)},
        ]
        for _ in range(4):
            self.calls += 1
            remaining = 16000 - self.reserved_output_tokens
            if self.calls > 24 or remaining <= 0:
                raise ModelError('Per-run model budget exhausted')
            output_limit = min(self.settings.llm_max_tokens, remaining)
            self.reserved_output_tokens += output_limit
            context_bytes = len(json.dumps(messages).encode('utf-8'))
            self.transmitted_context_bytes += context_bytes
            if context_bytes > 150000 or self.transmitted_context_bytes > 600000:
                raise ModelError('Serialized model context budget exhausted')
            try:
                payload = {'model': self.settings.llm_model, 'temperature': 0,
                           'max_tokens': output_limit, 'messages': messages,
                           'tools': tools.definitions}
                if self.response_format_with_tools:
                    payload['response_format'] = {'type': 'json_object'}
                with httpx.Client(timeout=self.settings.llm_timeout, follow_redirects=False) as client:
                    response = client.post(
                        self.settings.llm_base_url.rstrip('/') + '/chat/completions',
                        headers={'Authorization': f'Bearer {self.settings.llm_api_key}'},
                        json=payload,
                    )
                    if response.status_code == 400 and self.response_format_with_tools:
                        error = response.json().get('error', {})
                        if (isinstance(error, dict) and error.get('message') ==
                                'structured response_format with tools/MCP is not supported'):
                            self.response_format_with_tools = False
                            self.reserved_output_tokens -= output_limit
                            continue
                    response.raise_for_status()
                    result = response.json()
                usage = result.get('usage')
                if usage:
                    if not isinstance(usage, dict) or any(
                            not isinstance(value, int) or isinstance(value, bool) or value < 0
                            for key, value in usage.items()
                            if key in {'prompt_tokens', 'completion_tokens', 'total_tokens'}):
                        raise ModelError('Model returned invalid token usage')
                    self.usage.append(usage)
                    self.tokens += usage.get('total_tokens', 0)
                    if self.tokens > 32000:
                        raise ModelError('Per-run reported total token budget exhausted')
                    # Reclaim unused output allocation only when the provider reports it.
                    used_output = usage.get('completion_tokens')
                    if isinstance(used_output, int) and 0 <= used_output <= output_limit:
                        self.reserved_output_tokens -= output_limit - used_output
                message = result['choices'][0]['message']
                calls = message.get('tool_calls', [])
                if len(calls) > 8:
                    raise ModelError('Too many tool calls in one response')
                if not calls:
                    return json.loads(message['content'])
                messages.append(message)
                for call in calls:
                    try:
                        value = tools.call(call['function']['name'], json.loads(call['function']['arguments']))
                    except ToolArgumentsError:
                        value = {'error': 'Tool request rejected. Use a declared tool with exactly empty arguments {}. '
                                 'Data is already captured for this run; unavailable data cannot be fetched here.'}
                    messages.append({'role': 'tool', 'tool_call_id': call['id'],
                                     'content': json.dumps(value)})
            except (httpx.HTTPError, KeyError, IndexError, AttributeError, TypeError, ValueError) as exc:
                raise ModelError(f'Model response unavailable or invalid ({type(exc).__name__})') from None
        raise ModelError('Tool iteration budget exhausted')


class FixtureModel:
    """Deterministic test double, never used for live mode."""

    usage = []

    def complete(self, stage, context, schema, tools):
        data = tools.call('get_company_data', {})
        evidence = data['evidence']
        calculations = tools.call('calculate_metric', {})
        ids = [e['evidence_id'] for e in evidence]
        calc_ids = [c['calculation_id'] for c in calculations]
        claims = []
        if ids:
            claims.append({'text': 'Synthetic fixture company evidence is available.',
                           'evidence_ids': [ids[0]], 'calculation_ids': []})
        if stage in ('financials', 'valuation'):
            for calc in calculations:
                if calc['value'] is not None:
                    claims.append({'text': calc['metric'].replace('_', ' ') + ' from deterministic fixture inputs.',
                                   'evidence_ids': calc['input_evidence_ids'],
                                   'calculation_ids': [calc['calculation_id']],
                                   'value': calc['value'], 'unit': calc['unit'],
                                   'reference_id': calc['calculation_id']})
        result = {'stage': stage, 'summary': f'Synthetic fixture {stage} stage; not live AI analysis.',
                  'claims': claims, 'evidence_ids': ids, 'calculation_ids': calc_ids,
                  'gaps': ['Synthetic test data only; unavailable licensed analyst consensus.']}
        extras = {
            'profile': {'identity_check': 'Fixture identity only; no live cross-source verification.'},
            'financials': {'performance': 'Synthetic annual data exercises calculations only.'},
            'estimates': {'consensus_available': False},
            'valuation': {'limitations': ['Historical annual EPS is not a current TTM estimate.']},
            'risk': {'counterevidence': ['Synthetic inputs cannot establish real company performance.'],
                     'invalidation_conditions': ['Recheck all findings against live filings.'], 'disputes': []},
            'report': {'executive_summary': 'Synthetic educational pipeline demonstration; not investment advice.'},
        }
        return result | extras[stage]
