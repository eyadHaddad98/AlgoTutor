from langchain_core.runnables import RunnableLambda
from langchain_core.messages import AIMessage, ToolMessage
from algotutor.agent import Tutor, Router, Decision
from algotutor.config import Settings
from algotutor.catalog import example
from algotutor.retrieval import RetrievalError


class MemoryStore:
    def __init__(self):
        self.logs = []
    def log_tool(self, *args):
        self.logs.append(args)


class EmptyRetriever:
    def search(self, *args):
        return []


def make_model():
    # A scripted model exercises real LCEL composition and tool message plumbing.
    model = RunnableLambda(lambda prompt: AIMessage(content="התוצאה מוסברת לפי החישוב."))
    model.with_structured_output = lambda schema: RunnableLambda(lambda prompt: Decision(route="rag", reason="שאלה לימודית", search_query="BFS"))
    def respond(prompt):
        if any(isinstance(m, ToolMessage) for m in prompt.to_messages()):
            return AIMessage(content="התקבלה תוצאת הכלי.")
        return AIMessage(content="", tool_calls=[
            {"name": "dijkstra", "args": example("dijkstra"), "id": "call-1", "type": "tool_call"}])
    model.bind_tools = lambda schemas, **kwargs: RunnableLambda(respond)
    return model


def test_lcel_model_router_and_tool_execution():
    store, model = MemoryStore(), make_model()
    tutor = Tutor(Settings(demo=False, api_key=""), store, EmptyRetriever(), model=model)
    out = tutor.process("הרץ דייקסטרה", [], {"algorithm": "dijkstra", "arguments": example("dijkstra")}, "session", "request")
    assert out["generation"] == "anthropic_lcel"
    assert out["tool_results"][0]["output"]["distances"]["E"] == 11
    assert len(store.logs) == 1
    assert tutor.process("מהו BFS?", [], None, "session", "request")["routing"]["method"] == "llm_classifier"


def test_actual_tool_result_round_trip_to_model():
    model = make_model()
    seen = []
    def respond(prompt):
        messages = prompt.to_messages()
        seen.extend(messages)
        if any(isinstance(m, ToolMessage) for m in messages):
            return AIMessage(content="החישוב הושלם")
        return AIMessage(content="", tool_calls=[{"name": "bfs", "args": example("bfs"), "id": "bfs-1", "type": "tool_call"}])
    model.bind_tools = lambda *a, **kw: RunnableLambda(respond)
    tutor = Tutor(Settings(api_key=""), MemoryStore(), EmptyRetriever(), model=model)
    calls = []
    tutor.tool_loop("הרץ BFS", [], {"algorithm": "bfs"}, None, "s", "r", calls)
    assert len(calls) == 1
    assert any(isinstance(m, ToolMessage) and m.tool_call_id == "bfs-1" for m in seen)


def test_model_failure_uses_grounded_fallback_and_keeps_tool_results():
    def fail(_):
        raise RuntimeError("simulated API failure")
    model = RunnableLambda(fail)
    model.bind_tools = lambda *a, **kw: RunnableLambda(fail)
    model.with_structured_output = lambda *a, **kw: RunnableLambda(fail)
    tutor = Tutor(Settings(api_key=""), MemoryStore(), EmptyRetriever(), model=model)
    out = tutor.process("הרץ", [], {"algorithm": "kruskal", "arguments": example("kruskal")}, "s", "r")
    assert out["generation"] == "fallback"
    assert out["tool_results"][0]["output"]["total_weight"] == 10
    assert "10" in out["answer"]
    assert Router(model).decide("למה דייקסטרה נכשל במשקל שלילי?", [])["route"] == "rag"


def test_rag_unavailable_does_not_invent_sources():
    class BrokenRetriever:
        def search(self, *args):
            raise RetrievalError("מאגר הידע אינו זמין")
    out = Tutor(Settings(api_key=""), MemoryStore(), BrokenRetriever()).process("הסבר BFS", [], None, "s", "r")
    assert out["sources"] == []
    assert out["generation"] == "fallback"
    assert "מקור" in out["answer"]


def test_follow_up_rule_query_uses_history():
    output = Router().decide("ומה הסיבוכיות שלו?", [{"role": "user", "content": "הסבר BFS"}])
    assert "BFS" in output["search_query"]
