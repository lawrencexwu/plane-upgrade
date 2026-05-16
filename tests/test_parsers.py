from src.parsers import parse_expertflyer, parse_fare_quote


def test_parse_fare_extracts_price_class_cabin():
    txt = ("EVA Air BR55 TPE-ORD\nPremium Economy (L) Standard\n"
           "Total: TWD 80,000")
    p = parse_fare_quote(txt)
    assert p.cabin == "Premium Economy"
    assert p.fare_class == "L"
    assert p.fare_family == "Standard"
    assert p.price == 80000.0
    assert p.currency == "TWD"
    assert "BR55" in p.flight_numbers


def test_parse_fare_warns_when_class_missing():
    p = parse_fare_quote("Economy fare total USD 1,800")
    assert p.fare_class is None
    assert any("Fare class" in w for w in p.warnings)


def test_parse_expertflyer_strong_when_business_buckets_open():
    txt = "BR15 LAX-TPE Boeing 777-300ER 00:50 05:20 J9 C9 D4 Z0"
    p = parse_expertflyer(txt)
    assert p.flight_number == "BR15"
    assert p.open_business_buckets >= 2
    assert p.suggested_clue == "strong"


def test_parse_expertflyer_seatmap_only():
    p = parse_expertflyer("BR15 seat map shows several unassigned seats")
    assert p.suggested_clue == "seatmap_only"


def test_parse_expertflyer_always_disclaims():
    p = parse_expertflyer("BR15 J9")
    assert any("third-party" in w for w in p.warnings)
