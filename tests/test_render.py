"""Render seam: slot JSON → template → HTML; hostile fragments defanged (TRD §6)."""

import pytest

from server.errors import ValidationRejected
from server.services import postcards as postcard_service
from server.services.postcards import sanitize_offer_html


def test_sanitizer_strips_scripts_and_event_handlers():
    hostile = '<script>alert(1)</script><img src=x onerror=alert(1)><b>OK</b>'
    cleaned = sanitize_offer_html(hostile)
    assert "<script" not in cleaned and "onerror" not in cleaned and "<img" not in cleaned
    assert "<b>OK</b>" in cleaned


def test_sanitizer_limits_style_to_color_and_font_size():
    cleaned = sanitize_offer_html(
        '<span style="color:#1d4e8a; position:absolute; font-size:14px; background:url(x)">hi</span>'
    )
    assert "color: #1d4e8a" in cleaned and "font-size: 14px" in cleaned
    assert "position" not in cleaned and "background" not in cleaned


def test_slot_validation_enforces_spec(session, campaign):
    with pytest.raises(ValidationRejected) as e:
        postcard_service.save_draft(
            session,
            campaign["id"],
            [
                {
                    "slot": 99,
                    "headline": "way too many words in this headline to pass",
                    "offer_text": "one two three four five six seven eight nine ten eleven twelve thirteen",
                    "accent_color": "blue",
                }
            ],
        )
    msg = str(e.value)
    assert "1..8" in msg and "≤ 6 words" in msg and "≤ 12 words" in msg and "hex color" in msg


def test_unknown_template_rejected_naming_available(session, campaign):
    with pytest.raises(ValidationRejected, match="grid-4x2-v1"):
        postcard_service.save_draft(
            session, campaign["id"], [{"slot": 1, "headline": "Hi"}], template_id="fancy-9000"
        )


def test_render_stable_structure_and_empty_slot_placeholders(session, campaign):
    postcard_service.save_draft(
        session,
        campaign["id"],
        [
            {
                "slot": 1,
                "headline": "Roof storm check, free",
                "offer_text": "Free 20-point roof inspection this month",
                "contact_line": "(765) 555-0142",
                "accent_color": "#8a2f1d",
                "offer_html": '<b>Free</b> <span style="color:#8a2f1d">inspection</span><script>x()</script>',
            }
        ],
    )
    out = postcard_service.render(session, campaign["id"])
    html = out["html"]
    assert out["version"] == 1 and out["template_id"] == "grid-4x2-v1"
    assert "Local Business Spotlight — July" in html
    assert "Roof storm check, free" in html
    assert "<script" not in html
    assert html.count("this space available") == 7  # 8 slots, 1 filled
    assert 'class="slot empty"' in html


def test_render_versions_select_and_404(session, campaign):
    from server.errors import NotFound

    with pytest.raises(NotFound, match="No postcard drafts yet"):
        postcard_service.render(session, campaign["id"])
    postcard_service.save_draft(session, campaign["id"], [{"slot": 1, "headline": "V one"}])
    postcard_service.save_draft(session, campaign["id"], [{"slot": 1, "headline": "V two"}])
    assert "V one" in postcard_service.render(session, campaign["id"], version=1)["html"]
    assert "V two" in postcard_service.render(session, campaign["id"])["html"]
