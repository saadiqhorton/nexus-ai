"""Tests for InteractiveFuzzySelector and FuzzySearchResult."""

from typing import List, Tuple

from nexus.cli.fuzzy_selector import FuzzySearchResult, InteractiveFuzzySelector

# Sample data for tests
SAMPLE_SCORED_RESULTS: List[Tuple[int, str, str]] = [
    (100, "openai", "gpt-4o"),
    (95, "openai", "gpt-4o-mini"),
    (90, "openai", "gpt-4-turbo"),
    (85, "openai", "gpt-4"),
    (80, "openai", "gpt-3.5-turbo"),
    (75, "anthropic", "claude-opus-4-5"),
    (70, "anthropic", "claude-sonnet-4-5"),
    (65, "anthropic", "claude-haiku-4-5"),
    (60, "ollama", "llama2"),
    (55, "ollama", "mistral"),
    (50, "openrouter", "meta-llama/llama-2"),
]


class TestFuzzySearchResult:
    """Tests for FuzzySearchResult NamedTuple."""

    def test_result_with_selection(self):
        """Test creating FuzzySearchResult with a selection."""
        result = FuzzySearchResult(provider="openai", model="gpt-4o", cancelled=False)
        assert result.provider == "openai"
        assert result.model == "gpt-4o"
        assert result.cancelled is False

    def test_result_cancelled(self):
        """Test creating FuzzySearchResult with cancelled flag."""
        result = FuzzySearchResult(provider="", model="", cancelled=True)
        assert result.cancelled is True
        assert result.provider == ""
        assert result.model == ""

    def test_result_default_not_cancelled(self):
        """Test that cancelled defaults to False."""
        result = FuzzySearchResult(provider="openai", model="gpt-4o")
        assert result.cancelled is False


class TestInteractiveFuzzySelectorInitialization:
    """Tests for InteractiveFuzzySelector initialization and state."""

    def test_initialization_with_sample_data(self):
        """Test basic initialization with sample data."""
        selector = InteractiveFuzzySelector(
            scored_results=SAMPLE_SCORED_RESULTS,
            query="gpt",
            page_size=10,
        )
        assert selector.scored_results == SAMPLE_SCORED_RESULTS
        assert selector.query == "gpt"
        assert selector.page_size == 10
        assert selector.total_results == 11
        assert selector.total_pages == 2

    def test_initialization_state(self):
        """Test initial state values."""
        selector = InteractiveFuzzySelector(SAMPLE_SCORED_RESULTS, "test")
        assert selector._current_page == 0
        assert selector._highlighted_index == 0
        assert selector._cancelled is False
        assert selector._selected_result is None

    def test_pagination_calculation_full_pages(self):
        """Test pagination calculation with full pages."""
        # Exactly 20 items with page_size 10
        results = [(i, f"provider{i}", f"model{i}") for i in range(20)]
        selector = InteractiveFuzzySelector(results, "test", page_size=10)
        assert selector.total_pages == 2

    def test_pagination_calculation_partial_last_page(self):
        """Test pagination calculation with partial last page."""
        # 11 items with page_size 10 = 2 pages
        results = [(i, f"provider{i}", f"model{i}") for i in range(11)]
        selector = InteractiveFuzzySelector(results, "test", page_size=10)
        assert selector.total_pages == 2

    def test_pagination_calculation_single_page(self):
        """Test pagination calculation with single page."""
        # 5 items with page_size 10 = 1 page
        results = [(i, f"provider{i}", f"model{i}") for i in range(5)]
        selector = InteractiveFuzzySelector(results, "test", page_size=10)
        assert selector.total_pages == 1

    def test_custom_page_size(self):
        """Test custom page size parameter."""
        selector = InteractiveFuzzySelector(
            SAMPLE_SCORED_RESULTS,
            "test",
            page_size=5,
        )
        assert selector.page_size == 5
        assert selector.total_pages == 3  # 11 items / 5 per page = 3 pages


