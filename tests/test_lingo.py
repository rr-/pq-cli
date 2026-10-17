from pqcli.lingo import indefinite, to_arabic, to_roman


def test_indefinite_article() -> None:
    assert indefinite("Orc", 1) == "an Orc"
    assert indefinite("Ürn", 1) == "an Ürn"
    assert indefinite("über-Orc", 1) == "an über-Orc"
    assert indefinite("?", 1) == "a ?"
    assert indefinite("Rat", 1) == "a Rat"


def test_to_roman() -> None:
    assert to_roman(0) == "N"
    assert to_roman(-4) == "-IV"
    assert to_roman(1994) == "MCMXCIV"
    # pq-web aa37e4a: T = 10000, A = 5000
    assert to_roman(4000) == "MA"
    assert to_roman(5000) == "A"
    assert to_roman(9000) == "MT"
    assert to_roman(14999) == "TMACMXCIX"
    assert to_roman(23456) == "TTMMMCDLVI"


def test_to_arabic_inverts_to_roman() -> None:
    for num in [*range(1, 5000), 9000, 9999, 14999, 23456]:
        assert to_arabic(to_roman(num)) == num
    assert to_arabic("N") == 0
    assert to_arabic("iv") == 4
