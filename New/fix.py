#!/usr/bin/env python3
"""
One-shot patch for index.html — combines:

  NAME PICKER (from patch_name_picker.py)
    * Search field at the top of the name picker (live filter, × clear)
    * "Or type a name" merged into search; typed-name button appears
      only when the query has no exact match
    * Dates panels stay open across rebuilds (p.openDates)
    * Scroll position and search caret restored after every rebuild
    * Duet slot defaults to the first EMPTY slot (A filled -> B, and vice versa)

  PRINT (from patch_print_a4.py)
    * @page size:letter -> size:A4
    * .pg padding floor (.15in) so content never sits flush with paper edge
    * 40px gap + 1px rule between the two weeks on a sheet (.wk2+.wk2)
    * break-inside:avoid on .wk2

Run in the same directory as index.html:
    python3 patch_mwb.py
Then hard-refresh (Ctrl+F5 / Cmd+Shift+R).

Writes index.html.bak once, from the original file, before any change.
"""
import sys
import pathlib

MARKERS = [".sbox{", "firstEmptySlot", "size:A4", ".wk2+.wk2"]


def patch(text, anchor, repl, label):
    n = text.count(anchor)
    if n == 0:
        print(f"[FAIL] anchor not found: {label}", file=sys.stderr)
        sys.exit(1)
    if n > 1:
        print(f"[FAIL] anchor matches {n} times (expected 1): {label}", file=sys.stderr)
        sys.exit(1)
    return text.replace(anchor, repl, 1)


