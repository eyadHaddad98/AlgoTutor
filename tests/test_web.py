import pytest
from sqlalchemy import select
from algotutor.config import Settings
from algotutor.storage import ToolCall, Store
from algotutor.catalog import example
from algotutor.web import create_app


@pytest.fixture
def app(tmp_path):
    settings = Settings(demo=True, database_url="sqlite:///" + str(tmp_path / "test.sqlite3"), secret_key="x" * 40, api_key="")
    app = create_app(settings)
    app.config["TESTING"] = True
    return app


def test_chat_history_sessions_and_three_routes(app):
    client = app.test_client()
    assert client.get("/history").json == {"messages": []}
    for message, route, attached in [("שלום", "direct", None), ("מהו עץ פורש מינימלי?", "rag", None),
        ("הרץ דייקסטרה", "tools", {"algorithm": "dijkstra", "arguments": example("dijkstra")})]:
        response = client.post("/chat", json={"message": message, "tool_request": attached})
        assert response.status_code == 200
        assert response.json["route"] == route
        assert response.json["routing"]["method"] in ("explicit_input", "rules_fallback")
        assert response.json["generation"] == "fallback"
    assert len(client.get("/history").json["messages"]) == 6
    assert app.test_client().get("/history").json == {"messages": []}
    # Caller-supplied identifiers are ignored; only the signed session cookie owns history.
    assert app.test_client().get("/history?session_id=arbitrary").json == {"messages": []}
    client.post("/sessions/new", json={})
    assert client.get("/history").json == {"messages": []}


def test_calculator_logs_both_success_and_error(app):
    client = app.test_client()
    assert client.post("/tools/run", json={"algorithm": "kruskal", "arguments": example("kruskal")}).status_code == 200
    args = example("dijkstra")
    args["graph"]["edges"][0]["weight"] = -1
    result = client.post("/tools/run", json={"algorithm": "dijkstra", "arguments": args})
    assert result.status_code == 422
    assert "שליליים" in result.json["output"]["error"]
    with app.extensions["store"].sessions() as db:
        logs = db.scalars(select(ToolCall)).all()
        assert {row.status for row in logs} == {"ok", "error"}
        assert all(row.input and row.output for row in logs)


@pytest.mark.parametrize("data", [{}, {"message": ""}, {"message": "a" * 12001}, {"message": ["hello"]}, {"message": "x", "tool_request": {"algorithm": "bad", "arguments": {}}}, {"message": "x", "tool_request": {"algorithm": ["bfs"], "arguments": {}}}])
def test_bad_chat_input(app, data):
    assert app.test_client().post("/chat", json=data).status_code == 400


def test_http_errors_and_headers(app):
    client = app.test_client()
    assert client.post("/chat", data='{bad', content_type="application/json").status_code == 400
    assert client.post("/chat", data="hello").status_code == 415
    assert client.post("/chat", json={"message": "hello"}, headers={"Origin": "https://elsewhere.example"}).status_code == 403
    assert client.post("/chat", data="x" * 100001, content_type="application/json").status_code == 413
    assert client.get("/lectures/99").status_code == 404
    assert client.get("/lectures/1").mimetype == "application/pdf"
    assert "default-src 'self'" in client.get("/").headers["Content-Security-Policy"]
    assert client.get("/health").json["demo"] is True
    assert len(client.get("/catalog").json["algorithms"]) == 12


def test_production_rejects_sqlite():
    with pytest.raises(ValueError):
        Store("sqlite:///:memory:")
