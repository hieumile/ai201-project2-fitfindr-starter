"""
tests/test_tools.py

Run from the project root:  pytest tests/

Groq is mocked for suggest_outfit and create_fit_card so the tests run
without a real API key or network access.
"""

from unittest.mock import MagicMock, patch

import pytest

from tools import create_fit_card, search_listings, suggest_outfit
from utils.data_loader import get_empty_wardrobe, get_example_wardrobe


# ── Helpers ────────────────────────────────────────────────────────────────────

def _mock_groq(response_text: str):
    """Return a mock Groq client whose .chat.completions.create() returns response_text."""
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = MagicMock(
        choices=[MagicMock(message=MagicMock(content=response_text))]
    )
    return mock_client


VALID_ITEM = search_listings("vintage graphic tee", max_price=50)  # real lookup, no LLM


# ── search_listings ────────────────────────────────────────────────────────────

class TestSearchListings:
    def test_returns_dict_on_match(self):
        """Happy path: a matching query returns a dict, not None."""
        result = search_listings("vintage graphic tee", max_price=50)
        assert isinstance(result, dict)

    def test_returned_dict_has_required_fields(self):
        """Result contains exactly the 8 required fields."""
        result = search_listings("vintage graphic tee", max_price=50)
        assert result is not None
        for field in ("title", "description", "category", "style_tags",
                      "size", "condition", "price", "colors"):
            assert field in result, f"missing field: {field}"

    def test_no_match_returns_none(self):
        """Failure mode: impossible query returns None, no exception."""
        result = search_listings("designer ballgown", size="XXS", max_price=5)
        assert result is None

    def test_price_filter_respected(self):
        """Top result price must be within the requested ceiling."""
        result = search_listings("jacket", max_price=30)
        if result is not None:
            assert result["price"] <= 30

    def test_size_filter_respected(self):
        """Top result size must contain the requested size string (case-insensitive)."""
        result = search_listings("top", size="M")
        if result is not None:
            assert "m" in result["size"].lower()

    def test_no_keywords_match_returns_none(self):
        """Query with zero keyword overlap in the dataset returns None."""
        result = search_listings("xyzzy quux frobnicator")
        assert result is None


# ── suggest_outfit ─────────────────────────────────────────────────────────────

class TestSuggestOutfit:
    def test_returns_nonempty_string_with_wardrobe(self):
        """Happy path: non-empty wardrobe produces a non-empty suggestion string."""
        with patch("tools._get_groq_client", return_value=_mock_groq("Pair it with your baggy jeans.")):
            result = suggest_outfit(VALID_ITEM, get_example_wardrobe())
        assert isinstance(result, str)
        assert result.strip() != ""

    def test_empty_wardrobe_does_not_crash(self):
        """Failure mode: empty wardrobe returns general styling advice, no exception."""
        with patch("tools._get_groq_client", return_value=_mock_groq("Try pairing with wide-leg trousers.")):
            result = suggest_outfit(VALID_ITEM, get_empty_wardrobe())
        assert isinstance(result, str)
        assert result.strip() != ""

    def test_empty_wardrobe_uses_different_prompt(self):
        """Empty wardrobe path calls the LLM with a prompt about general styling."""
        mock_client = _mock_groq("General styling advice here.")
        with patch("tools._get_groq_client", return_value=mock_client):
            suggest_outfit(VALID_ITEM, get_empty_wardrobe())
        call_args = mock_client.chat.completions.create.call_args
        prompt = call_args.kwargs["messages"][0]["content"]
        # Empty-wardrobe prompt should mention general/styling guidance
        assert any(word in prompt.lower() for word in ("empty", "general", "styling"))

    def test_nonempty_wardrobe_references_wardrobe_items(self):
        """Non-empty wardrobe path includes wardrobe item names in the prompt."""
        mock_client = _mock_groq("Outfit suggestion with wardrobe pieces.")
        wardrobe = get_example_wardrobe()
        first_item_name = wardrobe["items"][0]["name"]
        with patch("tools._get_groq_client", return_value=mock_client):
            suggest_outfit(VALID_ITEM, wardrobe)
        call_args = mock_client.chat.completions.create.call_args
        prompt = call_args.kwargs["messages"][0]["content"]
        assert first_item_name in prompt


# ── create_fit_card ────────────────────────────────────────────────────────────

class TestCreateFitCard:
    OUTFIT = "Y2K baby tee with baggy jeans and chunky sneakers."

    def test_returns_caption_string(self):
        """Happy path: valid inputs produce a non-empty caption string."""
        with patch("tools._get_groq_client", return_value=_mock_groq("Thrifted this $18 gem and loving it.")):
            result = create_fit_card(self.OUTFIT, VALID_ITEM)
        assert isinstance(result, str)
        assert result.strip() != ""

    def test_empty_outfit_returns_error_string(self):
        """Failure mode: empty outfit string returns error message, no exception."""
        result = create_fit_card("", VALID_ITEM)
        assert isinstance(result, str)
        assert result.strip() != ""

    def test_whitespace_outfit_returns_error_string(self):
        """Failure mode: whitespace-only outfit string is treated as empty."""
        result = create_fit_card("   ", VALID_ITEM)
        assert isinstance(result, str)
        assert result.strip() != ""

    def test_empty_outfit_does_not_call_llm(self):
        """Empty outfit guard fires before any LLM call."""
        with patch("tools._get_groq_client") as mock_factory:
            create_fit_card("", VALID_ITEM)
        mock_factory.assert_not_called()

    def test_prompt_includes_item_title_and_price(self):
        """LLM prompt contains the item title and price."""
        mock_client = _mock_groq("Great caption here.")
        with patch("tools._get_groq_client", return_value=mock_client):
            create_fit_card(self.OUTFIT, VALID_ITEM)
        call_args = mock_client.chat.completions.create.call_args
        prompt = call_args.kwargs["messages"][0]["content"]
        assert VALID_ITEM["title"] in prompt
        assert str(VALID_ITEM["price"]) in prompt
