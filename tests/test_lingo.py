from pqcli.lingo import indefinite, to_roman


def test_indefinite_article() -> None:
    assert indefinite("Orc", 1) == "an Orc"
    assert indefinite("Ürn", 1) == "an Ürn"
    assert indefinite("über-Orc", 1) == "an über-Orc"
    assert indefinite("?", 1) == "a ?"
    assert indefinite("Rat", 1) == "a Rat"
