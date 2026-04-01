import asyncio
import importlib.util
import json
import os
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
MAIN_PATH = ROOT / "backend" / "fastapi" / "main.py"


class FakeResponse:
    def __init__(self, data=None, count=None):
        self.data = data or []
        self.count = count


class FakeTableQuery:
    def __init__(self, supabase, table_name: str):
        self.supabase = supabase
        self.table_name = table_name
        self.selected_columns = None
        self.count_mode = None
        self.filters = []
        self.order_by = None
        self.order_desc = False
        self.limit_count = None
        self.insert_payload = None
        self.update_payload = None

    def select(self, *columns, count=None):
        self.selected_columns = columns
        self.count_mode = count
        self.supabase.logs.append(("select", self.table_name, columns, count))
        return self

    def eq(self, column, value):
        self.filters.append((column, value))
        self.supabase.logs.append(("eq", self.table_name, column, value))
        return self

    def order(self, column, desc=False):
        self.order_by = column
        self.order_desc = desc
        self.supabase.logs.append(("order", self.table_name, column, desc))
        return self

    def limit(self, count):
        self.limit_count = count
        self.supabase.logs.append(("limit", self.table_name, count))
        return self

    def insert(self, payload):
        self.insert_payload = payload
        self.supabase.logs.append(("insert", self.table_name, payload))
        return self

    def update(self, payload):
        self.update_payload = payload
        self.supabase.logs.append(("update", self.table_name, payload))
        return self

    def execute(self):
        rows = [dict(row) for row in self.supabase.tables.get(self.table_name, [])]

        if self.insert_payload is not None:
            payload = dict(self.insert_payload)
            if "id" not in payload:
                payload["id"] = f"{self.table_name}-{len(self.supabase.tables.get(self.table_name, [])) + 1}"
            self.supabase.tables.setdefault(self.table_name, []).append(payload)
            return FakeResponse(data=[payload])

        for column, value in self.filters:
            rows = [row for row in rows if row.get(column) == value]

        filtered_count = len(rows)

        if self.update_payload is not None:
            for row in self.supabase.tables.get(self.table_name, []):
                if all(row.get(column) == value for column, value in self.filters):
                    row.update(self.update_payload)
            return FakeResponse(data=[])

        if self.order_by:
            rows.sort(key=lambda row: row.get(self.order_by), reverse=self.order_desc)

        if self.limit_count is not None:
            rows = rows[:self.limit_count]

        if self.selected_columns:
            rows = [
                {column: row.get(column) for column in self.selected_columns}
                for row in rows
            ]

        return FakeResponse(data=rows, count=filtered_count if self.count_mode == "exact" else None)


class FakeSupabase:
    def __init__(self):
        self.tables = {
            "cases": [
                {
                    "id": "case-1",
                    "summary": "Existing summary",
                    "notes": json.dumps(["stored note", "priority debt"]),
                }
            ],
            "messages": [
                {
                    "id": "m1",
                    "case_id": "case-1",
                    "role": "advisor",
                    "content": "Client has received a section 21 notice",
                    "created_at": "2026-04-01T10:00:00Z",
                },
                {
                    "id": "m2",
                    "case_id": "case-1",
                    "role": "assistant",
                    "content": "Asked whether the notice date has passed",
                    "created_at": "2026-04-01T10:01:00Z",
                },
                {
                    "id": "m3",
                    "case_id": "case-2",
                    "role": "advisor",
                    "content": "Unrelated case should never be read",
                    "created_at": "2026-04-01T09:59:00Z",
                },
            ],
            "chunks": [],
        }
        self.logs = []

    def table(self, table_name):
        return FakeTableQuery(self, table_name)

    def rpc(self, name, params):
        self.logs.append(("rpc", name, params))
        return SimpleNamespace(execute=lambda: FakeResponse(data=[]))


