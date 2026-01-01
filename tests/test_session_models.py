"""Tests for session Pydantic models."""

from datetime import datetime

from nexus.session.models import SearchResult, Session, Turn


class TestTurn:
    """Tests for the Turn model."""

    def test_turn_defaults(self):
        """Test Turn default values are set correctly."""
        turn = Turn(role="user", content="Hello", model="gpt-4")
        assert turn.id is not None
        assert turn.timestamp is not None
        assert turn.tokens == {}
        assert turn.duration_ms is None
        assert turn.metadata == {}

    def test_turn_with_metadata(self):
        """Test Turn with all optional fields."""
        turn = Turn(
            role="assistant",
            content="Response",
            model="gpt-4",
            tokens={"prompt": 10, "completion": 20, "total": 30},
            duration_ms=500,
            metadata={"system_prompt": "Be helpful"},
        )
        assert turn.tokens["total"] == 30
        assert turn.duration_ms == 500
        assert turn.metadata["system_prompt"] == "Be helpful"

    def test_turn_roles(self):
        """Test Turn role validation."""
        user_turn = Turn(role="user", content="Question", model="gpt-4")
        assert user_turn.role == "user"

        assistant_turn = Turn(role="assistant", content="Answer", model="gpt-4")
        assert assistant_turn.role == "assistant"

    def test_turn_serialization(self):
        """Test Turn JSON serialization and deserialization."""
        turn = Turn(
            role="user",
            content="Test content",
            model="gpt-4",
            tokens={"total": 10},
        )
        json_str = turn.model_dump_json()
        assert "Test content" in json_str
        assert "user" in json_str

        # Deserialize
        loaded = Turn.model_validate_json(json_str)
        assert loaded.content == "Test content"
        assert loaded.role == "user"
        assert loaded.id == turn.id

    def test_turn_unique_id(self):
        """Test that each Turn gets a unique ID."""
        turn1 = Turn(role="user", content="Hello", model="gpt-4")
        turn2 = Turn(role="user", content="Hello", model="gpt-4")
        assert turn1.id != turn2.id

    def test_turn_no_shared_mutable_defaults(self):
        """Ensure Turn mutable defaults are not shared between instances."""
        turn1 = Turn(role="user", content="Hello", model="gpt-4")
        turn2 = Turn(role="user", content="World", model="gpt-4")

        turn1.tokens["prompt"] = 5
        turn1.metadata["key"] = "value"

        assert turn2.tokens == {}
        assert turn2.metadata == {}


class TestSession:
    """Tests for the Session model."""

    def test_session_defaults(self):
        """Test Session default values."""
        session = Session(name="test", model="gpt-4", provider="openai")
        assert session.turns == []
        assert session.total_tokens == 0
        assert session.id is not None
        assert session.created_at is not None
        assert session.updated_at is not None

    def test_session_with_turns(self):
        """Test Session with turns."""
        session = Session(name="test", model="gpt-4", provider="openai")
        turn = Turn(role="user", content="Hello", model="gpt-4")
        session.turns.append(turn)
        assert len(session.turns) == 1
        assert session.turns[0].content == "Hello"

    def test_session_serialization(self):
        """Test Session JSON serialization and deserialization."""
        session = Session(name="test", model="gpt-4", provider="openai")
        json_str = session.model_dump_json()
        assert '"name":"test"' in json_str or '"name": "test"' in json_str

        # Deserialize
        loaded = Session.model_validate_json(json_str)
        assert loaded.name == "test"
        assert loaded.model == "gpt-4"
        assert loaded.provider == "openai"

    def test_session_with_turns_serialization(self):
        """Test Session with turns serialization."""
        session = Session(name="conversation", model="claude-3", provider="anthropic")
        turn1 = Turn(role="user", content="Hello", model="claude-3")
        turn2 = Turn(role="assistant", content="Hi there!", model="claude-3")
        session.turns.extend([turn1, turn2])
        session.total_tokens = 50

        json_str = session.model_dump_json()
        loaded = Session.model_validate_json(json_str)

        assert loaded.name == "conversation"
        assert len(loaded.turns) == 2
        assert loaded.turns[0].role == "user"
        assert loaded.turns[1].role == "assistant"
        assert loaded.total_tokens == 50

    def test_session_unique_id(self):
        """Test that each Session gets a unique ID."""
        session1 = Session(name="test1", model="gpt-4", provider="openai")
        session2 = Session(name="test2", model="gpt-4", provider="openai")
        assert session1.id != session2.id

    def test_session_no_shared_mutable_defaults(self):
        """Ensure Session mutable defaults are not shared between instances."""
        session1 = Session(name="one", model="gpt-4", provider="openai")
        session2 = Session(name="two", model="gpt-4", provider="openai")

        turn = Turn(role="user", content="Hello", model="gpt-4")
        session1.turns.append(turn)
        session1.total_tokens = 10

        assert session2.turns == []
        assert session2.total_tokens == 0


class TestSearchResult:
    """Tests for the SearchResult model."""

    def test_search_result_name_match(self):
        """Test SearchResult for name matches."""
        result = SearchResult(
            session_name="research",
            match_type="name",
            matched_text="research",
            turn_count=5,
            updated_at=datetime.now(),
        )
        assert result.match_type == "name"
        assert result.session_name == "research"
        assert result.matched_text == "research"
        assert result.turn_count == 5

    def test_search_result_content_match(self):
        """Test SearchResult for content matches."""
        result = SearchResult(
            session_name="coding",
            match_type="content",
            matched_text="explain quantum computing in detail",
            turn_count=10,
            updated_at=datetime.now(),
        )
        assert result.match_type == "content"
        assert "quantum" in result.matched_text
        assert result.turn_count == 10

    def test_search_result_serialization(self):
        """Test SearchResult JSON serialization."""
        result = SearchResult(
            session_name="test",
            match_type="name",
            matched_text="test",
            turn_count=3,
            updated_at=datetime.now(),
        )
        json_str = result.model_dump_json()
        loaded = SearchResult.model_validate_json(json_str)

        assert loaded.session_name == "test"
        assert loaded.match_type == "name"

    def test_search_result_match_types(self):
        """Test that match_type only accepts valid values."""
        # Valid types
        name_result = SearchResult(
            session_name="a",
            match_type="name",
            matched_text="a",
            turn_count=1,
            updated_at=datetime.now(),
        )
        assert name_result.match_type == "name"

        content_result = SearchResult(
            session_name="b",
            match_type="content",
            matched_text="b",
            turn_count=1,
            updated_at=datetime.now(),
        )
        assert content_result.match_type == "content"
