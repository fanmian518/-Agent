from __future__ import annotations

import contextvars
import hashlib
import html
import json
import math
import os
import sqlite3
import time
import uuid
from contextlib import contextmanager, asynccontextmanager
from pathlib import Path

_current = contextvars.ContextVar('evaluation_run', default=None)


def database():
    path = Path(os.getenv('EVALUATION_DB', 'data/evaluation.sqlite3'))
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path, timeout=10)
    connection.execute('PRAGMA journal_mode=WAL')
    connection.execute('CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, run_id TEXT NOT NULL, project TEXT NOT NULL, kind TEXT NOT NULL, timestamp REAL NOT NULL, payload TEXT NOT NULL)')
    connection.execute('CREATE INDEX IF NOT EXISTS events_run ON events(run_id)')
    return connection


def event(kind, **payload):
    current = _current.get()
    if current is None:
        return
    # No prompts, arguments, outputs, session identifiers or credentials are stored.
    with database() as connection:
        connection.execute('INSERT INTO events(run_id,project,kind,timestamp,payload) VALUES (?,?,?,?,?)',
                           (*current, kind, time.time(), json.dumps(payload, ensure_ascii=False, allow_nan=False)))
    connection.close()


@contextmanager
def run(project, mode='live'):
    if _current.get() is not None:
        yield _current.get()[0]
        return
    run_id = uuid.uuid4().hex
    token = _current.set((run_id, project))
    started = time.perf_counter()
    event('run_start', mode=mode)
    try:
        yield run_id
    except BaseException as exc:
        event('run_end', success=False, error_type=type(exc).__name__, latency_ms=(time.perf_counter()-started)*1000)
        raise
    else:
        event('run_end', success=True, latency_ms=(time.perf_counter()-started)*1000)
    finally:
        _current.reset(token)


@asynccontextmanager
async def arun(project, mode='live'):
    with run(project, mode) as run_id:
        yield run_id


def task(name, arguments):
    canonical = json.dumps(arguments, sort_keys=True, ensure_ascii=False, separators=(',', ':'), default=str)
    scope = (_current.get() or ('', ''))[0]
    digest = hashlib.sha256((scope + name + canonical).encode()).hexdigest()
    event('task', name=name, fingerprint=digest)


def record_usage(model, input_tokens=None, output_tokens=None):
    known = isinstance(input_tokens, int) and isinstance(output_tokens, int) and min(input_tokens, output_tokens) >= 0
    event('usage', model=model, input_tokens=input_tokens if known else None, output_tokens=output_tokens if known else None)