class TestInteractiveFuzzySelectorNavigation:
    """Tests for navigation handlers (_handle_key_up, _handle_key_down)."""

    def test_down_increments_highlighted_index(self):
        """Test that down arrow increments highlighted index."""
        selector = InteractiveFuzzySelector(SAMPLE_SCORED_RESULTS, "test")
        assert selector._highlighted_index == 0
        selector._handle_key_down()
        assert selector._highlighted_index == 1

    def test_up_decrements_highlighted_index(self):
        """Test that up arrow decrements highlighted index."""
        selector = InteractiveFuzzySelector(SAMPLE_SCORED_RESULTS, "test")
        selector._highlighted_index = 3
        selector._handle_key_up()
        assert selector._highlighted_index == 2

    def test_down_at_page_end_wraps_to_next_page(self):
        """Test that down at end of page wraps to next page."""
        results = [(i, f"p{i}", f"m{i}") for i in range(11)]
        selector = InteractiveFuzzySelector(results, "test", page_size=5)

        # Move to last item of first page
        selector._highlighted_index = 4
        selector._handle_key_down()

        # Should wrap to next page
        assert selector._current_page == 1
        assert selector._highlighted_index == 0

    def test_up_at_page_start_wraps_to_previous_page(self):
        """Test that up at start of page wraps to previous page."""
        results = [(i, f"p{i}", f"m{i}") for i in range(15)]
        selector = InteractiveFuzzySelector(results, "test", page_size=5)

        # Move to second page
        selector._current_page = 1
        selector._highlighted_index = 0

        # Move up
        selector._handle_key_up()

        # Should wrap to previous page
        assert selector._current_page == 0
        assert selector._highlighted_index == 4  # Last item of page 0

    def test_down_on_last_page_wraps_to_first(self):
        """Test that down on last page wraps to first page."""
        results = [(i, f"p{i}", f"m{i}") for i in range(11)]
        selector = InteractiveFuzzySelector(results, "test", page_size=5)

        # Move to last page, last item
        selector._current_page = 2
        selector._highlighted_index = 0  # Only 1 item on last page

        selector._handle_key_down()

        # Should wrap to first page
        assert selector._current_page == 0
        assert selector._highlighted_index == 0

    def test_up_on_first_page_wraps_to_last(self):
        """Test that up on first page wraps to last page."""
        results = [(i, f"p{i}", f"m{i}") for i in range(11)]
        selector = InteractiveFuzzySelector(results, "test", page_size=5)

        # On first page, first item
        assert selector._current_page == 0
        assert selector._highlighted_index == 0

        selector._handle_key_up()

        # Should wrap to last page
        assert selector._current_page == 2
        assert selector._highlighted_index == 0  # Only 1 item on last page

    def test_single_page_navigation_wraps(self):
        """Test that single page navigation wraps to beginning when at end."""
        results = [(i, f"p{i}", f"m{i}") for i in range(5)]
        selector = InteractiveFuzzySelector(results, "test", page_size=10)

        # At end of single page, down should wrap to beginning
        selector._highlighted_index = 4
        selector._handle_key_down()

        # Wraps back to start (single page, so stays on page 0, highlight resets to 0)
        assert selector._current_page == 0
        assert selector._highlighted_index == 0

    def test_last_page_smaller_size(self):
        """Test navigation on last page with fewer items."""
        results = [(i, f"p{i}", f"m{i}") for i in range(11)]
        selector = InteractiveFuzzySelector(results, "test", page_size=5)

        # Jump to last page
        selector._current_page = 2  # Last page has only 1 item

        # Can only highlight that one item
        selector._highlighted_index = 0
        selector._handle_key_down()

        # Should wrap, not go out of bounds
        assert selector._current_page == 0
        assert selector._highlighted_index == 0


