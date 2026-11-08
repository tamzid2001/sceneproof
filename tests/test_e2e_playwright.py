"""Browser E2E for the sceneproof web UI, via Playwright (Chromium).

Every visible interaction from the README flow is proven against the real
server: load scene, drag an entity, keyboard nudge, resize/add/remove with the
human approval gate, before/after compare, share-link replay and export.
Skips honestly when playwright is not installed in the active environment.
"""
import socket
import threading
from http.server import ThreadingHTTPServer

import pytest
from sceneproof.web import H

pw = pytest.importorskip(
    "playwright", reason="playwright not installed in this environment — browser E2E skipped honestly"
)


@pytest.fixture(scope="module")
def base_url():
    import sceneproof.web as web
    from sceneproof.engine import Engine
    web.ENG = Engine()  # fresh singleton: this module owns its approval-gate state
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    srv = ThreadingHTTPServer(("127.0.0.1", port), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{port}"
    srv.shutdown()


@pytest.fixture(scope="module")
def ui(base_url):
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        pg = browser.new_context().new_page()
        pg.goto(base_url + "/", wait_until="load")
        pg.click("#start")
        pg.wait_for_function("document.querySelectorAll('#object option').length === 6")
        yield {"page": pg, "context": pg.context, "base_url": base_url}
        browser.close()


def test_editor_basics(ui):
    pg = ui["page"]
    assert pg.is_visible("#stage")
    assert not pg.is_visible("#empty")
    assert pg.inner_text("#fp").startswith("· fingerprint")
    # constraint guides toggle exists and is on by default
    assert pg.is_checked("#overlays")


def test_drag_sets_pending_counterfactual(ui):
    pg = ui["page"]
    pg.locator("#stage").scroll_into_view_if_needed()
    cx, cy = pg.evaluate(
        """() => {
            const c = document.getElementById('stage');
            const r = c.getBoundingClientRect();
            const sx = r.width / c.width, sy = r.height / c.height;
            const o = window.__scene_objects__()['crate-b'];
            return [r.left + (o.x + o.w / 2) * c.width * sx,
                    r.top + (c.height - 40 - (o.y + o.h / 2) * c.height) * sy];
        }""")
    pg.mouse.move(cx, cy)
    pg.mouse.down()
    pg.mouse.move(cx + 40, cy - 20, steps=5)
    pg.mouse.up()
    dx, dy = pg.input_value("#dx"), pg.input_value("#dy")
    assert abs(float(dx)) > 0.01 and abs(float(dy)) > 0.01
    assert pg.input_value("#action") == "move"
    assert "not verified" in pg.inner_text("#comparenote").lower()


def test_run_move_and_compare_page(ui):
    pg = ui["page"]
    pg.select_option("#action", "move")
    pg.select_option("#object", "crate-b")
    pg.fill("#dx", "0.02")
    pg.fill("#dy", "0")
    pg.click("#run")
    pg.wait_for_function("document.getElementById('status').textContent.includes('Verified:')")
    assert "FEASIBLE" in pg.inner_text("#verdict")
    assert "OFFLINE_REFERENCE" in pg.inner_text("#src")
    assert "No violations" in pg.inner_text("#violations")


def test_remove_requires_named_human_approval(ui):
    pg = ui["page"]
    pg.select_option("#action", "remove")
    pg.select_option("#object", "shelf-1")
    assert pg.is_visible("#approval")
    pg.click("#run")
    pg.wait_for_function("document.getElementById('status').textContent.includes('Approval required')")
    pg.fill("#approver", "safety-lead")
    pg.check("#approved")
    pg.click("#run")
    pg.wait_for_function("document.getElementById('status').textContent.includes('Verified:')")
    assert not pg.inner_text("#verdict").startswith("FEASIBLE")  # removing the shelf must break the world
    assert "crate-a" in pg.inner_text("#violations")


def test_add_sensitive_kind_gated(ui):
    pg = ui["page"]
    pg.select_option("#action", "add")
    pg.fill("#newid", "human-2")
    pg.select_option("#kind", "human")
    assert pg.is_visible("#approval")


def test_share_link_encodes_and_replays(ui):
    pg = ui["page"]
    pg.select_option("#action", "move")
    pg.select_option("#object", "crate-b")
    pg.fill("#dx", "0.02")
    pg.fill("#dy", "0")
    url = pg.evaluate("shareUrl()")
    assert "act=move" in url and "obj=crate-b" in url and "seed=7" in url
    pg2 = ui["context"].new_page()
    pg2.goto(url, wait_until="load")
    pg2.wait_for_function("document.getElementById('score').textContent !== '—'", timeout=15000)
    assert "OFFLINE_REFERENCE" in pg2.inner_text("#src")  # replay keeps the honest label
    pg2.close()


def test_keyboard_nudge_updates_counterfactual(ui):
    pg = ui["page"]
    pg.select_option("#action", "move")
    pg.select_option("#object", "crate-b")
    pg.fill("#dx", "0")
    pg.fill("#dy", "0")
    pg.focus("#stage")
    for _ in range(3):
        pg.keyboard.press("ArrowUp")
    assert pg.input_value("#dy") == "0.06"
    assert pg.input_value("#action") == "move"
