from aps_bot.relay import split_content


def test_empty_content_has_no_chunks() -> None:
    assert split_content("") == []


def test_short_content_is_unchanged() -> None:
    assert split_content("hello") == ["hello"]


def test_long_content_preserves_every_character() -> None:
    content = "a" * 2001
    chunks = split_content(content)
    assert [len(chunk) for chunk in chunks] == [2000, 1]
    assert "".join(chunks) == content


def test_prefers_newline_boundary() -> None:
    content = "a" * 1995 + "\n" + "b" * 20
    chunks = split_content(content)
    assert chunks[0].endswith("\n")
    assert "".join(chunks) == content

