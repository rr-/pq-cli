import datetime
import typing as T

from pqcli import random


def format_float(num: float) -> str:
    ret = f"{num:.01f}"
    if ret.endswith("0"):
        ret = ret[:-2]
    return ret


def format_timespan(timespan: datetime.timedelta) -> str:
    num = timespan.total_seconds()
    if num < 60.0:
        return f"~{int(num)}s"
    num /= 60
    if num < 60.0:
        return f"~{int(num)}m"
    num /= 60
    if num < 24.0:
        return f"~{format_float(num)}h"
    num /= 24
    return f"~{format_float(num)}d"


def generate_name() -> str:
    parts = [
        "br|cr|dr|fr|gr|j|kr|l|m|n|pr||||r|sh|tr|v|wh|x|y|z".split("|"),
        "a|a|e|e|i|i|o|o|u|u|ae|ie|oo|ou".split("|"),
        "b|ck|d|g|k|m|n|p|t|v|x|z".split("|"),
    ]
    result = ""
    for i in range(6):
        result += random.choice(parts[i % 3])
    return result.title()


def to_roman(num: int) -> str:
    if not num:
        return "N"

    ret = ""

    def _rome(dn: int, ds: str) -> bool:
        nonlocal num, ret
        if num >= dn:
            num -= dn
            ret += ds
            return True
        return False

    if num < 0:
        ret = "-"
        num = -num

    while _rome(1000, "M"):
        pass
    _rome(900, "CM")
    _rome(500, "D")
    _rome(400, "CD")
    while _rome(100, "C"):
        pass
    _rome(90, "XC")
    _rome(50, "L")
    _rome(40, "XL")
    while _rome(10, "X"):
        pass
    _rome(9, "IX")
    _rome(5, "V")
    _rome(4, "IV")
    while _rome(1, "I"):
        pass
    return ret


def act_name(act: int) -> str:
    if act == 0:
        return "Prologue"
    return f"Act {to_roman(act)}"


def plural(subject: str) -> str:
    if subject.endswith("y"):
        return subject[:-1] + "ies"
    if subject.endswith("us"):
        return subject[:-2] + "i"
    if subject.endswith(("ch", "x", "s", "sh")):
        return subject + "es"
    if subject.endswith("f"):
        return subject[:-1] + "ves"
    if subject.endswith(("man", "Man")):
        return subject[:-2] + "en"
    return subject + "s"


def indefinite(subject: str, qty: int) -> str:
    if qty == 1:
        if subject.startswith(tuple("AEIOU?aeiou?")):
            return "an " + subject
        return "a " + subject
    return str(qty) + " " + plural(subject)


def definite(subject: str, qty: int) -> str:
    if qty > 1:
        subject = plural(subject)
    return "the " + subject


def prefix(a: T.List[str], m: int, subject: str, sep: str = " ") -> str:
    m = abs(m)
    if m < 1 or m > len(a):
        return subject
    return a[m - 1] + sep + subject


def sick(m: int, subject: str) -> str:
    m = 6 - abs(m)
    return prefix(
        ["dead", "comatose", "crippled", "sick", "undernourished"], m, subject
    )


def young(m: int, subject: str) -> str:
    m = 6 - abs(m)
    return prefix(
        ["foetal", "baby", "preadolescent", "teenage", "underage"], m, subject
    )


def big(m: int, subject: str) -> str:
    return prefix(
        ["greater", "massive", "enormous", "giant", "titanic"], m, subject
    )


def special(m: int, subject: str) -> str:
    if " " in subject:
        return prefix(
            ["veteran", "cursed", "warrior", "undead", "demon"], m, subject
        )
    return prefix(
        ["Battle-", "cursed ", "Were-", "undead ", "demon "], m, subject, ""
    )


def terminate_message(player_name: str) -> str:
    adjective = random.choice(["faithful", "noble", "loyal", "brave"])
    return f"Terminate {adjective} {player_name}?"
