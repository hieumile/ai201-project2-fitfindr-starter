# FitFindr — Starter Kit

This starter kit contains everything you need to begin Project 2.

## What's Included

```
ai201-project2-fitfindr-starter/
├── data/
│   ├── listings.json          # 40 mock secondhand listings
│   └── wardrobe_schema.json   # Wardrobe format + example wardrobe
├── utils/
│   └── data_loader.py         # Helper functions for loading the data
├── planning.md                # Your planning template — fill this out first
└── requirements.txt           # Python dependencies
```

## Setup

```bash
pip install -r requirements.txt
```

Set your Groq API key in a `.env` file (get a free key at [console.groq.com](https://console.groq.com)):
```
GROQ_API_KEY=your_key_here
```

## The Mock Listings Dataset

`data/listings.json` contains 40 mock secondhand listings across categories (tops, bottoms, outerwear, shoes, accessories) and styles (vintage, y2k, grunge, cottagecore, streetwear, and more).

Each listing has: `id`, `title`, `description`, `category`, `style_tags`, `size`, `condition`, `price`, `colors`, `brand`, and `platform`.

Load it with:
```python
from utils.data_loader import load_listings
listings = load_listings()
```

## The Wardrobe Schema

`data/wardrobe_schema.json` defines the format your agent uses to represent a user's existing wardrobe. It includes:

- `schema`: field definitions for a wardrobe item
- `example_wardrobe`: a sample wardrobe with 10 items you can use for testing
- `empty_wardrobe`: a starting template for a new user

Load an example wardrobe with:
```python
from utils.data_loader import get_example_wardrobe
wardrobe = get_example_wardrobe()
```

## AI Usage

This project used Claude (Anthropic, via Cowork) as the primary AI tool throughout implementation.

### Instance 1 — Implementing `search_listings`

**Input given to Claude:** The Tool 1 spec from `planning.md` (inputs, return value, failure mode), the `search_listings` stub from `tools.py`, and the `load_listings()` signature from `utils/data_loader.py`.

**What it produced:** A complete implementation that loaded listings, filtered by price and size using list comprehensions, scored each listing by keyword overlap across title/description/style_tags/colors, dropped zero-score results, and returned a sorted list of matching dicts.

**What I changed:** The generated code returned a `list[dict]` of all matches. I overrode this to return a single `dict | None` — just the top result — since the agent only ever uses the best match and passing a list created unnecessary indexing (`results[0]`) downstream. I also removed `id`, `brand`, and `platform` from the returned dict to match only the 8 fields specified in `planning.md`.

---

### Instance 2 — Implementing `run_agent` (planning loop)

**Input given to Claude:** The full Planning Loop and State Management sections from `planning.md`, the Architecture Mermaid diagram, the `_new_session()` dict definition, and the numbered TODO steps inside `run_agent()` in `agent.py`.

**What it produced:** A planning loop that initialized the session, parsed the query with regex, called `search_listings`, branched on the result, and conditionally called `suggest_outfit` and `create_fit_card` — storing each output in the session dict before proceeding.

**What I changed:** The generated price regex (`r"(?:under|max|below|up to)?\s*\$?(\d+(?:\.\d+)?)"`) matched bare numbers without a `$` or keyword, so `"90s track jacket"` was parsed as `max_price=90.0` and `"size 8"` produced `max_price=8.0`. I rewrote the regex to require either an explicit `$` sign or a keyword prefix (`under`, `max`, `below`, `up to`) before treating a number as a price. I also added a fix for the size regex, which was matching the `m` in `"I'm"` as size M by using lookahead/lookbehind to exclude apostrophe-adjacent matches.

---

## Where to Start

1. **Read `planning.md` and fill it out before writing any code.**
2. Verify the data loads correctly by running `python utils/data_loader.py`.
3. Build and test each tool individually before connecting them through your planning loop.

Your implementation files go in this same directory. There's no required file structure for your agent code — organize it however makes sense for your design.
