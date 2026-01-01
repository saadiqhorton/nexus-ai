"""Interactive fuzzy search selector with arrow key navigation.

This module provides an interactive interface for selecting models from fuzzy search
results using arrow keys, built on prompt_toolkit for keyboard handling.
"""

from typing import List, NamedTuple, Optional, Tuple

from prompt_toolkit import Application
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.containers import Window
from prompt_toolkit.layout.controls import FormattedTextControl


class FuzzySearchResult(NamedTuple):
    """Result of interactive fuzzy search selection.

    Attributes:
        provider: The selected provider name (e.g., 'openai', 'anthropic')
        model: The selected model ID (e.g., 'gpt-4o', 'claude-sonnet-4')
        cancelled: True if user cancelled (Esc/Ctrl+C), False if selection made
    """

    provider: str
    model: str
    cancelled: bool = False


class InteractiveFuzzySelector:
    """Interactive model selector with arrow key navigation.

    Provides a terminal UI for selecting from fuzzy search results using:
    - ↑↓ arrows for navigation
    - Enter to select
    - Esc/Ctrl+C to cancel
    - Automatic page wrapping
    """

    def __init__(
        self,
        scored_results: List[Tuple[int, str, str]],
        query: str,
        page_size: int = 10,
    ):
        """Initialize the interactive selector.

        Args:
            scored_results: List of (score, provider, model_id) tuples from fuzzy search
            query: The original search query string for display
            page_size: Maximum number of items per page (default: 10)
        """
        self.scored_results = scored_results
        self.query = query
        self.page_size = page_size

        # Calculate pagination
        self.total_results = len(scored_results)
        self.total_pages = (self.total_results + page_size - 1) // page_size

        # State tracking
        self._current_page = 0
        self._highlighted_index = 0  # Index within current page (0-based)
        self._selected_result: Optional[FuzzySearchResult] = None
        self._cancelled = False

    def run(self) -> FuzzySearchResult:
        """Run the interactive selector and return the user's choice.

        Returns:
            FuzzySearchResult with selected provider/model or cancelled=True
        """
        # Create and run the prompt_toolkit application
        app = self._create_application()

        try:
            app.run()
        except KeyboardInterrupt:
            # Ctrl+C pressed - treat as cancellation
            self._cancelled = True

        # Return result
        if self._cancelled or self._selected_result is None:
            return FuzzySearchResult(provider="", model="", cancelled=True)

        return self._selected_result

    def _create_application(self) -> Application:
        """Create the prompt_toolkit Application with key bindings.

        Returns:
            Configured Application instance ready to run
        """
        # Create key bindings
        kb = KeyBindings()

        @kb.add("up")
        def _handle_up(event):
            self._handle_key_up()

        @kb.add("down")
        def _handle_down(event):
            self._handle_key_down()

        @kb.add("enter")
        def _handle_enter_key(event):
            self._handle_enter()
            event.app.exit()

        @kb.add("escape")
        def _handle_escape_key(event):
            self._handle_escape()
            event.app.exit()

        @kb.add("c-c")
        def _handle_ctrl_c(event):
            self._handle_escape()
            event.app.exit()

        # Create layout with formatted text control
        content_control = FormattedTextControl(
            text=self._get_current_page_content,
            focusable=True,
        )

        layout = Layout(Window(content=content_control))

        # Create and return application
        return Application(
            layout=layout,
            key_bindings=kb,
            full_screen=False,
            mouse_support=False,
        )

    def _get_current_page_content(self) -> HTML:
        """Generate HTML-formatted content for current page display.

        Returns:
            HTML object with formatted page content including:
            - Header with query
            - Numbered list with highlighted selection
            - Page info and navigation hints
        """
        # Calculate page boundaries
        start_idx = self._current_page * self.page_size
        end_idx = min(start_idx + self.page_size, self.total_results)
        page_results = self.scored_results[start_idx:end_idx]

        # Build output lines
        lines = []

        # Header
        lines.append(f"<b>Fuzzy matches for '{self.query}':</b>\n")

        # Results with highlighting
        for local_idx, (score, provider, model_id) in enumerate(page_results):
            display_num = local_idx + 1
            model_text = f"{provider}/{model_id}"

            # Highlight the currently selected item
            if local_idx == self._highlighted_index:
                lines.append(f"<reverse>  → [{display_num}] {model_text}</reverse>")
            else:
                lines.append(f"    [{display_num}] {model_text}")

        lines.append("")  # Blank line before footer

        # Page info
        result_start = start_idx + 1
        result_end = end_idx
        page_info = (
            f"Page {self._current_page + 1} of {self.total_pages} - "
            f"Showing {result_start}-{result_end} of {self.total_results} results"
        )
        lines.append(page_info)

        # Navigation hints
        hints = "↑↓: Navigate | Enter: Select | Esc: Cancel"
        lines.append(f"<dim>{hints}</dim>")

        return HTML("\n".join(lines))

    def _handle_key_up(self) -> None:
        """Handle up arrow key press - move highlight up with page wrapping."""
        if self._highlighted_index > 0:
            # Move up within current page
            self._highlighted_index -= 1
        else:
            # At top of page - wrap to previous page
            self._current_page = (self._current_page - 1) % self.total_pages

            # Set highlight to last item of new page
            start_idx = self._current_page * self.page_size
            end_idx = min(start_idx + self.page_size, self.total_results)
            items_on_page = end_idx - start_idx
            self._highlighted_index = items_on_page - 1

    def _handle_key_down(self) -> None:
        """Handle down arrow key press - move highlight down with page wrapping."""
        # Calculate items on current page
        start_idx = self._current_page * self.page_size
        end_idx = min(start_idx + self.page_size, self.total_results)
        items_on_page = end_idx - start_idx

        if self._highlighted_index < items_on_page - 1:
            # Move down within current page
            self._highlighted_index += 1
        else:
            # At bottom of page - wrap to next page
            self._current_page = (self._current_page + 1) % self.total_pages
            self._highlighted_index = 0

    def _handle_enter(self) -> None:
        """Handle Enter key - confirm selection of highlighted item."""
        # Calculate global index from current page and local highlight
        global_idx = self._current_page * self.page_size + self._highlighted_index

        # Validate index is within bounds
        if 0 <= global_idx < self.total_results:
            _, provider, model = self.scored_results[global_idx]
            self._selected_result = FuzzySearchResult(
                provider=provider,
                model=model,
                cancelled=False,
            )
        else:
            # Should never happen, but handle gracefully
            self._cancelled = True

    def _handle_escape(self) -> None:
        """Handle Escape key - cancel selection."""
        self._cancelled = True
