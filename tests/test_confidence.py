from src.confidence import assess
from src.upgrade_rules import check_eligibility, load_chart


def _elig(route, fc):
    return check_eligibility(load_chart(), route, fc)


def test_non_upgradeable_returns_do_not_buy():
    e = _elig("TPE-ORD", "P")
    c = assess(e)
    assert c.level == "Do Not Buy"
    assert "NON-UPGRADEABLE" in c.reasoning


def test_basic_economy_classes_do_not_buy():
    for fc in ("A", "V", "W", "S"):
        c = assess(_elig("LAX-TPE", fc))
        assert c.level == "Do Not Buy"


def test_official_confirmed_is_high():
    e = _elig("TPE-ORD", "L")
    c = assess(e, official_confirmed=True)
    assert c.level == "High"
    assert c.is_official is True


def test_official_waitlist_is_medium_and_official():
    c = assess(_elig("TPE-ORD", "L"), official_waitlist=True)
    assert c.level == "Medium"
    assert c.is_official is True


def test_expertflyer_strong_clue_is_medium_not_official():
    c = assess(_elig("TPE-ORD", "L"), expertflyer_clue="strong")
    assert c.level == "Medium"
    assert c.is_official is False
    assert "NOT official" in c.reasoning


def test_expertflyer_weak_clue_is_low():
    c = assess(_elig("TPE-ORD", "L"), expertflyer_clue="weak")
    assert c.level == "Low"


def test_seatmap_only_is_low():
    c = assess(_elig("TPE-ORD", "L"), seatmap_only=True)
    assert c.level == "Low"


def test_unknown_defaults_to_low():
    c = assess(_elig("TPE-ORD", "L"))
    assert c.level == "Low"
