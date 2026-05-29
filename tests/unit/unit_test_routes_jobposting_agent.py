import unittest
import uuid
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from app.main import app
from app.models.jobposting_agent import JobPostingAgentQueryRequest

client = TestClient(app)


class JobPostingAgentRoutesTests(unittest.TestCase):

    def test_request_model_has_no_model_mode(self) -> None:
        # Verify the model schema fields
        fields = JobPostingAgentQueryRequest.model_fields
        self.assertIn("jobPostId", fields)
        self.assertIn("hrId", fields)
        self.assertIn("prompt", fields)
        self.assertIn("conversationId", fields)
        self.assertNotIn("modelMode", fields)

    @patch("app.api.routes_jobposting_agent.list_conversations", new_callable=AsyncMock)
    def test_get_conversations_success(self, mock_list) -> None:
        mock_list.return_value = [
            {
                "conversationid": uuid.uuid4(),
                "jobpostid": 12,
                "hrid": 34,
                "title": "Topic A",
                "createdat": "2026-05-29T10:00:00",
                "lastmessageat": "2026-05-29T10:05:00",
                "messagecount": 2,
                "isarchived": False,
            }
        ]

        response = client.get(
            "/v2/agent/job-posting/conversations?jobPostId=12&hrId=34"
        )
        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertEqual(len(json_data), 1)
        self.assertEqual(json_data[0]["title"], "Topic A")
        self.assertEqual(json_data[0]["messageCount"], 2)

    @patch("app.api.routes_jobposting_agent.get_conversation", new_callable=AsyncMock)
    @patch("app.api.routes_jobposting_agent.get_messages", new_callable=AsyncMock)
    def test_get_messages_success(self, mock_get_msgs, mock_get_conv) -> None:
        conv_id = uuid.uuid4()
        mock_get_conv.return_value = {"conversationid": conv_id}
        mock_get_msgs.return_value = [
            {
                "messageid": 1,
                "role": "user",
                "content": "Hello",
                "createdat": "2026-05-29T10:00:00",
            },
            {
                "messageid": 2,
                "role": "assistant",
                "content": "Hi",
                "toolname": "get_job_posting_context",
                "toolcallid": "call_123",
                "model": "gemini-3.1-flash-lite",
                "latencyms": 150,
                "createdat": "2026-05-29T10:00:02",
            },
        ]

        response = client.get(f"/v2/agent/job-posting/conversations/{conv_id}/messages")
        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertEqual(len(json_data), 2)
        self.assertEqual(json_data[0]["role"], "user")
        self.assertEqual(json_data[1]["toolName"], "get_job_posting_context")

    @patch("app.api.routes_jobposting_agent.get_conversation", new_callable=AsyncMock)
    def test_get_messages_not_found(self, mock_get_conv) -> None:
        conv_id = uuid.uuid4()
        mock_get_conv.return_value = None

        response = client.get(f"/v2/agent/job-posting/conversations/{conv_id}/messages")
        self.assertEqual(response.status_code, 404)

    @patch("app.api.routes_jobposting_agent.get_conversation", new_callable=AsyncMock)
    @patch(
        "app.api.routes_jobposting_agent.rename_conversation", new_callable=AsyncMock
    )
    def test_rename_conversation_success(self, mock_rename, mock_get_conv) -> None:
        conv_id = uuid.uuid4()
        mock_get_conv.side_effect = [
            {
                "conversationid": conv_id,
                "hrid": 34,
                "lastmessageat": "2026-05-29T10:00:00",
            },
            {
                "conversationid": conv_id,
                "hrid": 34,
                "lastmessageat": "2026-05-29T10:10:00",
            },
        ]

        response = client.patch(
            f"/v2/agent/job-posting/conversations/{conv_id}?hrId=34",
            json={"title": "Updated Topic"},
        )
        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertEqual(json_data["title"], "Updated Topic")
        self.assertEqual(json_data["updatedAt"], "2026-05-29T10:10:00")
        mock_rename.assert_called_once_with(conv_id, "Updated Topic")

    def test_rename_conversation_invalid_title(self) -> None:
        conv_id = uuid.uuid4()
        response = client.patch(
            f"/v2/agent/job-posting/conversations/{conv_id}", json={"title": ""}
        )
        self.assertEqual(
            response.status_code, 422
        )  # FastAPI validation error for empty field (min_length=1)

        response = client.patch(
            f"/v2/agent/job-posting/conversations/{conv_id}", json={"title": "a" * 201}
        )
        self.assertEqual(
            response.status_code, 422
        )  # FastAPI validation error for too long field

    @patch("app.api.routes_jobposting_agent.get_conversation", new_callable=AsyncMock)
    def test_rename_conversation_forbidden_owner(self, mock_get_conv) -> None:
        conv_id = uuid.uuid4()
        mock_get_conv.return_value = {"conversationid": conv_id, "hrid": 99}

        response = client.patch(
            f"/v2/agent/job-posting/conversations/{conv_id}?hrId=34",
            json={"title": "New Title"},
        )
        self.assertEqual(response.status_code, 403)

    @patch("app.api.routes_jobposting_agent.get_conversation", new_callable=AsyncMock)
    @patch(
        "app.api.routes_jobposting_agent.archive_conversation", new_callable=AsyncMock
    )
    def test_delete_conversation_success(self, mock_archive, mock_get_conv) -> None:
        conv_id = uuid.uuid4()
        mock_get_conv.return_value = {"conversationid": conv_id, "hrid": 34}

        response = client.delete(
            f"/v2/agent/job-posting/conversations/{conv_id}?hrId=34"
        )
        self.assertEqual(response.status_code, 204)
        mock_archive.assert_called_once_with(conv_id)

    @patch("app.api.routes_jobposting_agent.get_conversation", new_callable=AsyncMock)
    def test_delete_conversation_forbidden(self, mock_get_conv) -> None:
        conv_id = uuid.uuid4()
        mock_get_conv.return_value = {"conversationid": conv_id, "hrid": 99}

        response = client.delete(
            f"/v2/agent/job-posting/conversations/{conv_id}?hrId=34"
        )
        self.assertEqual(response.status_code, 403)

    @patch("app.services.jobposting_agent_query.acquire_conn")
    @patch(
        "app.services.jobposting_agent_query.run_agent_turn_boundary",
        new_callable=AsyncMock,
    )
    @patch(
        "app.services.jobposting_agent_query.create_conversation",
        new_callable=AsyncMock,
    )
    @patch("app.services.jobposting_agent_query.insert_message", new_callable=AsyncMock)
    @patch(
        "app.services.jobposting_agent_query.insert_tool_call_log",
        new_callable=AsyncMock,
    )
    @patch("app.services.jobposting_agent_query.save_state", new_callable=AsyncMock)
    def test_query_agent_creates_conv_and_returns_payload(
        self, mock_save_state, mock_log, mock_msg, mock_create, mock_run, mock_acq
    ) -> None:
        # Mock HR and Job existing under same company (compId=100)
        mock_conn = AsyncMock()
        mock_conn.fetchrow.side_effect = [
            {"compid": 100},  # HR compId
            {"compid": 100},  # Job compId
        ]

        class MockAcquire:
            async def __aenter__(self):
                return mock_conn

            async def __aexit__(self, exc_type, exc, tb):
                pass

        mock_acq.return_value = MockAcquire()

        conv_id = uuid.uuid4()
        mock_create.return_value = conv_id
        mock_msg.return_value = 555  # Message ID

        # Mock runtime response
        mock_run.return_value = {
            "response": "Here are your candidates.",
            "model": "gemini-3.1-flash-lite",
            "steps_used": 1,
            "tool_calls": [
                {
                    "step": 1,
                    "toolName": "get_job_candidate_ranking",
                    "args": {"limit": 10},
                    "resultSummary": "10 candidates found",
                    "status": "success",
                    "latencyMs": 100,
                }
            ],
            "source_job_app_ids": [101, 102],
            "working_set": {
                "jobAppIds": [101, 102],
                "label": "Top Candidates",
            },
            "latency_ms": 1200,
            "warnings": [
                {"type": "data_quality", "message": "Raw location format mismatch"}
            ],
            "state": {"workingSetJobAppIds": [101, 102]},
        }

        response = client.post(
            "/v2/agent/job-posting/query",
            json={
                "jobPostId": 12,
                "hrId": 34,
                "prompt": "Get top candidates for me",
            },
        )
        self.assertEqual(response.status_code, 200)
        json_data = response.json()
        self.assertEqual(json_data["conversationId"], str(conv_id))
        self.assertEqual(json_data["response"], "Here are your candidates.")
        self.assertEqual(len(json_data["toolCalls"]), 1)
        self.assertEqual(json_data["workingSet"]["label"], "Top Candidates")
        self.assertEqual(len(json_data["warnings"]), 1)

    @patch(
        "app.api.routes_jobposting_agent.process_jobposting_agent_query",
        new_callable=AsyncMock,
    )
    def test_query_agent_not_implemented_returns_503(self, mock_query) -> None:
        mock_query.side_effect = NotImplementedError(
            "JobPosting Agent Runtime is not implemented yet."
        )

        response = client.post(
            "/v2/agent/job-posting/query",
            json={
                "jobPostId": 12,
                "hrId": 34,
                "prompt": "Get top candidates for me",
            },
        )
        self.assertEqual(response.status_code, 503)
        self.assertIn("Dịch vụ AI chưa sẵn sàng", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
