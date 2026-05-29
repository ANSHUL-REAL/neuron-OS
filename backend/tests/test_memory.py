from neuronos.memory import MemoryStore


def test_memory_store_saves_and_searches_semantic_text(tmp_path):
    store = MemoryStore(tmp_path / "neuronos.db", collection_path=tmp_path / "chroma")
    store.save_memory("project", "My LangGraph project lives in D:\\Projects\\langgraph")

    results = store.search("continue LangGraph work")

    assert results
    assert results[0].kind == "project"
    assert "LangGraph project" in results[0].content


def test_memory_store_records_execution_log(tmp_path):
    store = MemoryStore(tmp_path / "neuronos.db", collection_path=tmp_path / "chroma")

    store.record_execution("tool-1", "browser.search", "completed", "Opened search")
    rows = store.recent_executions(limit=1)

    assert rows[0].tool == "browser.search"
    assert rows[0].status == "completed"


def test_memory_store_returns_recent_conversation(tmp_path):
    store = MemoryStore(tmp_path / "neuronos.db")
    store.save_conversation("user", "open brave")
    store.save_conversation("assistant", "Done.")

    rows = store.recent_conversations(limit=2)

    assert [row["role"] for row in rows] == ["assistant", "user"]
    assert rows[1]["content"] == "open brave"