def load_main_module(fake_supabase: FakeSupabase):
    module_name = "rag_main_under_test"
    sys.modules.pop(module_name, None)

    fake_gemini = SimpleNamespace(
        models=SimpleNamespace(
            generate_content=lambda **kwargs: SimpleNamespace(text='{"search_query": "rewritten"}')
        )
    )

    with patch.dict(
        os.environ,
        {
            "SUPABASE_URL": "https://example.supabase.co",
            "SUPABASE_KEY": "test-key",
            "GEMINI_API_KEY": "test-gemini-key",
        },
        clear=False,
    ), patch("supabase.create_client", return_value=fake_supabase), patch("google.genai.Client", return_value=fake_gemini):
        spec = importlib.util.spec_from_file_location(module_name, MAIN_PATH)
        module = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        spec.loader.exec_module(module)
        return module


class RagContextTests(unittest.TestCase):
    def test_rewrite_query_uses_case_notes_and_same_case_history(self):
        fake_supabase = FakeSupabase()
        main = load_main_module(fake_supabase)

        captured = {}

        def fake_rewrite(user_query, notes, history, selected_sources, selected_documents):
            captured["user_query"] = user_query
            captured["notes"] = notes
            captured["history"] = history
            captured["selected_sources"] = selected_sources
            captured["selected_documents"] = selected_documents
            return user_query

        main.rewrite_search_query = fake_rewrite
        main.retrieve_chunks = lambda *args, **kwargs: [{"source_url": "https://example.com", "text": "retrieved"}]
        main.rerank_chunks = lambda chunks, *args, **kwargs: chunks
        main.generate_ai_response = lambda *args, **kwargs: ("Grounded answer", ["https://example.com"])

        request = main.QueryRequest(
            query="Can the landlord evict them now?",
            notes=["unsaved frontend note"],
            selected_sources=[],
            selected_documents=[],
        )
        result = asyncio.run(main.ask_question("case-1", request))

        self.assertEqual(captured["user_query"], "Can the landlord evict them now?")
        self.assertIn("stored note", captured["notes"])
        self.assertIn("priority debt", captured["notes"])
        self.assertIn("unsaved frontend note", captured["notes"])
        self.assertEqual(
            captured["history"],
            [
                {"role": "advisor", "content": "Client has received a section 21 notice"},
                {"role": "assistant", "content": "Asked whether the notice date has passed"},
            ],
        )
        self.assertEqual(result["answer"], "Grounded answer")
        self.assertEqual(result["sources"], ["https://example.com"])

        self.assertIn(("select", "cases", ("id", "summary", "notes"), None), fake_supabase.logs)
        self.assertIn(("eq", "cases", "id", "case-1"), fake_supabase.logs)
        self.assertIn(("eq", "messages", "case_id", "case-1"), fake_supabase.logs)
        unrelated_texts = [entry["content"] for entry in captured["history"]]
        self.assertNotIn("Unrelated case should never be read", unrelated_texts)

    def test_rewrite_prompt_contains_current_query_notes_and_recent_messages(self):
        fake_supabase = FakeSupabase()
        main = load_main_module(fake_supabase)

        prompt_holder = {}

        def fake_generate_content(*, model, contents):
            prompt_holder["model"] = model
            prompt_holder["contents"] = contents
            return SimpleNamespace(text='{"search_query": "section 21 eviction notice rent arrears"}')

        main.gemini_client = SimpleNamespace(
            models=SimpleNamespace(generate_content=fake_generate_content)
        )

        rewritten = main.rewrite_search_query(
            "What help can we give about a section 21 notice?",
            ["rent arrears", "two children in household"],
            [
                {"role": "advisor", "content": "Client says the notice was hand delivered"},
                {"role": "assistant", "content": "We need the expiry date and tenancy type"},
            ],
            ["https://www.citizensadvice.org.uk/housing"],
            ["Housing handbook"],
        )

        self.assertEqual(rewritten, "section 21 eviction notice rent arrears")
        self.assertEqual(prompt_holder["model"], "gemini-2.5-flash")
        self.assertIn("Original question:\nWhat help can we give about a section 21 notice?", prompt_holder["contents"])
        self.assertIn("Notes:\n- rent arrears\n- two children in household", prompt_holder["contents"])
        self.assertIn("Recent case messages:\nAdvisor: Client says the notice was hand delivered", prompt_holder["contents"])
        self.assertIn("Assistant: We need the expiry date and tenancy type", prompt_holder["contents"])


if __name__ == "__main__":
    unittest.main()