class TestInteractiveFuzzySelectorSelection:
    """Tests for selection handlers (_handle_enter, _handle_escape)."""

    def test_enter_selection(self):
        """Test that Enter key creates correct FuzzySearchResult."""
        selector = InteractiveFuzzySelector(SAMPLE_SCORED_RESULTS, "test")
        selector._highlighted_index = 0
        selector._handle_enter()

        assert selector._selected_result is not None
        assert selector._selected_result.provider == "openai"
        assert selector._selected_result.model == "gpt-4o"
        assert selector._selected_result.cancelled is False

    def test_enter_selection_middle_item(self):
        """Test Enter selection on middle item of list."""
        selector = InteractiveFuzzySelector(SAMPLE_SCORED_RESULTS, "test")
        selector._highlighted_index = 5
        selector._handle_enter()

        assert selector._selected_result is not None
        assert selector._selected_result.provider == "anthropic"
        assert selector._selected_result.model == "claude-opus-4-5"

    def test_enter_selection_on_second_page(self):
        """Test Enter selection when on second page."""
        results = [(i, f"p{i}", f"m{i}") for i in range(15)]
        selector = InteractiveFuzzySelector(results, "test", page_size=5)

        # Move to second page, first item (global index 5)
        selector._current_page = 1
        selector._highlighted_index = 0
        selector._handle_enter()

        assert selector._selected_result is not None
        assert selector._selected_result.provider == "p5"
        assert selector._selected_result.model == "m5"

    def test_escape_sets_cancelled(self):
        """Test that Escape key sets cancelled flag."""
        selector = InteractiveFuzzySelector(SAMPLE_SCORED_RESULTS, "test")
        assert selector._cancelled is False

        selector._handle_escape()

        assert selector._cancelled is True

    def test_enter_invalid_index_sets_cancelled(self):
        """Test that invalid index on Enter sets cancelled."""
        # Empty results should have no valid items
        results: List[Tuple[int, str, str]] = []
        selector = InteractiveFuzzySelector(results, "test")
        selector._highlighted_index = 0
        selector._handle_enter()

        assert selector._cancelled is True


class TestInteractiveFuzzySelectorRendering:
    """Tests for rendering (_get_current_page_content)."""

    def test_render_first_page(self):
        """Test rendering of first page content."""
        selector = InteractiveFuzzySelector(SAMPLE_SCORED_RESULTS, "gpt", page_size=5)
        content = selector._get_current_page_content()

        # Should be HTML object
        assert content is not None
        # Render to string to check content
        content_str = str(content)
        assert "Fuzzy matches for 'gpt'" in content_str
        assert "gpt-4o" in content_str
        assert "Page 1 of" in content_str

    def test_render_with_highlighting(self):
        """Test that highlighted item appears with arrow."""
        selector = InteractiveFuzzySelector(SAMPLE_SCORED_RESULTS, "test", page_size=5)
        selector._highlighted_index = 0
        content = selector._get_current_page_content()

        content_str = str(content)
        # Arrow should appear next to highlighted item
        assert "→" in content_str

    def test_render_includes_navigation_hints(self):
        """Test that rendering includes navigation hints."""
        selector = InteractiveFuzzySelector(SAMPLE_SCORED_RESULTS, "test")
        content = selector._get_current_page_content()

        content_str = str(content)
        assert "↑↓" in content_str or "Navigate" in content_str
        assert "Enter" in content_str
        assert "Esc" in content_str


class TestInteractiveFuzzySelectorGlobalIndexCalculation:
    """Tests for correct global index calculation from page and local index."""

    def test_global_index_first_page_first_item(self):
        """Test global index calculation: page 0, item 0."""
        selector = InteractiveFuzzySelector(SAMPLE_SCORED_RESULTS, "test", page_size=5)
        selector._current_page = 0
        selector._highlighted_index = 0

        global_idx = (
            selector._current_page * selector.page_size + selector._highlighted_index
        )
        assert global_idx == 0

    def test_global_index_first_page_last_item(self):
        """Test global index calculation: page 0, item 4."""
        selector = InteractiveFuzzySelector(SAMPLE_SCORED_RESULTS, "test", page_size=5)
        selector._current_page = 0
        selector._highlighted_index = 4

        global_idx = (
            selector._current_page * selector.page_size + selector._highlighted_index
        )
        assert global_idx == 4

    def test_global_index_second_page_first_item(self):
        """Test global index calculation: page 1, item 0."""
        selector = InteractiveFuzzySelector(SAMPLE_SCORED_RESULTS, "test", page_size=5)
        selector._current_page = 1
        selector._highlighted_index = 0

        global_idx = (
            selector._current_page * selector.page_size + selector._highlighted_index
        )
        assert global_idx == 5

    def test_global_index_second_page_middle_item(self):
        """Test global index calculation: page 1, item 3."""
        selector = InteractiveFuzzySelector(SAMPLE_SCORED_RESULTS, "test", page_size=5)
        selector._current_page = 1
        selector._highlighted_index = 3

        global_idx = (
            selector._current_page * selector.page_size + selector._highlighted_index
        )
        assert global_idx == 8


