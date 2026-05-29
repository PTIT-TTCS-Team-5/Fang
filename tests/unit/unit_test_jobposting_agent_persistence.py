import unittest
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, patch

from app.services.jobposting_agent_persistence import (
    archive_conversation,
    create_conversation,
    get_conversation,
    get_messages,
    get_state,
    insert_message,
    insert_tool_call_log,
    list_conversations,
    rename_conversation,
    save_state,
)


class MockTransaction:
    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        pass


class MockConnection:
    def __init__(self):
        self.fetchval = AsyncMock()
        self.fetchrow = AsyncMock()
        self.fetch = AsyncMock()
        self.execute = AsyncMock()
        self.trans = MockTransaction()

    def transaction(self):
        return self.trans


class MockAcquireConn:
    def __init__(self, conn):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, exc_type, exc, tb):
        pass


class JobPostingAgentPersistenceTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.conn = MockConnection()
        self.acquire_patch = patch(
            "app.services.jobposting_agent_persistence.acquire_conn",
            return_value=MockAcquireConn(self.conn),
        )
        self.acquire_patch.start()

    def tearDown(self):
        self.acquire_patch.stop()

    async def test_create_conversation_inserts_conv_and_state(self) -> None:
        expected_uuid = uuid.uuid4()
        self.conn.fetchval.return_value = expected_uuid

        conv_id = await create_conversation(
            job_post_id=12, hr_id=34, title="Test Thread"
        )

        self.assertEqual(conv_id, expected_uuid)
        # Check first query inserted conversation
        self.conn.fetchval.assert_called_once()
        self.assertIn(
            "INSERT INTO AIJOBPOSTINGCHATCONVERSATION",
            self.conn.fetchval.call_args[0][0],
        )
        self.assertEqual(self.conn.fetchval.call_args[0][1], 12)
        self.assertEqual(self.conn.fetchval.call_args[0][2], 34)
        self.assertEqual(self.conn.fetchval.call_args[0][3], "Test Thread")

        # Check second query inserted empty state
        self.conn.execute.assert_called_once()
        self.assertIn(
            "INSERT INTO AIJOBPOSTINGCHATSTATE", self.conn.execute.call_args[0][0]
        )
        self.assertEqual(self.conn.execute.call_args[0][1], conv_id)

    async def test_get_conversation_returns_row_as_dict(self) -> None:
        conv_uuid = uuid.uuid4()
        mock_row = {
            "conversationid": conv_uuid,
            "jobpostid": 12,
            "hrid": 34,
            "title": "A Thread",
            "createdat": datetime.now(),
            "lastmessageat": datetime.now(),
            "isarchived": False,
        }
        self.conn.fetchrow.return_value = mock_row

        res = await get_conversation(conv_uuid)

        self.assertEqual(res, mock_row)
        self.conn.fetchrow.assert_called_once_with(unittest.mock.ANY, conv_uuid)

    async def test_list_conversations_filters_and_includes_message_count(self) -> None:
        conv_uuid = uuid.uuid4()
        mock_rows = [
            {
                "conversationid": conv_uuid,
                "jobpostid": 12,
                "hrid": 34,
                "title": "A Thread",
                "createdat": datetime.now(),
                "lastmessageat": datetime.now(),
                "isarchived": False,
                "messagecount": 5,
            }
        ]
        self.conn.fetch.return_value = mock_rows

        res = await list_conversations(hr_id=34, job_post_id=12)

        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["messagecount"], 5)
        self.assertIn(
            "c.hrId = $1 AND c.jobPostId = $2 AND c.isArchived = FALSE",
            self.conn.fetch.call_args[0][0],
        )
        self.assertIn("role IN ('user', 'assistant')", self.conn.fetch.call_args[0][0])

    async def test_rename_conversation_updates_title_and_touches(self) -> None:
        conv_uuid = uuid.uuid4()
        await rename_conversation(conv_uuid, "New Title")

        self.conn.execute.assert_called_once()
        self.assertIn(
            "UPDATE AIJOBPOSTINGCHATCONVERSATION", self.conn.execute.call_args[0][0]
        )
        self.assertEqual(self.conn.execute.call_args[0][1], conv_uuid)
        self.assertEqual(self.conn.execute.call_args[0][2], "New Title")

    async def test_archive_conversation_sets_is_archived_true(self) -> None:
        conv_uuid = uuid.uuid4()
        await archive_conversation(conv_uuid)

        self.conn.execute.assert_called_once()
        self.assertIn("isArchived = TRUE", self.conn.execute.call_args[0][0])
        self.assertEqual(self.conn.execute.call_args[0][1], conv_uuid)

    async def test_insert_message_creates_row_and_touches(self) -> None:
        conv_uuid = uuid.uuid4()
        self.conn.fetchval.return_value = 999

        with patch(
            "app.services.jobposting_agent_persistence.touch_conversation"
        ) as mock_touch:
            msg_id = await insert_message(
                conversation_id=conv_uuid,
                role="user",
                content="Hello World",
                tool_name="some_tool",
                tool_call_id="call_1",
            )
            self.assertEqual(msg_id, 999)
            mock_touch.assert_called_once_with(conv_uuid)

        self.conn.fetchval.assert_called_once()
        self.assertIn(
            "INSERT INTO AIJOBPOSTINGCHATMESSAGE", self.conn.fetchval.call_args[0][0]
        )

    async def test_get_messages_filters_system_and_tool_correctly(self) -> None:
        conv_uuid = uuid.uuid4()
        self.conn.fetch.return_value = []

        # Default: hide system, include tool
        await get_messages(conv_uuid)
        query_default = self.conn.fetch.call_args[0][0]
        self.assertIn("role != 'system'", query_default)
        self.assertNotIn("role NOT IN ('tool_call', 'tool_result')", query_default)

        # include_system=True, include_tool=False
        await get_messages(conv_uuid, include_system=True, include_tool=False)
        query_custom = self.conn.fetch.call_args[0][0]
        self.assertNotIn("role != 'system'", query_custom)
        self.assertIn("role NOT IN ('tool_call', 'tool_result')", query_custom)

    async def test_save_and_get_state(self) -> None:
        conv_uuid = uuid.uuid4()
        mock_state = {"workingSetJobAppIds": [1, 2, 3]}

        await save_state(conv_uuid, mock_state)
        self.conn.execute.assert_called_once()
        # asyncpg JSONB codec expects a Python dict, not a pre-serialised string
        self.assertEqual(self.conn.execute.call_args[0][2], mock_state)

        self.conn.fetchval.return_value = mock_state
        state_res = await get_state(conv_uuid)
        self.assertEqual(state_res, mock_state)

    async def test_insert_tool_call_log_resolves_tool_id(self) -> None:
        conv_uuid = uuid.uuid4()
        self.conn.fetchval.side_effect = [
            100,
            1000,
        ]  # first fetches toolId, second inserts and returns logId

        log_id = await insert_tool_call_log(
            conversation_id=conv_uuid,
            message_id=55,
            job_post_id=12,
            hr_id=34,
            tool_name="get_job_candidate_ranking",
            tool_input={"limit": 10},
            tool_output_meta={"summary": "Ranked 10 candidates"},
        )

        self.assertEqual(log_id, 1000)
        self.assertEqual(self.conn.fetchval.call_count, 2)
        # Verify first call was tool name lookup
        self.assertIn(
            "SELECT toolId FROM AIJOBPOSTINGTOOL WHERE toolName = $1",
            self.conn.fetchval.call_args_list[0][0][0],
        )
        # Verify second call was insert log
        self.assertIn(
            "INSERT INTO AIJOBPOSTINGTOOLCALLLOG",
            self.conn.fetchval.call_args_list[1][0][0],
        )
        # Verify JSONB columns receive dicts, not pre-serialised strings (asyncpg handles serialisation)
        insert_args = self.conn.fetchval.call_args_list[1][0]
        self.assertEqual(insert_args[7], {"limit": 10})  # toolInput param
        self.assertEqual(
            insert_args[8], {"summary": "Ranked 10 candidates"}
        )  # toolOutputMeta param


if __name__ == "__main__":
    unittest.main()
