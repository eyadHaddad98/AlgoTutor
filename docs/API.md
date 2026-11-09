# REST API

Same-origin JSON API. Session identity comes from the server-signed cookie; callers cannot select another user's session through request parameters. In curl, use `-c cookies.txt -b cookies.txt` to retain a session.

## POST /chat

```json
{"message":"למה דייקסטרה דורש משקלים אי־שליליים?"}
```

Optional explicit tool request:

```json
{"message":"הרץ והסבר","tool_request":{"algorithm":"bfs","arguments":{"graph":{"vertices":["A","B"],"directed":false,"edges":[{"from":"A","to":"B","weight":1}]},"source":"A"}}}
```

Response shape:

```json
{
  "answer": "...",
  "route": "rag",
  "routing": {"route":"rag","reason":"...","algorithm":null,"search_query":"...","method":"llm_classifier"},
  "sources": [{"id":"...","lecture":3,"page":1,"slide":83,"title":"...","text":"...","score":0.84,"score_type":"cosine","url":"/lectures/3#page=1"}],
  "tool_results": [],
  "notices": [],
  "generation": "anthropic_lcel",
  "request_id": "UUID",
  "demo": false
}
```

Values above are illustrative, not a claimed recorded model answer or score. Routes: `rag`, `tools`, `direct`. Router methods: `llm_classifier`, `explicit_input`, `rules_fallback`. Generation: `anthropic_lcel` or `fallback`. Fallback HTTP 200 means a usable degraded response, not a successful LLM call. Model/API exceptions and missing retrieval are disclosed in `notices`.

The message must contain 1–12,000 nonempty characters. Maximum request body: 100,000 bytes. Tool inputs are validated before execution. Concurrent requests for the same session can return 409. Input validation returns 400, wrong content type 415, oversized request 413, and DB/server failure 503.

## POST /tools/run

Body: `{"algorithm":"dijkstra","arguments":{...}}` using the same schemas as the tool registry.

Returns `name`, `input`, `output`, `ok`, `tool_call_id` (null for direct calculator), `request_id` and `execution:"python_calculator"`. Success is HTTP 200, algorithm validation errors 422. Both are logged to PostgreSQL; calculator calls do not automatically add chat messages.

## GET /history

Returns `{"messages":[{"id":"...","role":"user|assistant","content":"...","payload":{},"created_at":"..."}]}` for the current session, oldest first among the last 100 messages.

## POST /sessions/new

Send `{}`. Creates a new signed-cookie session and returns `{"ok":true}`. It does not delete old DB rows.

## GET /health

```json
{"status":"ready","server":"ok","database":"ok","rag":{"status":"ready","chunks":500},"llm":"configured","demo":false}
```

The chunk count is illustrative. Status can be `ready`, `degraded` or `unhealthy`. It checks DB and Chroma and whether a key is configured. It intentionally does not call a paid model or download the embedding model. DB failure returns 503; incomplete AI setup returns 200 with `degraded`.

## GET /catalog and GET /lectures/{1..11}

Catalog returns tools, their examples and the lecture manifest. Lecture routes serve the supplied PDF through Flask; `#page=N` anchors identify physical PDF pages. Printed slide numbers are distinct metadata.
