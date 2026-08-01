from app.retrieval.text_utils import clean_title


def test_strips_escaped_html_entities():
    raw = "The &lt;i&gt;Comrades Marathon&lt;/i&gt;: a narrative review of physiological responses"
    assert clean_title(raw) == "The Comrades Marathon: a narrative review of physiological responses"


def test_strips_real_tags():
    assert clean_title("A study of <b>VO2max</b> in athletes") == "A study of VO2max in athletes"


def test_leaves_clean_title_unchanged():
    assert clean_title("Effects of creatine supplementation on kidney function") == "Effects of creatine supplementation on kidney function"


def test_handles_none_and_empty():
    assert clean_title(None) == ""
    assert clean_title("") == ""
