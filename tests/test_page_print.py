"""Print copies preserve complete nested JSON without executing source markup."""

import json
from html.parser import HTMLParser

from evidenceforge.page_print import json_print_html


def test_print_json_contains_all_nested_records_as_escaped_text():
    class Content(HTMLParser):
        def __init__(self):
            super().__init__(convert_charrefs=True)
            self.tags = []
            self.text = []

        def handle_starttag(self, tag, attrs):
            self.tags.append(tag)

        def handle_data(self, data):
            self.text.append(data)

    value = {"nested": {"records": [{"quote": "</pre><script>alert(1)</script>&"}]}}
    parser = Content()
    parser.feed(json_print_html(value))
    assert parser.tags == ["pre"]
    assert json.loads("".join(parser.text)) == value


def test_scalar_progress_value_has_valid_interactive_and_print_json():
    import pytest

    pytest.importorskip("streamlit")
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_string(
        "from evidenceforge.ui import show_json\nshow_json('completed')",
        default_timeout=90,
    ).run()
    assert not at.exception and not at.error
    assert json.loads(at.get("json")[0].proto.body) == "completed"