def summary(project=None, mode=None, pricing=None):
    with database() as connection:
        rows = connection.execute('SELECT run_id,project,kind,payload FROM events ORDER BY id').fetchall()
    connection.close()
    starts = {rid: json.loads(payload) for rid, proj, kind, payload in rows if kind == 'run_start' and (project is None or proj == project)}
    selected = {rid for rid, start in starts.items() if mode is None or start.get('mode') == mode}
    events = [(rid, kind, json.loads(payload)) for rid, proj, kind, payload in rows if rid in selected]
    ends = [p for _, k, p in events if k == 'run_end']
    tools = [p for _, k, p in events if k == 'tool']
    tasks = [(rid, p['fingerprint']) for rid, k, p in events if k == 'task']
    usage = [p for _, k, p in events if k == 'usage']
    known = [p for p in usage if p['input_tokens'] is not None]
    retries = sum(k == 'retry' for _, k, _ in events)
    latencies = sorted(p['latency_ms'] for p in ends)
    ratio = lambda a, b: a / b if b else None
    pricing = pricing or {}
    models = {}
    for item in usage:
        m = models.setdefault(item['model'], {'calls': 0, 'known_calls': 0, 'input_tokens': 0, 'output_tokens': 0, 'estimated_cost': None})
        m['calls'] += 1
        if item['input_tokens'] is not None:
            m['known_calls'] += 1
            m['input_tokens'] += item['input_tokens']
            m['output_tokens'] += item['output_tokens']
    for name, m in models.items():
        price = pricing.get('models', {}).get(name)
        if price and m['known_calls'] == m['calls']:
            rates = [float(price['input_per_million']), float(price['output_per_million'])]
            if any(not math.isfinite(v) or v < 0 for v in rates):
                raise ValueError('Model prices must be finite and nonnegative')
            m['estimated_cost'] = (m['input_tokens']*rates[0] + m['output_tokens']*rates[1])/1_000_000
    complete_cost = bool(models) and all(m['estimated_cost'] is not None for m in models.values()) and retries == 0
    return {
        'project': project, 'mode': mode or 'all', 'runs': len(selected), 'completed_runs': len(ends),
        'run_completion_rate': ratio(sum(p['success'] for p in ends), len(ends)),
        'task_count': len(tasks), 'duplicate_task_count': len(tasks)-len(set(tasks)),
        'task_redundancy_rate': ratio(len(tasks)-len(set(tasks)), len(tasks)),
        'tool_calls': len(tools), 'tool_successes': sum(p['success'] for p in tools),
        'tool_success_rate': ratio(sum(p['success'] for p in tools), len(tools)),
        'retry_count': retries, 'retry_fraction': ratio(retries, len(usage)+retries),
        'latency_p50_ms': latencies[math.ceil(len(latencies)*.5)-1] if latencies else None,
        'latency_p95_ms': latencies[math.ceil(len(latencies)*.95)-1] if latencies else None,
        'model_calls': len(usage), 'usage_coverage': ratio(len(known), len(usage)),
        'known_input_tokens': sum(p['input_tokens'] for p in known),
        'known_output_tokens': sum(p['output_tokens'] for p in known),
        'estimated_cost': sum(m['estimated_cost'] for m in models.values()) if complete_cost else None,
        'currency': pricing.get('currency'), 'models': models,
        'definitions': {
            'task_redundancy_rate': '同一请求内相同任务名及规范化参数的重复次数 / 计划任务数；仅为精确重复代理指标，不能代表语义冗余。工具重试不重复计入任务。',
            'tool_success_rate': '实际工具调用中无异常且未返回业务错误的次数 / 实际调用次数；不等于答案正确率。',
            'run_completion_rate': '已结束请求中正常结束的比例；不等于业务目标完成率。',
            'estimated_cost': '按模型输入/输出每百万 Token 单价估算，非账单。无价格、usage 缺失或有未知重试费用时显示 N/A。',
            'retry_fraction': '显式重试次数 / (模型返回次数 + 重试次数)。',
        },
    }


def write_report(output, **kwargs):
    result = summary(**kwargs)
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.with_suffix('.json').write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    labels = {'runs':'请求样本数','task_count':'拆分任务数','task_redundancy_rate':'任务拆分冗余率（精确重复）','tool_calls':'工具调用次数','tool_success_rate':'工具调用成功率','retry_count':'重试次数','latency_p50_ms':'P50 耗时 / ms','latency_p95_ms':'P95 耗时 / ms','model_calls':'模型调用次数','usage_coverage':'Token 数据覆盖率','known_input_tokens':'已采集输入 Token','known_output_tokens':'已采集输出 Token','estimated_cost':'Token 估算成本'}
    cards = []
    for key, label in labels.items():
        value = result[key]
        display = 'N/A · 尚无数据' if value is None else (f'{value:.2%}' if 'rate' in key or key == 'usage_coverage' else f'{value:,.3f}' if isinstance(value, float) else str(value))
        cards.append(f'<article><small>{label}</small><strong>{html.escape(display)}</strong></article>')
    body = ''.join(cards)
    definitions = ''.join(f'<li>{html.escape(v)}</li>' for v in result['definitions'].values())
    output.with_suffix('.html').write_text(f'''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>Agent 评测报告</title><style>body{{background:#101724;color:#e9eef7;font:16px system-ui;max-width:1150px;margin:50px auto;padding:24px}}h1{{font-size:36px}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:16px}}article{{background:#1c293b;padding:24px;border-radius:12px}}small{{color:#a7bed4}}strong{{display:block;margin-top:12px;font-size:26px}}li{{margin:12px 0;line-height:1.6}}code{{color:#7be0c3}}</style><h1>Agent 工程评测</h1><p>项目：{html.escape(str(result['project'] or '全部'))} · 数据分组：<code>{html.escape(result['mode'])}</code> · 生成时间：{time.strftime('%Y-%m-%d %H:%M:%S')}</p><div class="grid">{body}</div><h2>统计口径</h2><ul>{definitions}</ul><p>fixture / offline 数据只证明测试场景的行为，不代表真实用户效果。输入、工具参数与模型输出不会写入评测库。</p></html>''', encoding='utf-8')
    return result
