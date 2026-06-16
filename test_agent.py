"""
Checkpoint verification for agent.py.
Run from the project root: python test_agent.py
"""
from agent import run_agent
from utils.data_loader import get_example_wardrobe

# ── Happy path ─────────────────────────────────────────────────────────────────
print("=== Happy path: vintage graphic tee under $30 ===\n")
session = run_agent(
    query="I'm looking for a vintage graphic tee under $30",
    wardrobe=get_example_wardrobe(),
)

print("Parsed params:")
print(f"  description : {session['parsed']['description']}")
print(f"  size        : {session['parsed']['size']}")
print(f"  max_price   : {session['parsed']['max_price']}")

print("\nsession['selected_item']:")
item = session["selected_item"]
for k, v in item.items():
    print(f"  {k}: {v}")

print("\nsession['outfit_suggestion'] (first 200 chars):")
print(session["outfit_suggestion"][:200])

print("\nsession['fit_card']:")
print(session["fit_card"])

print(f"\nsession['error']: {session['error']}")

# State-passing check: selected_item fed into suggest_outfit
assert session["selected_item"] is not None, "selected_item should not be None"
assert session["outfit_suggestion"] and session["outfit_suggestion"].strip(), \
    "outfit_suggestion should be non-empty"
assert session["fit_card"] and session["fit_card"].strip(), \
    "fit_card should be non-empty"
assert session["error"] is None, "error should be None on success"
print("\n✓ Happy path: state flows correctly through all three tools")

# ── No-results path ────────────────────────────────────────────────────────────
print("\n\n=== No-results path: designer ballgown size XXS under $5 ===\n")
session2 = run_agent(
    query="designer ballgown size XXS under $5",
    wardrobe=get_example_wardrobe(),
)

print(f"session['error']    : {session2['error']}")
print(f"session['fit_card'] : {session2['fit_card']}")
print(f"session['outfit_suggestion']: {session2['outfit_suggestion']}")

assert session2["error"] is not None, "error should be set on no-results path"
assert session2["fit_card"] is None, "fit_card should be None on no-results path"
assert session2["outfit_suggestion"] is None, \
    "outfit_suggestion should be None — suggest_outfit must not have been called"
print("\n✓ No-results path: agent stops after search_listings, suggest_outfit never called")
