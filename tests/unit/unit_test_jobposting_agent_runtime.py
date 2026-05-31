import unittest
import uuid
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from app.services import jobposting_agent_runtime as runtime


def fake_response(*, text=None, calls=None):
    parts = []
    for call in calls or []:
        parts.append(SimpleNamespace(function_call=SimpleNamespace(**call), text=None))
    if text is not None:
        parts.append(SimpleNamespace(function_call=None, text=text))
    content = SimpleNamespace(parts=parts)
    return SimpleNamespace(text=text, candidates=[SimpleNamespace(content=content)])


async def ok_tool(**kwargs):
    return {
        "ok": True,
        "data": {"job_app_id": kwargs.get("job_app_id", 101), "value": "ok"},
        "source": {"tool": "mock"},
        "warnings": [],
        "error": None,
    }


async def ranking_tool(**kwargs):
    return {
        "ok": True,
        "data": {
            "candidates": [
                {"job_app_id": 101, "candidate_id": 7, "candidate_name": "A"}
            ],
            "returned": 1,
            "limit": kwargs.get("limit", 10),
            "filters_applied": kwargs.get("filters") or {},
            "total_available": 1,
        },
        "source": {"tool": "get_job_candidate_ranking"},
        "warnings": [],
        "error": None,
    }


async def large_tool(**kwargs):
    return {
        "ok": True,
        "data": {"payload": "x" * 1000, "job_app_id": 101},
        "source": {"tool": "large"},
        "warnings": [],
        "error": None,
    }


class JobPostingAgentRuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_mock_gemini_function_call_then_final_answer(self) -> None:
        conv_id = uuid.uuid4()
        responses = [
            (
                fake_response(
                    calls=[
                        {
                            "name": "get_job_candidate_ranking",
                            "args": {"limit": 10},
                            "id": "fc1",
                        }
                    ]
                ),
                "gemini-3.1-flash-lite",
            ),
            (fake_response(text="Đây là top ứng viên."), "gemini-3.1-flash-lite"),
        ]
        with patch(
            "app.services.jobposting_agent_runtime._generate_with_fallback",
            new_callable=AsyncMock,
        ) as mock_gen:
            mock_gen.side_effect = responses
            with patch.dict(
                runtime.TOOL_FUNCTIONS, {"get_job_candidate_ranking": ranking_tool}
            ):
                result = await runtime.run_agent_turn(
                    conversation_id=conv_id,
                    job_post_id=12,
                    hr_id=34,
                    prompt="Top 10",
                    state={},
                    history=[],
                )

        self.assertEqual(result["response"], "Đây là top ứng viên.")
        self.assertEqual(
            result["tool_calls"][0]["toolName"], "get_job_candidate_ranking"
        )
        self.assertEqual(result["source_job_app_ids"], [101])
        self.assertEqual(result["working_set"]["jobAppIds"], [101])
        self.assertEqual(result["state"]["workingSetJobAppIds"], [101])

    async def test_max_steps_exceeded_returns_warning(self) -> None:
        with patch.object(runtime.settings, "jobposting_agent_max_tool_steps", 1):
            with patch(
                "app.services.jobposting_agent_runtime._generate_with_fallback",
                new_callable=AsyncMock,
            ) as mock_gen:
                mock_gen.return_value = (
                    fake_response(
                        calls=[
                            {"name": "get_job_posting_context", "args": {}, "id": "fc1"}
                        ]
                    ),
                    "gemini-3.1-flash-lite",
                )
                with patch.dict(
                    runtime.TOOL_FUNCTIONS, {"get_job_posting_context": ok_tool}
                ):
                    result = await runtime.run_agent_turn(
                        conversation_id=uuid.uuid4(),
                        job_post_id=12,
                        hr_id=34,
                        prompt="Context",
                        state={},
                        history=[],
                    )

        self.assertTrue(
            any(w["type"] == "max_steps_reached" for w in result["warnings"])
        )
        self.assertIn("thu hẹp", result["response"])

    async def test_max_full_cv_loads_enforced(self) -> None:
        responses = [
            (
                fake_response(
                    calls=[
                        {
                            "name": "get_job_application_full_cv",
                            "args": {"job_app_id": 101},
                            "id": "fc1",
                        },
                        {
                            "name": "get_job_application_full_cv",
                            "args": {"job_app_id": 102},
                            "id": "fc2",
                        },
                    ]
                ),
                "gemini-3.1-flash-lite",
            ),
            (fake_response(text="Xong."), "gemini-3.1-flash-lite"),
        ]
        with patch.object(runtime.settings, "jobposting_agent_max_full_cv_loads", 1):
            with patch(
                "app.services.jobposting_agent_runtime._generate_with_fallback",
                new_callable=AsyncMock,
            ) as mock_gen:
                mock_gen.side_effect = responses
                with patch(
                    "app.services.jobposting_agent_runtime.jobposting_tools.validate_job_application_scope",
                    new_callable=AsyncMock,
                ) as mock_scope:
                    mock_scope.return_value = {"job_app_id": 101}
                    with patch.dict(
                        runtime.TOOL_FUNCTIONS, {"get_job_application_full_cv": ok_tool}
                    ):
                        result = await runtime.run_agent_turn(
                            conversation_id=uuid.uuid4(),
                            job_post_id=12,
                            hr_id=34,
                            prompt="Load CV",
                            state={},
                            history=[],
                        )

        self.assertEqual(result["tool_calls"][0]["status"], "success")
        self.assertEqual(result["tool_calls"][1]["status"], "error")
        self.assertIn("FULL_CV_LIMIT", result["tool_calls"][1]["resultSummary"])

    async def test_invalid_tool_name_blocked(self) -> None:
        responses = [
            (
                fake_response(
                    calls=[{"name": "delete_candidate", "args": {}, "id": "fc1"}]
                ),
                "gemini-3.1-flash-lite",
            ),
            (fake_response(text="Không thể gọi tool đó."), "gemini-3.1-flash-lite"),
        ]
        with patch(
            "app.services.jobposting_agent_runtime._generate_with_fallback",
            new_callable=AsyncMock,
        ) as mock_gen:
            mock_gen.side_effect = responses
            result = await runtime.run_agent_turn(
                conversation_id=uuid.uuid4(),
                job_post_id=12,
                hr_id=34,
                prompt="Delete",
                state={},
                history=[],
            )

        self.assertEqual(result["tool_calls"][0]["status"], "error")
        self.assertIn("INVALID_TOOL", result["tool_calls"][0]["resultSummary"])

    async def test_job_app_id_out_of_scope_blocked(self) -> None:
        responses = [
            (
                fake_response(
                    calls=[
                        {
                            "name": "get_job_application_summary",
                            "args": {"job_app_id": 999},
                            "id": "fc1",
                        }
                    ]
                ),
                "gemini-3.1-flash-lite",
            ),
            (fake_response(text="Không có quyền."), "gemini-3.1-flash-lite"),
        ]
        with patch(
            "app.services.jobposting_agent_runtime._generate_with_fallback",
            new_callable=AsyncMock,
        ) as mock_gen:
            mock_gen.side_effect = responses
            with patch(
                "app.services.jobposting_agent_runtime.jobposting_tools.validate_job_application_scope",
                new_callable=AsyncMock,
            ) as mock_scope:
                mock_scope.return_value = None
                with patch.dict(
                    runtime.TOOL_FUNCTIONS, {"get_job_application_summary": ok_tool}
                ):
                    result = await runtime.run_agent_turn(
                        conversation_id=uuid.uuid4(),
                        job_post_id=12,
                        hr_id=34,
                        prompt="Summary",
                        state={},
                        history=[],
                    )

        self.assertEqual(result["tool_calls"][0]["status"], "error")
        self.assertIn("job_app_id không thuộc", result["tool_calls"][0]["errorMsg"])

    async def test_too_large_compare_calls_count_and_returns_narrowing_message(
        self,
    ) -> None:
        with patch(
            "app.services.jobposting_agent_runtime.jobposting_tools.count_job_applications",
            new_callable=AsyncMock,
        ) as mock_count:
            mock_count.return_value = {
                "ok": True,
                "data": {"count": 150, "job_app_ids": []},
                "source": {},
                "warnings": [],
                "error": None,
            }
            with patch(
                "app.services.jobposting_agent_runtime._generate_with_fallback",
                new_callable=AsyncMock,
            ) as mock_gen:
                result = await runtime.run_agent_turn(
                    conversation_id=uuid.uuid4(),
                    job_post_id=12,
                    hr_id=34,
                    prompt="So sánh chi tiết tất cả ứng viên",
                    state={},
                    history=[],
                )

        mock_count.assert_awaited_once()
        mock_gen.assert_not_called()
        self.assertEqual(result["tool_calls"][0]["toolName"], "count_job_applications")
        self.assertTrue(any(w["type"] == "too_large_set" for w in result["warnings"]))

    async def test_tool_result_truncation_prevents_oversized_log_output(self) -> None:
        responses = [
            (
                fake_response(
                    calls=[{"name": "get_job_posting_context", "args": {}, "id": "fc1"}]
                ),
                "gemini-3.1-flash-lite",
            ),
            (fake_response(text="Xong."), "gemini-3.1-flash-lite"),
        ]
        with patch.object(
            runtime.settings, "jobposting_agent_max_tool_result_chars", 300
        ):
            with patch(
                "app.services.jobposting_agent_runtime._generate_with_fallback",
                new_callable=AsyncMock,
            ) as mock_gen:
                mock_gen.side_effect = responses
                with patch.dict(
                    runtime.TOOL_FUNCTIONS, {"get_job_posting_context": large_tool}
                ):
                    result = await runtime.run_agent_turn(
                        conversation_id=uuid.uuid4(),
                        job_post_id=12,
                        hr_id=34,
                        prompt="Context",
                        state={},
                        history=[],
                    )

        self.assertLess(len(result["tool_calls"][0]["resultSummary"]), 500)
        self.assertTrue(any(w["type"] == "truncated" for w in result["warnings"]))

    async def test_runtime_result_matches_ws2_shape(self) -> None:
        with patch(
            "app.services.jobposting_agent_runtime._generate_with_fallback",
            new_callable=AsyncMock,
        ) as mock_gen:
            mock_gen.return_value = (
                fake_response(text="Xin chào."),
                "gemini-3.1-flash-lite",
            )
            result = await runtime.run_agent_turn(
                conversation_id=uuid.uuid4(),
                job_post_id=12,
                hr_id=34,
                prompt="Hello",
                state={},
                history=[],
            )

        expected = {
            "response",
            "model",
            "steps_used",
            "tool_calls",
            "source_job_app_ids",
            "working_set",
            "latency_ms",
            "warnings",
            "state",
        }
        self.assertEqual(set(result.keys()), expected)


if __name__ == "__main__":
    unittest.main()
