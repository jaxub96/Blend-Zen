import math
from modules.zen_gin_export.light_conversion import gothic_range_to_blender_power


def test_power_scales_with_range_squared():
    assert math.isclose(gothic_range_to_blender_power(1400) / gothic_range_to_blender_power(700), 4.0)


def test_power_is_much_lower_than_old_heuristic():
    # old heuristic was range_cm * 2 -> 1400 W for a 700 cm light
    assert gothic_range_to_blender_power(700) < 200


def test_known_value():
    # 7 m range: match at 3.5 m, target display 0.5 -> linear 0.5**2.2
    expected = 16 * math.pi * 3.5 ** 2 * 0.5 ** 2.2
    assert math.isclose(gothic_range_to_blender_power(700), expected)
