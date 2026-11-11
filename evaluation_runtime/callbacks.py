"""LangChain Core callback protocol for LangGraph execution."""
import time
from langchain_core.callbacks import BaseCallbackHandler
from .metrics import event, record_usage


class EvaluationCallback(BaseCallbackHandler):
    def __init__(self):
        self.started = {}
        self.spans = {}

    def on_tool_start(self, serialized, input_str, *, run_id, **kwargs):
        self.started[run_id] = (time.perf_counter(), serialized.get('name', 'tool'))
        from opentelemetry import trace
        self.spans[run_id] = trace.get_tracer(__name__).start_span('tool.' + serialized.get('name','tool'))

    def _tool_end(self, run_id, success):
        started, name = self.started.pop(run_id, (time.perf_counter(), 'tool'))
        event('tool', name=name, success=success, latency_ms=(time.perf_counter()-started)*1000)
        span = self.spans.pop(run_id, None)
        if span:
            span.set_attribute('tool.success', success)
            span.end()

    def on_tool_end(self, output, *, run_id, **kwargs):
        failed = (isinstance(output, dict) and (bool(output.get('error')) or output.get('success') is False)) or (isinstance(output, str) and output.startswith(('错误:', '错误：')))
        self._tool_end(run_id, not failed)

    def on_tool_error(self, error, *, run_id, **kwargs):
        self._tool_end(run_id, False)

    def on_llm_end(self, response, **kwargs):
        metadata = response.llm_output or {}
        usage = metadata.get('token_usage', {})
        record_usage(metadata.get('model_name', 'unknown'), usage.get('prompt_tokens'), usage.get('completion_tokens'))
        from opentelemetry import trace
        span = trace.get_current_span()
        span.set_attribute('gen_ai.request.model',metadata.get('model_name','unknown'))
        for source, name in [('prompt_tokens','input_tokens'),('completion_tokens','output_tokens')]:
            if isinstance(usage.get(source),int):
                span.set_attribute('gen_ai.usage.'+name,usage[source])

    def on_llm_error(self, error, **kwargs):
        record_usage('unknown')
