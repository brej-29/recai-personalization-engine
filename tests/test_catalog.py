from kindred.build_catalog import clean, components, drop_first_sentence, mk_text


def test_clean_strips_html_and_source_notes():
    raw = "A <b>boy</b> wakes.<br>He&nbsp;runs. (Source: Somewhere) Note: sequel announced."
    assert clean(raw) == "A boy wakes. He runs."


def test_drop_first_sentence_removes_title_and_cast_line():
    lead = "Foo is a 2001 American drama film directed by Bar. A man loses his farm and walks west."
    assert drop_first_sentence(lead) == "A man loses his farm and walks west."
    assert drop_first_sentence("One sentence only.") == ""


def test_mk_text_is_title_free_and_stable():
    assert mk_text("Plot.", ["Drama"], ["Elf"]) == "Plot. Genres: Drama. Themes: Elf."


def test_components_join_related_titles():
    rows = [
        {"_aid": 1, "_rel": [2], "id": "al:1"},
        {"_aid": 2, "_rel": [], "id": "al:2"},
        {"_aid": 3, "_rel": [], "id": "al:3"},
        {"id": "im:tt1"},
    ]
    components(rows)
    assert rows[0]["comp"] == rows[1]["comp"] != rows[2]["comp"]
    assert rows[3]["comp"] == "im:tt1"
