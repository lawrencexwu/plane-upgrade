from src.confidence import assess
from src.upgrade_rules import classify_fare_class, load_chart


def _fc(code):
    return classify_fare_class(load_chart(), code)


def test_non_upgradeable_do_not_buy():
    assert assess(_fc("P")).level == "Do Not Buy"


def test_avws_do_not_buy():
    for c in ("A", "V", "W", "S"):
        assert assess(_fc(c)).level == "Do Not Buy"


def test_official_confirmed_high():
    a = assess(_fc("L"), official_confirmed=True)
    assert a.level == "High" and a.is_official


def test_official_waitlist_medium():
    a = assess(_fc("L"), official_waitlist=True)
    assert a.level == "Medium" and a.is_official


def test_expertflyer_strong_medium_not_official():
    a = assess(_fc("L"), expertflyer_clue="strong")
    assert a.level == "Medium" and a.is_official is False


def test_expertflyer_weak_low():
    assert assess(_fc("L"), expertflyer_clue="weak").level == "Low"


def test_seatmap_only_low():
    assert assess(_fc("L"), expertflyer_clue="seatmap_only").level == "Low"


def test_unknown_low():
    assert assess(_fc("L")).level == "Low"
