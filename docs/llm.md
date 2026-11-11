# SiliconFlow Intent Parsing

The Agent now uses SiliconFlow through LangChain structured output. Configure
the following variables in the project-root `.env` and restart the backend:

```dotenv
LLM_BASE_URL=https://api.siliconflow.cn/v1
LLM_API_KEY=your-private-key
LLM_MODEL=deepseek-ai/DeepSeek-V4-Flash
```

Do not commit `.env` or send keys in requests. The backend reads the key locally.

Send text (including speech transcription) to the existing endpoint:

```http
POST /api/agent/execute
Content-Type: application/json

{"message": "Find a white phone under 5000"}
```

Flow: API -> LangGraph parse node -> SiliconFlow -> validated ShoppingIntent
-> existing search and business tools -> existing response.

Only one supported intent is processed per request. Ambiguous or unsupported
requests return a clarification without executing tools. Payment is not an
allowed model action; users must confirm payment on the order page. The current
payment endpoint still simulates payment rather than charging a real account.

Connection, configuration and output-validation failures return HTTP 502 with
a sanitized message. There is no automatic fallback to rule-based execution.
The old rule parser remains for offline business regression tests only.

Ordinary pytest runs mock the model and do not call the paid API. Model tests
validate schemas, invented IDs, failure handling and the graph payment guard.
The live API was separately tested using only intent parsing, without business
tools. RAG is not yet connected.

## Multi-turn requests

The first request omits `session_id`. The response includes a generated
`session_id`; send it with later messages to continue the same conversation:

```json
{"message": "Only white ones under 5000", "session_id": "<ID returned by the server>"}
```

Omit the ID to start a new conversation. Unknown, expired, and other-user
session IDs are rejected. User identity comes from the backend Cart instance,
not from a request parameter. The HTTP app still uses one development user;
this is not a replacement for login and authentication.

The model extracts changed filters and result positions. The backend merges
filters and maps positions to IDs in the most recently displayed product list.
An ambiguous "this one" or an out-of-range position requires clarification.
Changing the product topic does not inherit old filters. Prior actions and
quantities are not replayed. Failed parsing does not overwrite the context.

Sessions contain at most six recent exchanges, filters, ordered product IDs,
and an optional focused product ID. They do not cache complete product records.
One process stores up to 1000 sessions, with a 30-minute idle timeout and
per-session serialization. Restarting loses conversational context, not business
data. Run one backend worker for this implementation; shared multi-worker
session persistence requires a later database/Redis-backed store.
