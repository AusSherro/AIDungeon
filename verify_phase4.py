import sys, os

# Test 1: HP floor on CON decrease
from utils.character_manager import register_character, load_character, set_stat, death_save, short_rest, CHAR_DIR

TEST_USER = 'verify_phase4_test'

# Cleanup first
path = os.path.join(CHAR_DIR, f'{TEST_USER}.json')
if os.path.exists(path):
    os.remove(path)

# Register character
register_character(TEST_USER, 'Test', 'Fighter', 'Human')
data = load_character(TEST_USER)
print(f'Initial max_hp: {data["max_hp"]}')

# Set CON to 1 (modifier = -5). For level 1: max_hp = hit_die + modifier change
# The important thing is max_hp must be >= 1
set_stat(TEST_USER, 'CON', 1)
data = load_character(TEST_USER)
assert data['max_hp'] >= 1, f'FAIL: max_hp = {data["max_hp"]}, should be >= 1'
print(f'After CON=1: max_hp={data["max_hp"]} (>= 1) ✓')

# Cleanup and recreate for death save test
os.remove(path)
register_character(TEST_USER, 'Test', 'Fighter', 'Human')

# Test 2: Death save clears conditions
from utils.character_manager import damage_character, add_condition
damage_character(TEST_USER, 9999)  # Drop to 0
add_condition(TEST_USER, 'unconscious')
add_condition(TEST_USER, 'dying')

# 3 successful death saves
for i in range(3):
    death_save(TEST_USER, True)
data = load_character(TEST_USER)
assert data['hp'] == 1, f'FAIL: hp should be 1 after stabilize, got {data["hp"]}'
conditions_lower = [c.lower() for c in data.get('conditions', [])]
assert 'unconscious' not in conditions_lower, f'FAIL: unconscious not cleared'
assert 'dying' not in conditions_lower, f'FAIL: dying not cleared'
assert 'dead' not in conditions_lower, f'FAIL: dead not cleared'
print(f'Death save stabilize: hp=1, conditions cleared ✓')

# Test 3: dnd5e_data import is direct (no DND_DATA_AVAILABLE)
import utils.character_manager as cm
assert not hasattr(cm, 'DND_DATA_AVAILABLE'), 'FAIL: DND_DATA_AVAILABLE still exists!'
print(f'DND_DATA_AVAILABLE removed ✓')

# Test 4: Warlock short rest (check pact_slots_used exists in flow)
os.remove(path)
register_character(TEST_USER, 'Test Warlock', 'Warlock', 'Human')
data = load_character(TEST_USER)
from utils.character_manager import save_character
data['pact_slots_used'] = 2
save_character(TEST_USER, data)
result = short_rest(TEST_USER)
data = load_character(TEST_USER)
assert data.get('pact_slots_used', 0) == 0, f'FAIL: pact_slots_used should be 0'
print(f'Warlock pact slots recover on short rest ✓')

# Cleanup
os.remove(path)
print('\nAll Phase 4 character fixes verified!')
