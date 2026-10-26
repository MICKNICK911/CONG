#!/usr/bin/env python3
"""
Month-band tinting for the Stats table in index.html.

What it does:
  * Month header cell  ->  darker tint  (--mh)
  * Week header cells  ->  darker tint  (--mh)  [same band as month header]
  * Empty body cells   ->  lighter tint (--mt)
  * First column of each month (except the very first) -> 2px left border (--me)
  * Assigned cells keep their existing bgOf() colour (inline style wins)
  * Convention (cvc) cells get tinted like the rest of the month
  * Only one month shown -> nothing happens (nothing to separate)
  * 6 pastel hues cycling positionally; dark-mode palette included

Run in the same directory as index.html:
    python3 patch_stats_months.py
Then hard-refresh the page (Ctrl+F5 / Cmd+Shift+R).
"""
import sys
import pathlib

# ----------------------------------------------------------------------------
# 1) CSS — palette + rules.  Appended after the existing .st rules so that
#    .mt-empty overrides .cvc when both apply (never happens in practice,
#    because we only set one of them at a time, but ordering is safe anyway).
# ----------------------------------------------------------------------------
CSS_ANCHOR = ".st td.cvc{background:var(--sec)}.st td.tot{font-weight:600;font-size:12px}"

CSS_INSERT = CSS_ANCHOR + """

/* ---- month band tints (stats table) ---- */
.st .m0{--mt:#eef4fb;--mh:#dbe8f6;--me:#a9c4e0}
.st .m1{--mt:#fcf6ea;--mh:#f6e8c9;--me:#dcc088}
.st .m2{--mt:#ecf5ee;--mh:#d7ecdb;--me:#a9c9af}
.st .m3{--mt:#f4eef9;--mh:#e4d7ef;--me:#bda9d6}
.st .m4{--mt:#fdf1ed;--mh:#f8ddd5;--me:#e0b1a1}
.st .m5{--mt:#eaf5f5;--mh:#d3ebe9;--me:#a0cbc6}
@media (prefers-color-scheme:dark){
 .st .m0{--mt:#1a2330;--mh:#22344a;--me:#3d5a7a}
 .st .m1{--mt:#2b251a;--mh:#3d3322;--me:#7a5a2a}
 .st .m2{--mt:#1c2820;--mh:#2a3d30;--me:#4a7a55}
 .st .m3{--mt:#231c2d;--mh:#342a42;--me:#6a5080}
 .st .m4{--mt:#2d1f1a;--mh:#422a22;--me:#8a4a3a}
 .st .m5{--mt:#1a2828;--mh:#253d3a;--me:#4a7a72}
}
.st th.mhd{background:var(--mh)}
.st td.mt-empty{background:var(--mt)}
.st .mfirst{border-left:2px solid var(--me)}"""

# ----------------------------------------------------------------------------
# 2) Header rows — compute month index per week, colour both <th> rows, mark
#    the first week-column of every month (except month index 0) for a left
#    border.
# ----------------------------------------------------------------------------
HDR_ANCHOR = (
    " var wrap=el('div','sw2'),t=el('table','st'),h1=el('tr'),h2=el('tr'),th=el('th','nc','Name');th.rowSpan=2;h1.appendChild(th);\n"
    " var g0=null;ws.forEach(function(w){var k=w.mon.slice(0,7);if(g0&&g0.k===k)g0.n++;else{g0={k:k,n:1,th:el('th','',mname(k))};h1.appendChild(g0.th)}g0.th.colSpan=g0.n;\n"
    "  var c=el('th','',lab(w).replace(/^[A-Za-z]+ /,'').replace(' - ','\u2013'));if(w.cv)c.appendChild(el('div','','Conv.'));h2.appendChild(c)});"
)

