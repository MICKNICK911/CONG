#!/usr/bin/env python3
"""
patch_index.py - adds PDF import fallback to index.html

Patches:
1. Adds firstMondayOf, findBible, splitPartLine, parsePageWeeks helpers
2. Adds _pdfHint global for filename-derived year/month
3. Modifies monFor to prefer precomputed r.mon
4. Modifies parseLines to fall back to parsePageWeeks when header parsing fails
5. Modifies pickPdf to extract year/month from filename
6. Adds editable Bible reading field in drawReview

Idempotent: running twice is safe.
"""

import sys
import re
import shutil
from pathlib import Path
from datetime import datetime

# Markers to detect idempotency
HELPERS_MARKER = "/*__PDF_PATCH_HELPERS__*/"
PDF_HINT_MARKER = "var _pdfHint="

def patch(html: str) -> tuple[str, list[str]]:
    log = []
    
    # --- 1. Add helpers after ML array ---
    if HELPERS_MARKER not in html:
        ML_ANCHOR = ("var MS=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'],"
                     "ML=['January','February','March','April','May','June','July','August',"
                     "'September','October','November','December'];")
        if ML_ANCHOR not in html:
            raise RuntimeError("ML anchor not found - file structure changed")
        
        helpers = (
            "\n" + HELPERS_MARKER + "\n"
            "var _pdfHint=null;\n"
            "function firstMondayOf(y,m){var d=new Date(Date.UTC(y,m,1));"
            "while(d.getUTCDay()!==1)d.setUTCDate(d.getUTCDate()+1);return iso(d)}\n"
            "function findBible(lines){\n"
            "  var PAT=/[1-3]?\\s*[A-Z][A-Z'’\\-]*(?:\\s+[A-Z][A-Z'’\\-]*)*\\s+\\d{1,3}\\s*[-–—]\\s*\\d{1,3}/;\n"
            "  var OLD=/\\|\\s*([1-3]?\\s*[A-Z][A-Z'’\\-]*(?:\\s+[A-Z][A-Z'’\\-]*)*\\s+\\d{1,3}\\s*[-–—]\\s*\\d{1,3})/;\n"
            "  for(var i=0;i<lines.length;i++){\n"
            "    var s=lines[i].replace(/\\s+/g,' ').trim().toUpperCase();\n"
            "    if(!s)continue;\n"
            "    if(/^SONG\\s+\\d+/.test(s))continue;\n"
            "    if(/^\\d{1,3}$/.test(s))continue;\n"
            "    if(/^\\d{1,2}\\.\\s/.test(s))continue;\n"
            "    var m=s.match(OLD)||s.match(PAT);\n"
            "    if(m)return(m[1]||m[0]).replace(/\\s+/g,' ').trim();\n"
            "  }\n"
            "  return '';\n"
            "}\n"
            "function splitPartLine(line){\n"
            "  var re=/(^|\\s)(\\d{1,2})\\.\\s+/g,m,idxs=[];\n"
            "  while((m=re.exec(line))!==null)idxs.push({n:+m[2],start:m.index,content:re.lastIndex});\n"
            "  if(!idxs.length)return null;\n"
            "  var out=[];\n"
            "  for(var i=0;i<idxs.length;i++){\n"
            "    var end=i+1<idxs.length?idxs[i+1].start:line.length;\n"
            "    out.push({n:idxs[i].n,text:line.slice(idxs[i].content,end).trim()});\n"
            "  }\n"
            "  return out;\n"
            "}\n"
            "function parsePageWeeks(P,m0,yr){\n"
            "  if(!P.length)return [];\n"
            "  var weekStart=/^\\s*1\\.\\s+\\S.*\\((?:Simma\\s+\\d+|\\d+\\s*min)/i;\n"
            "  var weekPages=[];\n"
            "  P.forEach(function(lines,pi){\n"
            "    if(pi===0)return;\n"
            "    if(lines.some(function(ln){return weekStart.test(ln)}))weekPages.push(pi);\n"
            "  });\n"
            "  if(!weekPages.length)return [];\n"
            "  var coverTxt=(P[0]||[]).join(' ').toUpperCase();\n"
            "  var cm=coverTxt.match(/JANUARY|FEBRUARY|MARCH|APRIL|MAY|JUNE|JULY|AUGUST|SEPTEMBER|OCTOBER|NOVEMBER|DECEMBER/);\n"
            "  var startMonth=cm?MN.indexOf(cm[0]):(m0>=0?m0:(_pdfHint?_pdfHint.month:0));\n"
            "  var useYear=_pdfHint?_pdfHint.year:yr;\n"
            "  var firstMon=firstMondayOf(useYear,startMonth);\n"
            "  var W=[];\n"
            "  weekPages.forEach(function(pi,wi){\n"
            "    var cur={key:'auto-'+wi,sm:startMonth,day:0,mon:add(firstMon,7*wi),"
            "bible:findBible(P[pi]),songs:['','',''],parts:[]};\n"
            "    var sec=1;\n"
            "    var songSlot=0;\n"
            "    var open=null;\n"
            "    var end=weekPages[wi+1]||P.length;\n"
            "    function close(){\n"
            "      if(!open)return;\n"
            "      var t=open.text,mm=minM(t);\n"
            "      var ti=twFix((mm?t.slice(0,mm.index):t).replace(/[\\s,;:–-]+$/g,'').trim());\n"
            "      if(!cur.parts.some(function(p){return p.sec===open.sec&&p.n===open.n}))\n"
            "        cur.parts.push({sec:open.sec,n:open.n,t:ti,m:mm?Math.max(+mm[1],+(mm[2]||0)):null});\n"
            "      open=null;\n"
            "    }\n"
            "    for(var p=pi;p<end;p++){\n"
            "      P[p].forEach(function(ln){\n"
            "        var k=sk(ln);\n"
            "        if(k==='treasuresfromgodsword'||k==='biblemuakorade'){close();sec=1;return}\n"
            "        if(k==='applyyourselftothefieldministry'||k==='mawaninkuasnkaho'){close();sec=2;return}\n"
            "        if(k==='livingaschristians'||k==='kristofoabrab'){close();sec=3;return}\n"
            "        var sg=ln.match(/\\bSong\\s+(\\d+)/i)||ln.match(/(?:^|\\s)Dwom\\s+(\\d+)(?![\\d:])/);\n"
            "        if(sg&&!open){\n"
            "          if(songSlot<3){cur.songs[songSlot]=sg[1];songSlot++}\n"
            "          return;\n"
            "        }\n"
            "        var segs=splitPartLine(ln);\n"
            "        if(segs){\n"
            "          for(var si=0;si<segs.length;si++){\n"
            "            close();\n"
            "            open={sec:sec,n:segs[si].n,text:segs[si].text};\n"
            "            if(minM(open.text))close();\n"
            "          }\n"
            "        }else if(open){\n"
            "          open.text+=' '+ln;\n"
            "          if(open.text.length>200)open=null;\n"
            "          if(open&&minM(open.text))close();\n"
            "        }\n"
            "      });\n"
            "    }\n"
            "    close();\n"
            "    W.push(cur);\n"
            "  });\n"
            "  return W;\n"
            "}\n"
        )
        html = html.replace(ML_ANCHOR, ML_ANCHOR + helpers, 1)
        log.append("+ inserted helpers (firstMondayOf, findBible, splitPartLine, parsePageWeeks, _pdfHint)")
    else:
        log.append("= helpers already present, skipped")
    
    # --- 2. Modify monFor ---
    OLD_MONFOR = (
        "function monFor(r,R){var y=r.sm<R.m0?R.year+1:R.year;"
        "return monOf(iso(new Date(Date.UTC(y,r.sm,r.day))))}"
    )
    NEW_MONFOR = (
        "function monFor(r,R){if(r.mon)return r.mon;"
        "var y=r.sm<R.m0?R.year+1:R.year;"
        "return monOf(iso(new Date(Date.UTC(y,r.sm,r.day))))}"
    )
    if OLD_MONFOR in html:
        html = html.replace(OLD_MONFOR, NEW_MONFOR, 1)
        log.append("+ patched monFor to prefer precomputed r.mon")
    elif NEW_MONFOR in html:
        log.append("= monFor already patched")
    else:
        raise RuntimeError("monFor anchor not found")
    
    # --- 3. Modify parseLines tail ---
    OLD_TAIL = (
        " var f=W.length?(m0>-1?m0:W[0].sm):-1;"
        "var na=0,nb=0;P.forEach(function(Ls){Ls.forEach(function(x){"
        "if(/\\(Simma\\s+\\d/.test(x))na++;if(/\\d\\s*min\\.?\\)/i.test(x))nb++})});"
        "return{weeks:W,m0:f,year:yr,lang:na>nb?'tw':'en'}}"
    )
    NEW_TAIL = (
        " var na=0,nb=0;P.forEach(function(Ls){Ls.forEach(function(x){"
        "if(/\\(Simma\\s+\\d/.test(x))na++;if(/\\d\\s*min\\.?\\)/i.test(x))nb++})});"
        "var lang=na>nb?'tw':'en';"
        "if(!W.length){W=parsePageWeeks(P,m0,yr);}"
        "var f=W.length?(m0>-1?m0:W[0].sm):-1;"
        "return{weeks:W,m0:f,year:yr,lang:lang}}"
    )
    if OLD_TAIL in html:
        html = html.replace(OLD_TAIL, NEW_TAIL, 1)
        log.append("+ patched parseLines to fall back to parsePageWeeks")
    elif NEW_TAIL in html:
        log.append("= parseLines already patched")
    else:
        raise RuntimeError("parseLines tail anchor not found")
    
    # --- 4. pickPdf: set _pdfHint from filename before parseLines ---
    # Find: "var R=parseLines(L);"
    OLD_PICK = "var R=parseLines(L);if(!R.weeks.length)"
    NEW_PICK = (
        "var _fn=(f.files[0]&&f.files[0].name)||'',"
        "_fm=_fn.match(/mwb_[A-Za-z]+_(\\d{4})(\\d{2})/i);"
        "if(_fm)_pdfHint={year:+_fm[1],month:+_fm[2]-1};"
        "var R=parseLines(L);if(!R.weeks.length)"
    )
    if OLD_PICK in html and "_pdfHint={year" not in html:
        html = html.replace(OLD_PICK, NEW_PICK, 1)
        log.append("+ patched pickPdf to read year/month from filename (mwb_E_YYYYMM.pdf)")
    elif "_pdfHint={year" in html:
        log.append("= pickPdf already patched")
    else:
        log.append("! pickPdf anchor not found (skipped filename hint)")
    
    # --- 5. drawReview: add editable Bible field ---
    # Find the loop that adds cards; we insert after `c.appendChild(h);`
    # Pattern: within R.weeks.forEach... h.appendChild(...);c.appendChild(h);
    # We want to insert Bible input right after c.appendChild(h) in that loop.
    # The exact string is:
    # `h.appendChild(document.createTextNode(' '+lab({mon:mon})+(wkOf(mon)?' (exists)':'')+(r.bible?' · '+r.bible:'')+(r.songs.some(Boolean)?' · songs '+r.songs.join('/'):'')));c.appendChild(h);`
    # Then followed by `var n=0;w.items.forEach(...`
    OLD_DRAW = (
        "+(r.bible?' · '+r.bible:'')+(r.songs.some(Boolean)?' · songs '+r.songs.join('/'):'')));"
        "c.appendChild(h);\n"
        "  var n=0;w.items.forEach"
    )
    NEW_DRAW = (
        "+(r.bible?' · '+r.bible:'')+(r.songs.some(Boolean)?' · songs '+r.songs.join('/'):'')));"
        "c.appendChild(h);\n"
        "  var bbi=el('input');bbi.type='text';bbi.placeholder='Bible reading';"
        "bbi.value=r.bible||'';bbi.oninput=function(){r.bible=bbi.value};c.appendChild(bbi);\n"
        "  var n=0;w.items.forEach"
    )
    if OLD_DRAW in html:
        html = html.replace(OLD_DRAW, NEW_DRAW, 1)
        log.append("+ added editable Bible reading field to review sheet")
    elif "bbi.placeholder='Bible reading'" in html:
        log.append("= review sheet Bible field already present")
    else:
        log.append("! drawReview anchor not found (Bible field NOT added)")
    
    return html, log


def main():
    if len(sys.argv) < 2:
        target = Path("index.html")
    else:
        target = Path(sys.argv[1])
    
    if not target.exists():
        print(f"ERROR: {target} not found", file=sys.stderr)
        return 1
    
    original = target.read_text(encoding="utf-8")
    backup = target.with_suffix(target.suffix + f".bak-{datetime.now():%Y%m%d-%H%M%S}")
    shutil.copy2(target, backup)
    print(f"Backup: {backup}")
    
    try:
        patched, log = patch(original)
    except RuntimeError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        print("File unchanged.", file=sys.stderr)
        return 1
    
    if patched == original:
        print("No changes needed (already patched).")
        return 0
    
    target.write_text(patched, encoding="utf-8")
    for line in log:
        print(line)
    print(f"\nPatched {target} ({len(patched) - len(original):+d} chars)")
    return 0


if __name__ == "__main__":
    sys.exit(main())