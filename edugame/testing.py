"""Checks for a game's browser test (Playwright, sync API): the keyboard and the panels.

    from edugame import testing
    rows = testing.check_keys_list(page, where=frame)          # ? and /: the list of keys
    testing.check_panel(page, lambda: frame.click("#helpButton"), "#helpBack", where=frame)

`page` is the Playwright page (it has the keyboard); `where` is the frame the game is in, if it's in one (the kit's
test page and Kolibri run games in a frame), otherwise the page. Each check raises AssertionError with what went
wrong. See docs/ACCESSIBILITY.md.
"""

_ACTIVE = """() => { const a = document.activeElement; if (!a || a === document.body) return '';
    return a.id ? '#' + a.id : a.tagName.toLowerCase() + (a.className && typeof a.className === 'string' ? '.' + a.className.trim().split(/\\s+/).join('.') : ''); }"""


def focused(where):
    """What has the keyboard, as '#id' or 'tag.class' ('' for nothing)."""
    return where.evaluate(_ACTIVE)


def _inside(where, selector):
    return where.evaluate("s => { const p = document.querySelector(s); return !!p && p.contains(document.activeElement); }", selector)


def _shown(where, selector):
    return where.evaluate("""s => { const p = document.querySelector(s);
        return !!p && !p.hidden && !p.classList.contains('hidden') && p.getClientRects().length > 0; }""", selector)


def check_panel(page, open_it, panel, where=None, opener=None, tabs=4, close_key="Escape"):
    """open_it() opens a panel (selector `panel`): it must show, have the keyboard, keep it while Tab and Shift+Tab
    are pressed, close with Escape, and give the keyboard back to what had it before (or to `opener`, a selector,
    when open_it clicks a button: the click gives that button the keyboard)."""
    where = where or page
    before = focused(where)
    open_it()
    page.wait_for_timeout(100)
    assert _shown(where, panel), "%s didn't open" % panel
    assert _inside(where, panel), "%s opened without the keyboard (it's on %r)" % (panel, focused(where))
    for _ in range(tabs):
        page.keyboard.press("Tab")
        assert _inside(where, panel), "Tab left %s (the keyboard went to %r)" % (panel, focused(where))
    for _ in range(tabs):
        page.keyboard.press("Shift+Tab")
        assert _inside(where, panel), "Shift+Tab left %s (the keyboard went to %r)" % (panel, focused(where))
    page.keyboard.press(close_key)
    page.wait_for_timeout(100)
    assert not _shown(where, panel), "%s didn't close with %s" % (panel, close_key)
    after = focused(where)
    if opener:
        back = where.evaluate("s => document.querySelector(s) === document.activeElement", opener)
        assert back, "the keyboard didn't go back to %s after %s: it's on %r" % (opener, panel, after)
    else:
        assert after == before, "the keyboard didn't go back after %s: it was on %r, now %r" % (panel, before, after)


def check_keys_list(page, where=None, keys=("?", "/")):
    """The kit's list of keys (EduGame.addKeys): each of `keys` opens it as a panel (check_panel). Returns its rows
    as [(key, what it does)], headings as (heading, None)."""
    where = where or page
    for k in keys:
        check_panel(page, lambda: page.keyboard.press(k), ".eg-keys", where=where)
    where.evaluate("EduGame.openKeys()")
    rows = where.evaluate("""() => [...document.querySelectorAll('.eg-keys dl > *')].reduce((out, el) => {
        if (el.classList.contains('eg-keys-part')) out.push([el.textContent, null]);
        else if (el.tagName === 'DT') out.push([el.textContent, '']);
        else out[out.length - 1][1] = el.textContent;
        return out; }, [])""")
    where.evaluate("EduGame.closeKeys()")
    assert rows, "the list of keys is empty"
    return [tuple(r) for r in rows]
