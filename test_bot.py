"""Run with: uv run test_bot.py"""

from bot import parse

assert parse("TE23A") == ("TE23A", None, False)
assert parse("  TE23A -w ") == ("TE23A", None, True)
assert parse("TE23A -w42") == ("TE23A", 42, True)
assert parse("KFN") == ("KFN", None, False)
assert parse("EE 23-B -w7") == ("EE 23-B", 7, True)

assert parse("TE23A -w99") is None  # no such week
assert parse("TE23A -w0") is None
assert parse("200501011234") is None  # personnummer, 12 digits
assert parse("050101-1234") is None  # personnummer, 10 digits with hyphen
assert parse("0501011234 -w") is None
assert parse("") is None
assert parse("-w") is None  # option without an ID
assert parse("A" * 21) is None  # too long
assert parse("TE23A; rm -rf /") is None  # only letters, digits, space, hyphen

print("ok")