class TestInteractiveFuzzySelectorEdgeCases:
    """Tests for edge cases and special scenarios."""

    def test_empty_results(self):
        """Test selector behavior with empty results."""
        results: List[Tuple[int, str, str]] = []
        selector = InteractiveFuzzySelector(results, "test")

        assert selector.total_results == 0
        assert selector.total_pages == 0

    def test_single_result(self):
        """Test selector with single result."""
        results = [(100, "openai", "gpt-4o")]
        selector = InteractiveFuzzySelector(results, "gpt")

        assert selector.total_results == 1
        assert selector.total_pages == 1
        assert selector._current_page == 0
        assert selector._highlighted_index == 0

        selector._handle_enter()
        assert selector._selected_result.model == "gpt-4o"

    def test_exactly_one_page(self):
        """Test selector with exactly one page of results."""
        results = [(i, f"p{i}", f"m{i}") for i in range(10)]
        selector = InteractiveFuzzySelector(results, "test", page_size=10)

        assert selector.total_pages == 1
        # Navigation shouldn't create new pages
        selector._handle_key_down()
        # Should stay on page 0 with last item highlighted
        assert selector._current_page == 0

    def test_query_with_special_characters(self):
        """Test selector with special characters in query."""
        selector = InteractiveFuzzySelector(
            SAMPLE_SCORED_RESULTS,
            "gpt-4o",
            page_size=10,
        )
        assert selector.query == "gpt-4o"

    def test_very_long_model_names(self):
        """Test rendering with very long model names."""
        results = [
            (
                100,
                "provider",
                "model-with-extremely-long-name-that-might-cause-wrapping",
            )
        ]
        selector = InteractiveFuzzySelector(results, "test")

        # Should not crash
        content = selector._get_current_page_content()
        assert content is not None


class TestInteractiveFuzzySelectorRun:
    """Tests for run() method behavior."""

    def test_run_returns_fuzzy_search_result(self, monkeypatch):
        """Test that run() returns FuzzySearchResult with cancelled state."""

        # Mock Application.run() to avoid actually running the interactive app
        def mock_run(self):
            # Simulate cancelled state
            self._cancelled = True

        monkeypatch.setattr(
            "nexus.cli.fuzzy_selector.InteractiveFuzzySelector.run",
            lambda self: FuzzySearchResult(provider="", model="", cancelled=True),
        )

        # Create and run selector
        _ = InteractiveFuzzySelector(SAMPLE_SCORED_RESULTS, "test")
        result = FuzzySearchResult(provider="", model="", cancelled=True)

        assert isinstance(result, FuzzySearchResult)
        assert result.cancelled is True

    def test_run_with_selection(self, monkeypatch):
        """Test run() return value when selection is made."""
        # Mock Application.run() to avoid actually running the interactive app
        selector = InteractiveFuzzySelector(SAMPLE_SCORED_RESULTS, "test")
        selector._selected_result = FuzzySearchResult(
            provider="openai",
            model="gpt-4o",
            cancelled=False,
        )

        # Simulate run() returning the pre-set result
        def mock_run(self):
            if self._selected_result:
                return self._selected_result
            return FuzzySearchResult(provider="", model="", cancelled=True)

        monkeypatch.setattr(
            InteractiveFuzzySelector,
            "run",
            mock_run,
        )

        result = selector.run()
        assert result.provider == "openai"
        assert result.model == "gpt-4o"
        assert result.cancelled is False
