# FitFindr

FitFindr is an AI-powered thrift shopping assistant. A user describes a secondhand item they're looking for, and the agent searches a mock listings dataset, suggests outfits using the user's wardrobe, and generates a shareable fit card caption.

## Setup

```bash
pip install -r requirements.txt
```

Create a `.env` file in the project root with your Groq API key (free at [console.groq.com](https://console.groq.com)):

```
GROQ_API_KEY=your_key_here
```

Run the app:

```bash
python app.py
```

Then open the localhost URL shown in your terminal (usually http://localhost:7860).

---

## Tool Inventory

### Tool 1: `search_listings`

**Purpose:** Searches the mock listings dataset for the single best item matching the user's description, optional size, and optional price ceiling. No LLM is involved — this is pure keyword scoring over the local dataset.

**Inputs:**

| Parameter | Type | Description |
|---|---|---|
| `description` | `str` | Keywords describing what the user wants (e.g. `"vintage graphic tee"`) |
| `size` | `str \| None` | Size to filter by, case-insensitive substring match (e.g. `"M"` matches `"S/M"`). `None` skips size filtering. |
| `max_price` | `float \| None` | Maximum price inclusive. `None` skips price filtering. |

**Output:** A `dict` with 8 fields — `title`, `description`, `category`, `style_tags` (list), `size`, `condition`, `price` (float), `colors` (list) — for the highest-scoring match. Returns `None` if nothing matches.

---

### Tool 2: `suggest_outfit`

**Purpose:** Given the thrifted item and the user's wardrobe, calls the LLM to suggest 1–2 complete outfit combinations. If the wardrobe is empty, the LLM gives general styling advice instead.

**Inputs:**

| Parameter | Type | Description |
|---|---|---|
| `new_item` | `dict` | The item dict returned by `search_listings` (8 fields) |
| `wardrobe` | `dict` | A wardrobe dict with an `"items"` key containing a list of wardrobe item dicts. May be empty. |

**Output:** A non-empty `str` containing outfit suggestions or general styling advice. Never raises an exception — empty wardrobe is handled gracefully with a different LLM prompt.

**Model:** `llama-3.3-70b-versatile` via Groq, temperature 0.7.

---

### Tool 3: `create_fit_card`

**Purpose:** Takes the outfit suggestion and the thrifted item and generates a short, casual Instagram/TikTok-style caption. Designed to sound like a real person posting, not a product description. Uses high temperature so output varies across calls.

**Inputs:**

| Parameter | Type | Description |
|---|---|---|
| `outfit` | `str` | The outfit suggestion string returned by `suggest_outfit` |
| `new_item` | `dict` | The item dict returned by `search_listings` (8 fields) |

**Output:** A `str` of 2–4 sentences usable as an OOTD caption. If `outfit` is empty or whitespace-only, returns an error message string without calling the LLM.

**Model:** `llama-3.3-70b-versatile` via Groq, temperature 1.3.

---

## Planning Loop

The agent's planning loop is conditional and state-driven — it does not call all three tools unconditionally in a fixed sequence. Each tool call is gated on what the previous step returned.

1. **Parse.** The user's natural language query is parsed with regex to extract a `description`, `size`, and `max_price`. Price requires either an explicit `$` or a keyword (under/max/below/up to) to avoid matching bare numbers like the `90` in `"90s jacket"`. Extracted tokens are stripped from the query to produce a clean description.

2. **Search — always runs.** `search_listings` is called with the parsed parameters. This is the only tool guaranteed to run on every interaction.

3. **Branch on result.** If `search_listings` returns `None`, the agent sets `session["error"]` and returns immediately. `suggest_outfit` and `create_fit_card` are never called — there is nothing to style.

4. **Suggest outfit — only if a match was found.** `suggest_outfit` is called with the selected item and the user's wardrobe. Even if the wardrobe is empty, it continues rather than stopping.

5. **Create fit card — only if an outfit suggestion exists.** `create_fit_card` is called with the suggestion string and the item. The agent is done when this returns.

The agent knows it's done when either `session["fit_card"]` is populated (success) or `session["error"]` is set (early exit).

---

## State Management

All state lives in a single `session` dict created at the start of each interaction by `_new_session()`. No global variables are used. Each tool is called with values read directly from the session, and its return value is written back into the appropriate field before the next step.

| Field | Set by | Read by |
|---|---|---|
| `session["query"]` | `_new_session()` | parse step |
| `session["parsed"]` | parse step | `search_listings` call |
| `session["search_results"]` | `search_listings` call | branch check |
| `session["selected_item"]` | branch check | `suggest_outfit` call |
| `session["wardrobe"]` | `_new_session()` (passed in by caller) | `suggest_outfit` call |
| `session["outfit_suggestion"]` | `suggest_outfit` call | `create_fit_card` call |
| `session["fit_card"]` | `create_fit_card` call | returned to caller |
| `session["error"]` | any early-exit step | caller checks this first |

No tool receives the session dict itself — inputs are unpacked explicitly, keeping each tool independently testable.

---

## Error Handling

### `search_listings` — no results

If no listings score above zero after filtering, the tool returns `None`. The agent sets `session["error"]` to a user-friendly message and returns the session immediately without calling `suggest_outfit` or `create_fit_card`.

**Concrete example from testing:**

```
query: "designer ballgown size XXS under $5"

session["error"]           → "No listings matched your search. Try different
                              keywords, a larger budget, or a different size."
session["fit_card"]        → None
session["outfit_suggestion"] → None
```

`suggest_outfit` was never called, confirmed by the `None` values in both downstream fields.

---

### `suggest_outfit` — empty wardrobe

If `wardrobe["items"]` is empty (or the key is missing), the tool detects this before building the prompt and switches to a general styling advice prompt instead of one that references wardrobe pieces. The agent continues normally — no error is set.

**Concrete example from testing:**

```python
result = search_listings("vintage graphic tee", max_price=30.0)
print(suggest_outfit(result, get_empty_wardrobe()))
```

Output: general advice about what styles pair well with a Y2K baby tee — no crash, no empty string, no reference to wardrobe items that don't exist.

---

### `create_fit_card` — empty outfit string

If `outfit` is an empty string or whitespace-only, the function returns a descriptive error string immediately without calling the LLM.

**Concrete example from testing:**

```python
print(create_fit_card("", result))
# → "Could not generate a fit card: no outfit suggestion was provided."

print(create_fit_card("   ", result))
# → "Could not generate a fit card: no outfit suggestion was provided."
```

The LLM is never called in either case, confirmed by patching `_get_groq_client` in the test suite and asserting it was not invoked.

---

## Spec Reflection

**What matched the spec:** The conditional planning loop matches the design in `planning.md` exactly — `suggest_outfit` and `create_fit_card` are skipped when there are no search results, and the empty wardrobe case is handled with a different LLM prompt rather than a crash or an empty response. State flows through the session dict with no re-entry or hardcoded values between steps, as described in the State Management section.

**What changed from the original spec:** The planning.md spec described `search_listings` returning a list of matching items. During implementation, this was changed to return a single `dict | None` (the top result only), since the agent only ever uses the best match and returning a list created unnecessary indexing downstream. This simplification also meant the "select top result" step in the loop became a no-op — the tool itself handles ranking and selection.

The size regex required revision after testing revealed it was matching the `m` in `"I'm"` as size M, and the price regex was matching bare numbers like `90` from `"90s jacket"`. Both were tightened: size now uses lookahead/lookbehind to exclude apostrophe-adjacent matches, and price now requires either an explicit `$` or a keyword prefix. These edge cases were not anticipated in the planning.md spec.

---

## AI Usage

This project used Claude (Anthropic, via Cowork) as the primary AI tool throughout implementation.

### Instance 1 — Implementing `search_listings`

**Input given to Claude:** The Tool 1 spec from `planning.md` (inputs, return value, failure mode), the `search_listings` stub from `tools.py`, and the `load_listings()` signature from `utils/data_loader.py`.

**What it produced:** A complete implementation that loaded listings, filtered by price and size, scored each listing by keyword overlap across title/description/style_tags/colors, dropped zero-score results, and returned a sorted list of matching dicts.

**What I changed:** The generated code returned a `list[dict]` of all matches. I overrode this to return a single `dict | None` — just the top result — since the agent only ever uses the best match and passing a list created unnecessary indexing (`results[0]`) downstream. I also removed `id`, `brand`, and `platform` from the returned dict to match only the 8 fields specified in `planning.md`.

### Instance 2 — Implementing `run_agent` (planning loop)

**Input given to Claude:** The full Planning Loop and State Management sections from `planning.md`, the Architecture Mermaid diagram, the `_new_session()` dict definition, and the numbered TODO steps inside `run_agent()` in `agent.py`.

**What it produced:** A planning loop that initialized the session, parsed the query with regex, called `search_listings`, branched on the result, and conditionally called `suggest_outfit` and `create_fit_card`, storing each output in the session dict before proceeding.

**What I changed:** The generated price regex matched bare numbers without a `$` or keyword, so `"90s track jacket"` was parsed as `max_price=90.0` and `"size 8"` produced `max_price=8.0`. I rewrote the regex to require either an explicit `$` sign or a keyword prefix. I also fixed the size regex, which was matching the `m` in `"I'm"` as size M, by adding lookahead/lookbehind to exclude apostrophe-adjacent characters.
