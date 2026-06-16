"""
Quick test for create_fit_card.
Run from the project root: python test_create_fit_card.py
"""
from tools import search_listings, suggest_outfit, create_fit_card
from utils.data_loader import get_example_wardrobe

item = search_listings("vintage graphic tee", max_price=30.0)
wardrobe = get_example_wardrobe()
outfit = suggest_outfit(item, wardrobe)

print("=== item ===")
print(item)
print("\n=== outfit suggestion (shared input for all runs) ===")
print(outfit)
print()

for i in range(1, 4):
    card = create_fit_card(outfit, item)
    print(f"--- Run {i} ---")
    print(card)
    print()

print("--- Empty outfit guard (should not crash) ---")
print(create_fit_card("", item))
print(create_fit_card("   ", item))
