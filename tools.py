"""
tools.py

The three required FitFindr tools. Each tool is a standalone function that
can be called and tested independently before being wired into the agent loop.

Complete and test each tool before moving to agent.py.

Tools:
    search_listings(description, size, max_price)  → list[dict]
    suggest_outfit(new_item, wardrobe)              → str
    create_fit_card(outfit, new_item)               → str
"""

import os

from dotenv import load_dotenv
from groq import Groq

from utils.data_loader import load_listings

load_dotenv()


# ── Groq client ───────────────────────────────────────────────────────────────

def _get_groq_client():
    """Initialize and return a Groq client using GROQ_API_KEY from .env."""
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not set. Add it to a .env file in the project root."
        )
    return Groq(api_key=api_key)


# ── Tool 1: search_listings ───────────────────────────────────────────────────

def search_listings(
    description: str,
    size: str | None = None,
    max_price: float | None = None,
) -> dict | None:
    """
    Search the mock listings dataset for the best item matching the description,
    optional size, and optional price ceiling.

    Args:
        description: Keywords describing what the user is looking for
                     (e.g., "vintage graphic tee").
        size:        Size string to filter by, or None to skip size filtering.
                     Matching is case-insensitive (e.g., "M" matches "S/M").
        max_price:   Maximum price (inclusive), or None to skip price filtering.

    Returns:
        A dict for the top matching item with fields:
            title, description, category, style_tags (list), size,
            condition, price (float), colors (list)
        Returns None if nothing matches — does NOT raise an exception.
    """
    listings = load_listings()

    # Filter by price and size
    if max_price is not None:
        listings = [l for l in listings if l["price"] <= max_price]
    if size is not None:
        size_lower = size.lower()
        listings = [l for l in listings if size_lower in l["size"].lower()]

    # Build keyword set from description
    keywords = set(description.lower().split())

    # Score each listing by keyword overlap across searchable fields
    def score(listing: dict) -> int:
        searchable = " ".join([
            listing["title"],
            listing["description"],
            listing["category"],
            " ".join(listing["style_tags"]),
            " ".join(listing["colors"]),
            listing["brand"] or "",
        ]).lower()
        return sum(1 for kw in keywords if kw in searchable)

    scored = [(score(l), l) for l in listings]
    scored = [(s, l) for s, l in scored if s > 0]
    if not scored:
        return None

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[0][1]

    return {
        "title":       top["title"],
        "description": top["description"],
        "category":    top["category"],
        "style_tags":  top["style_tags"],
        "size":        top["size"],
        "condition":   top["condition"],
        "price":       top["price"],
        "colors":      top["colors"],
    }


# ── Tool 2: suggest_outfit ────────────────────────────────────────────────────

def suggest_outfit(new_item: dict, wardrobe: dict) -> str:
    """
    Given a thrifted item and the user's wardrobe, suggest 1–2 complete outfits.

    Args:
        new_item: A listing dict (the item the user is considering buying).
        wardrobe: A wardrobe dict with an 'items' key containing a list of
                  wardrobe item dicts. May be empty — handle this gracefully.

    Returns:
        A non-empty string with outfit suggestions.
        If the wardrobe is empty, offer general styling advice for the item
        rather than raising an exception or returning an empty string.

    TODO:
        1. Check whether wardrobe['items'] is empty.
        2. If empty: call the LLM with a prompt for general styling ideas
           (what kinds of items pair well, what vibe it suits, etc.).
        3. If not empty: format the wardrobe items into a prompt and ask
           the LLM to suggest specific outfit combinations using the new item
           and named pieces from the wardrobe.
        4. Return the LLM's response as a string.

    Before writing code, fill in the Tool 2 section of planning.md.
    """
    client = _get_groq_client()

    item_summary = (
        f"Title: {new_item['title']}\n"
        f"Category: {new_item['category']}\n"
        f"Style tags: {', '.join(new_item['style_tags'])}\n"
        f"Colors: {', '.join(new_item['colors'])}\n"
        f"Size: {new_item['size']}\n"
        f"Condition: {new_item['condition']}\n"
        f"Price: ${new_item['price']}\n"
        f"Description: {new_item['description']}"
    )

    items = wardrobe.get("items", [])

    if not items:
        prompt = (
            f"A user is considering buying this thrifted item:\n\n{item_summary}\n\n"
            "Their wardrobe is currently empty. Give them general styling advice: "
            "what kinds of pieces would pair well with this item, what vibe or aesthetic "
            "it suits, and what to look for next when building an outfit around it. "
            "Keep it practical and specific — 3–5 sentences."
        )
    else:
        wardrobe_lines = "\n".join(
            f"- {item.get('name', 'Unknown')} ({item.get('category', '')}): "
            f"{item.get('colors', [''])[0] if item.get('colors') else ''}, "
            f"style: {', '.join(item.get('style_tags', []))}"
            for item in items
        )
        prompt = (
            f"A user is considering buying this thrifted item:\n\n{item_summary}\n\n"
            f"Their current wardrobe contains:\n{wardrobe_lines}\n\n"
            "Suggest 1–2 complete outfit combinations using the new item and specific "
            "pieces from their wardrobe listed above. Name each wardrobe piece you include. "
            "Keep it concise and practical — 4–6 sentences total."
        )

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
    )
    return response.choices[0].message.content


# ── Tool 3: create_fit_card ───────────────────────────────────────────────────

def create_fit_card(outfit: str, new_item: dict) -> str:
    """
    Generate a short, shareable outfit caption for the thrifted find.

    Args:
        outfit:   The outfit suggestion string from suggest_outfit().
        new_item: The listing dict for the thrifted item.

    Returns:
        A 2–4 sentence string usable as an Instagram/TikTok caption.
        If outfit is empty or missing, return a descriptive error message
        string — do NOT raise an exception.

    The caption should:
    - Feel casual and authentic (like a real OOTD post, not a product description)
    - Mention the item name, price, and platform naturally (once each)
    - Capture the outfit vibe in specific terms
    - Sound different each time for different inputs (use higher LLM temperature)

    TODO:
        1. Guard against an empty or whitespace-only outfit string.
        2. Build a prompt that gives the LLM the item details and the outfit,
           and asks for a caption matching the style guidelines above.
        3. Call the LLM and return the response.

    Before writing code, fill in the Tool 3 section of planning.md.
    """
    if not outfit or not outfit.strip():
        return "Could not generate a fit card: no outfit suggestion was provided."

    client = _get_groq_client()

    prompt = (
        f"You are writing a casual, authentic OOTD (outfit of the day) caption "
        f"for Instagram or TikTok — not a product description.\n\n"
        f"Thrifted item: {new_item['title']} — ${new_item['price']}\n"
        f"Colors: {', '.join(new_item['colors'])}\n"
        f"Vibe: {', '.join(new_item['style_tags'])}\n\n"
        f"Outfit built around it:\n{outfit}\n\n"
        f"Write a 2–4 sentence caption that:\n"
        f"- Sounds like a real person posting, not a brand\n"
        f"- Mentions the item name and price once, naturally\n"
        f"- Captures the specific vibe of this outfit (not generic compliments)\n"
        f"- Varies in tone and phrasing — do not use a template\n\n"
        f"Return only the caption text, nothing else."
    )

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=1.3,
    )
    return response.choices[0].message.content
