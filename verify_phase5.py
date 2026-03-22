import sys

# === Cluster 5.2: World Generator Fixes ===

# Test 1: Time parsing flexibility
from utils.world_generator import parse_time_string
tests = [
    ('about 3 hours', 'advance', 3),
    ('4 to 5 hours', 'advance', 4),
    ('a few hours pass', 'advance', 3),
    ('several hours later', 'advance', 5),
    ('couple hours of travel', 'advance', 2),
    ('30 minutes', 'advance', 1),
    ('long rest', 'advance', 8),
    ('dawn', 'set_period', None),
]
for text, expected_action, expected_hours in tests:
    r = parse_time_string(text)
    ok = r['action'] == expected_action
    if expected_hours is not None:
        ok = ok and r.get('hours') == expected_hours
    status = '✓' if ok else 'FAIL'
    print(f'  {status}: "{text}" → {r["action"]}' + (f', {r.get("hours")}h' if 'hours' in r else f', {r.get("period", "")}'))
    if not ok:
        print(f'    Expected: action={expected_action}, hours={expected_hours}')
        sys.exit(1)
print('Time parsing flexibility ✓')

# Test 2: Indoor lighting protection (code check)
import inspect
from utils.world_generator import update_lighting_for_time
source = inspect.getsource(update_lighting_for_time)
assert 'LOCATION_PRESETS' in source or 'is_outdoor' in source, 'FAIL: update_lighting_for_time still uses source whitelist'
assert 'outdoor_sources' not in source, 'FAIL: old outdoor_sources whitelist still present'
print('Indoor lighting uses preset-based detection ✓')

# Test 3: apply_location_preset has override param
from utils.world_generator import apply_location_preset
sig = inspect.signature(apply_location_preset)
assert 'override' in sig.parameters, 'FAIL: override param missing'
print(f'apply_location_preset has override param ✓')

# Test 4: TimeState rollover uses while
from utils.world_generator import TimeState
ts = TimeState(hour=23, day=30, month=12, year=1490)
ts.advance(48)  # 2 full days
assert ts.hour == 23, f'FAIL: hour should be 23, got {ts.hour}'
assert ts.day == 2, f'FAIL: day should be 2, got {ts.day}'
assert ts.month == 1, f'FAIL: month should be 1, got {ts.month}'
assert ts.year == 1491, f'FAIL: year should be 1491, got {ts.year}'
print(f'TimeState rollover: {ts.year}-{ts.month:02d}-{ts.day:02d} {ts.hour}:00 ✓')

# === Cluster 5.3: Travel & World Map Fixes ===

# Test 5: Travel detection with known locations
from utils.world_map import detect_natural_language_travel
intent = detect_natural_language_travel('we travel to Phandalin', known_locations=['Phandalin', 'Neverwinter'])
assert intent is not None, 'FAIL: should detect known location'
assert intent.destination == 'Phandalin', f'FAIL: destination should be Phandalin, got {intent.destination}'
assert intent.confidence == 0.9, f'FAIL: known location should have 0.9 confidence'
print(f'Known location detection: {intent.destination} (conf={intent.confidence}) ✓')

# Should NOT match vague words
intent2 = detect_natural_language_travel('we travel towards madness')
assert intent2 is None, f'FAIL: should not match "madness", got {intent2}'
print(f'Rejects vague destination "madness" ✓')

# Test 6: Location key normalization
from utils.world_map import add_location, get_location
import os, json
TEST_CHANNEL = 'verify_world_test'
# Add with mixed case
loc = add_location(TEST_CHANNEL, 'Phandalin', terrain='plains', status='visited')
# Retrieve with different case
found = get_location(TEST_CHANNEL, 'phandalin')
assert found is not None, 'FAIL: lowercase lookup failed'
assert found.name == 'Phandalin', f'FAIL: display name lost, got {found.name}'
print(f'Location normalization: stored as lowercase, display name preserved ✓')

# Cleanup
from utils.world_map import get_world_path
path = get_world_path(TEST_CHANNEL)
if os.path.exists(path):
    os.remove(path)

# Test 7: ENCOUNTER_MULTIPLIERS removed
import utils.encounter_manager as em
assert not hasattr(em, 'ENCOUNTER_MULTIPLIERS'), 'FAIL: ENCOUNTER_MULTIPLIERS still exists'
print(f'ENCOUNTER_MULTIPLIERS removed ✓')

# Test 8: Night detection uses world_generator (code check)
source3 = inspect.getsource(em.advance_travel)
assert 'get_time_state' in source3, 'FAIL: advance_travel does not use get_time_state'
assert 'hours_traveled_today > 12' not in source3, 'FAIL: old simplified night check still present'
print(f'Night detection uses game time ✓')

print('\nAll Phase 5 world/travel fixes verified!')