def apply_all(text):
    out = text

    # ========================================================================
    # PRINT
    # ========================================================================

    # @page: Letter -> A4
    out = patch(
        out,
        " @page{size:letter;margin:.5in .55in}",
        " @page{size:A4;margin:.5in .55in}",
        "print: @page size",
    )

    # .pg padding floor
    out = patch(
        out,
        " .pg{font:11px/1.25 Tahoma,Verdana,sans-serif;break-after:page;position:relative;min-height:9.7in}",
        " .pg{font:11px/1.25 Tahoma,Verdana,sans-serif;break-after:page;position:relative;"
        "min-height:9.7in;padding:.15in .15in;box-sizing:border-box}",
        "print: .pg padding floor",
    )

    # .wk2 gap + rule on second week only
    out = patch(
        out,
        " .wk2{margin-bottom:22px}.dl{font-weight:bold;font-size:11px}",
        " .wk2{margin-bottom:0;break-inside:avoid}"
        ".wk2+.wk2{margin-top:40px;padding-top:8px;border-top:1px solid #ccc}"
        ".dl{font-weight:bold;font-size:11px}",
        "print: .wk2 gap + rule",
    )

    # ========================================================================
    # NAME PICKER
    # ========================================================================

    # CSS for search box
    css_anchor = (
        ".shh{display:flex;justify-content:space-between;align-items:center;"
        "margin-bottom:8px;gap:8px}.shh b{font-size:15px}.shh button{height:34px;padding:0 12px}"
    )
    css_new = css_anchor + "\n" + (
        ".sbox{position:relative;margin:8px 0}\n"
        ".sbox input{padding-right:38px}\n"
        ".sbox .sclr{position:absolute;right:4px;top:50%;transform:translateY(-50%);"
        "width:30px;height:30px;border-radius:50%;border:none;background:none;"
        "font-size:18px;line-height:1;color:var(--mut);cursor:pointer;"
        "display:none;align-items:center;justify-content:center;padding:0}\n"
        ".sbox input:not(:placeholder-shown)~.sclr{display:inline-flex}"
    )
    out = patch(out, css_anchor, css_new, "picker: .sbox CSS")

    # firstEmptySlot helper
    out = patch(
        out,
        "/* picker sheet */\nfunction drawSheet(){",
        "/* picker sheet */\n"
        "function firstEmptySlot(i,slots){if(slots<2)return 0;if(!i.n[0])return 0;"
        "if(!i.n[1])return 1;return 0}\n"
        "function drawSheet(){",
        "picker: firstEmptySlot helper",
    )

    # row() opens with slot:null
    out = patch(
        out,
        "b.onclick=function(){ui.p={w:w,i:i,slot:0,cat:null,back:false};drawSheet()}",
        "b.onclick=function(){ui.p={w:w,i:i,slot:null,cat:null,back:false};drawSheet()}",
        "picker: row() ui.p",
    )

    # slotBar() opens with slot:null
    out = patch(
        out,
        "else{ui.p={w:w,i:i,slot:half&&i.n[0]?1:0,cat:null,back:false};drawSheet()}",
        "else{ui.p={w:w,i:i,slot:null,cat:null,back:false};drawSheet()}",
        "picker: slotBar() ui.p",
    )

    # scroll capture at top of drawSheet
    out = patch(
        out,
        " var sh=$('sheet'),p=ui.p;sh.innerHTML='';if(!p){sh.className='';return}",
        " var sh=$('sheet'),p=ui.p;var _old=sh.querySelector('.sh'),sc0=_old?_old.scrollTop:0;"
        "sh.innerHTML='';if(!p){sh.className='';return}",
        "picker: drawSheet scroll capture",
    )

    # declare si, default p.slot from firstEmptySlot
    out = patch(
        out,
        " var cat=p.cat;if(!cat&&!p.back&&i.c&&cats.indexOf(i.c)>-1)cat=i.c;if(!cat&&cats.length===1)cat=cats[0];",
        " var cat=p.cat;if(!cat&&!p.back&&i.c&&cats.indexOf(i.c)>-1)cat=i.c;"
        "if(!cat&&cats.length===1)cat=cats[0];var si=null;",
        "picker: si declaration",
    )
    out = patch(
        out,
        "  var slots=cat==='Duet'?2:1;\n  if(cats.length>1)",
        "  var slots=cat==='Duet'?2:1;\n  if(p.slot==null)p.slot=firstEmptySlot(i,slots);\n  if(cats.length>1)",
        "picker: slot default",
    )

    # group chooser / back button reset
    out = patch(
        out,
        "b.onclick=function(){p.cat=c;p.slot=0;p.back=false;drawSheet()}",
        "b.onclick=function(){p.cat=c;p.slot=null;p.back=false;p.fs=null;drawSheet()}",
        "picker: group chooser reset",
    )
    out = patch(
        out,
        "bk.onclick=function(){p.cat=null;p.back=true;drawSheet()}",
        "bk.onclick=function(){p.cat=null;p.back=true;p.fs=null;drawSheet()}",
        "picker: back button reset",
    )

    # body: search + typed-name merge + dates persistence
    body_anchor = (
        "  var us=usage(w),pe=S.people.filter(function(x){return x.cats.indexOf(cat)>-1});\n"
        "  pe.sort(function(a,b){return(us[a.name]||0)-(us[b.name]||0)||a.name.localeCompare(b.name)});\n"
        "  box.appendChild(el('p','note','Number shows uses in these two months.'));\n"
        "  if(!pe.length)box.appendChild(el('p','note','No one is ticked for '+cat+'. Add people in the People tab, or type a name below.'));\n"
        "  pe.forEach(function(x){var why=conflict(w,i,x.name),b=el('button','pn');b.disabled=!!why;\n"
        "   var l=el('span');l.appendChild(document.createTextNode(x.name));if(why){l.appendChild(document.createElement('br'));l.appendChild(el('small','warn',why))}\n"
        "   b.appendChild(l);b.appendChild(el('span','cnt',us[x.name]||0));b.onclick=function(){setName(p,x.name,cat,slots)};\n"
        "   var wr=el('div','pwrap'),pr2=el('div','pw'),db=el('button','dbtn','Dates'),dl2=el('div','pdates');dl2.style.display='none';\n"
        "   db.onclick=function(){var o=dl2.style.display==='none';dl2.style.display=o?'block':'none';db.className='dbtn'+(o?' on':'');dl2.dataset.name=x.name;if(o)fillDates(dl2,x.name)};\n"
        "   pr2.appendChild(b);pr2.appendChild(db);wr.appendChild(pr2);wr.appendChild(dl2);box.appendChild(wr)});\n"
        "  var oi=el('input');oi.placeholder='Or type a name';box.appendChild(oi);\n"
        "  var ob=el('button','big','Use typed name');ob.onclick=function(){if(oi.value.trim())setName(p,oi.value.trim(),cat,slots)};box.appendChild(ob);\n"
        "  var cr=el('button','big','Clear this cell');cr.onclick=function(){i.n=[];i.c='';save();ui.p=null;drawSheet();render()};box.appendChild(cr)}"
    )
    body_new = (
        "  var sbox=el('div','sbox'),si2=el('input');si2.type='text';si2.placeholder='Search name\u2026';si2.value=p.q||'';\n"
        "  si2.oninput=function(){var pos=si2.selectionStart;if(pos==null)pos=si2.value.length;p.q=si2.value;p.fs=pos;drawSheet()};\n"
        "  var clr=el('button','sclr','\u00d7');clr.type='button';clr.title='Clear search';clr.onclick=function(){p.q='';p.fs=0;drawSheet()};\n"
        "  sbox.appendChild(si2);sbox.appendChild(clr);box.appendChild(sbox);si=si2;\n"
        "  var us=usage(w),pe=S.people.filter(function(x){return x.cats.indexOf(cat)>-1});\n"
        "  pe.sort(function(a,b){return(us[a.name]||0)-(us[b.name]||0)||a.name.localeCompare(b.name)});\n"
        "  var q=(p.q||'').trim(),qsk=sk(q);\n"
        "  if(qsk)pe=pe.filter(function(x){return sk(x.name).indexOf(qsk)>-1});\n"
        "  box.appendChild(el('p','note','Number shows uses in these two months.'));\n"
        "  if(!pe.length)box.appendChild(el('p','note',qsk?'No matches for \"'+q+'\".':'No one is ticked for '+cat+'. Add people in the People tab, or type any name.'));\n"
        "  if(!p.openDates)p.openDates={};\n"
        "  pe.forEach(function(x){var why=conflict(w,i,x.name),b=el('button','pn');b.disabled=!!why;\n"
        "   var l=el('span');l.appendChild(document.createTextNode(x.name));if(why){l.appendChild(document.createElement('br'));l.appendChild(el('small','warn',why))}\n"
        "   b.appendChild(l);b.appendChild(el('span','cnt',us[x.name]||0));b.onclick=function(){setName(p,x.name,cat,slots)};\n"
        "   var wr=el('div','pwrap'),pr2=el('div','pw'),db=el('button','dbtn','Dates'),dl2=el('div','pdates');dl2.style.display='none';\n"
        "   if(p.openDates[x.name]){dl2.style.display='block';db.className='dbtn on';dl2.dataset.name=x.name;fillDates(dl2,x.name)}\n"
        "   db.onclick=function(){var o=dl2.style.display==='none';dl2.style.display=o?'block':'none';db.className='dbtn'+(o?' on':'');\n"
        "    if(o){dl2.dataset.name=x.name;fillDates(dl2,x.name);p.openDates[x.name]=1}else delete p.openDates[x.name]};\n"
        "   pr2.appendChild(b);pr2.appendChild(db);wr.appendChild(pr2);wr.appendChild(dl2);box.appendChild(wr)});\n"
        "  if(qsk&&!pe.some(function(x){return x.name.toLowerCase()===q.toLowerCase()})){\n"
        "   var ub=el('button','big','Use \"'+q+'\" as typed name');ub.onclick=function(){setName(p,q,cat,slots)};box.appendChild(ub)}\n"
        "  var cr=el('button','big','Clear this cell');cr.onclick=function(){i.n=[];i.c='';save();ui.p=null;drawSheet();render()};box.appendChild(cr)}"
    )
    out = patch(out, body_anchor, body_new, "picker: search field + typed-name merge")

    # setName: clear search when auto-advancing to partner
    out = patch(
        out,
        "if(slots===2&&p.slot===0&&!n[1]){p.slot=1;drawSheet()}else{ui.p=null;drawSheet()}render()}",
        "if(slots===2&&p.slot===0&&!n[1]){p.slot=1;p.q='';p.fs=null;drawSheet()}"
        "else{ui.p=null;drawSheet()}render()}",
        "picker: setName advance reset",
    )

    # restore scroll + caret at end of drawSheet
    out = patch(
        out,
        " sh.appendChild(box)}",
        " sh.appendChild(box);\n"
        " if(p.fs!=null&&si){var _pos=p.fs,_n=si.value.length;p.fs=null;if(_pos<0||_pos>_n)_pos=_n;"
        "try{si.focus();si.setSelectionRange(_pos,_pos)}catch(e){}}\n"
        " if(sc0)box.scrollTop=sc0}",
        "picker: scroll/caret restore",
    )

    return out


def main():
    p = pathlib.Path("index.html")
    if not p.exists():
        print("[FAIL] index.html is not in the current directory.", file=sys.stderr)
        sys.exit(1)

    src = p.read_text(encoding="utf-8")
    present = [m in src for m in MARKERS]
    if all(present):
        print("Already fully patched — nothing to do.")
        return
    if any(present):
        print(
            "[FAIL] This file looks partially patched.\n"
            "       Restore index.html from your pre-patch backup (or from an earlier index.html.bak)\n"
            "       and run this script against the original. Re-running on a partial patch is unsafe.",
            file=sys.stderr,
        )
        sys.exit(1)

    out = apply_all(src)

    p.with_suffix(".html.bak").write_text(src, encoding="utf-8")
    p.write_text(out, encoding="utf-8")
    print("Patched index.html  (backup: index.html.bak)")
    print("Reload with a hard refresh (Ctrl+F5 / Cmd+Shift+R), then:")
    print("  - Open any assignment sheet to see the search field.")
    print("  - Print to PDF with Margins = Default (A4, background graphics on).")


if __name__ == "__main__":
    main()