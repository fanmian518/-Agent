import httpx
from openai import APIConnectionError, APIStatusError, APITimeoutError, RateLimitError
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_random_exponential
from evaluation_runtime import event


def transient(exc):
    return isinstance(exc, (APIConnectionError, APITimeoutError, RateLimitError, httpx.TransportError)) or (isinstance(exc, (APIStatusError, httpx.HTTPStatusError)) and (getattr(exc, 'status_code', getattr(getattr(exc, 'response', None), 'status_code', 0)) in (408, 429) or getattr(exc, 'status_code', getattr(getattr(exc, 'response', None), 'status_code', 0)) >= 500))


retry_external = retry(retry=retry_if_exception(transient), stop=stop_after_attempt(3), wait=wait_random_exponential(min=.2, max=4), reraise=True, before_sleep=lambda state: event('retry', error_type=type(state.outcome.exception()).__name__))


@retry_external
def invoke_model(model, messages):
    return model.invoke(messages)