HDR_INSERT = (
    " var wrap=el('div','sw2'),t=el('table','st'),h1=el('tr'),h2=el('tr'),th=el('th','nc','Name');th.rowSpan=2;h1.appendChild(th);\n"
    " var monIdx={},nextIdx=0;ws.forEach(function(w){var k=w.mon.slice(0,7);if(!(k in monIdx))monIdx[k]=nextIdx++});\n"
    " var monthsCount=nextIdx,prevMon=null;\n"
    " var g0=null;ws.forEach(function(w){var k=w.mon.slice(0,7);if(g0&&g0.k===k)g0.n++;else{g0={k:k,n:1,th:el('th','',mname(k))};if(monthsCount>1)g0.th.className='mhd m'+monIdx[k]+(monIdx[k]>0?' mfirst':'');h1.appendChild(g0.th)}g0.th.colSpan=g0.n;\n"
    "  var c=el('th','',lab(w).replace(/^[A-Za-z]+ /,'').replace(' - ','\u2013'));if(monthsCount>1){var hcls='mhd m'+monIdx[k];if(k!==prevMon&&monIdx[k]>0)hcls+=' mfirst';c.className=hcls}if(w.cv)c.appendChild(el('div','','Conv.'));h2.appendChild(c);prevMon=k});"
)

# ----------------------------------------------------------------------------
# 3) Body cells — assigned cells keep bgOf(); empty cells get the light tint;
#    first-of-month column gets the left border on every row.
# ----------------------------------------------------------------------------
BODY_ANCHOR = (
    "  gr[1].forEach(function(n){var r=el('tr');r.appendChild(el('td','nc',n));\n"
    "   ws.forEach(function(w){var c=el('td',w.cv?'cvc':''),a=((map[g]||{})[n]||{})[w.id];if(a){c.style.background=bgOf(a);c.title=n+' \u00b7 '+g+' \u00b7 '+lab(w)}r.appendChild(c)});\n"
    "   r.appendChild(el('td','tot',((tot[g]||{})[n])||0));tb.appendChild(r)})});"
)

BODY_INSERT = (
    "  gr[1].forEach(function(n){var r=el('tr');r.appendChild(el('td','nc',n));var pm=null;\n"
    "   ws.forEach(function(w){var k=w.mon.slice(0,7),isf=k!==pm,ccls=[],c=el('td'),a=((map[g]||{})[n]||{})[w.id];\n"
    "    if(monthsCount>1){ccls.push('m'+monIdx[k]);if(isf&&monIdx[k]>0)ccls.push('mfirst');if(!a)ccls.push('mt-empty')}else if(w.cv)ccls.push('cvc');\n"
    "    if(ccls.length)c.className=ccls.join(' ');\n"
    "    if(a){c.style.background=bgOf(a);c.title=n+' \u00b7 '+g+' \u00b7 '+lab(w)}\n"
    "    r.appendChild(c);pm=k});\n"
    "   r.appendChild(el('td','tot',((tot[g]||{})[n])||0));tb.appendChild(r)})});"
)

# ----------------------------------------------------------------------------
def patch(text, anchor, replacement, label):
    n = text.count(anchor)
    if n == 0:
        print(f"[FAIL] anchor not found: {label}", file=sys.stderr)
        sys.exit(1)
    if n > 1:
        print(f"[FAIL] anchor found {n} times (expected 1): {label}", file=sys.stderr)
        sys.exit(1)
    return text.replace(anchor, replacement, 1)

def main():
    p = pathlib.Path("index.html")
    if not p.exists():
        print("[FAIL] index.html is not in the current directory.", file=sys.stderr)
        sys.exit(1)

    src = p.read_text(encoding="utf-8")
    if "month band tints (stats table)" in src:
        print("Already patched — nothing to do.")
        return

    out = src
    out = patch(out, CSS_ANCHOR,  CSS_INSERT,  "stats CSS")
    out = patch(out, HDR_ANCHOR,  HDR_INSERT,  "stats header rows")
    out = patch(out, BODY_ANCHOR, BODY_INSERT, "stats body cells")

    p.with_suffix(".html.bak").write_text(src, encoding="utf-8")
    p.write_text(out, encoding="utf-8")
    print("Patched index.html  (backup: index.html.bak)")
    print("Reload with a hard refresh (Ctrl+F5 / Cmd+Shift+R).")

if __name__ == "__main__":
    main()