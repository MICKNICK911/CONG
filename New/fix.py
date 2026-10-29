
#!/usr/bin/env python3
"""
add_ai_prompt.py - add the "AI Prompt: Convert workbook PDF to JSON"
section to index.html.

Usage:
  python3 add_ai_prompt.py [index.html]
"""
import sys
from pathlib import Path
from datetime import datetime

# ---------------------------------------------------------------------------
# Prompt text (raw triple-quoted: no escaping needed)
# ---------------------------------------------------------------------------
PROMPT = r'''You are converting a JW Meeting Workbook PDF into a JSON file for a
scheduling web app. The PDF is attached. Read it carefully before
producing any output.

==================== STEP 0 — CONFIRM YOU CAN READ IT ====================

Before doing anything else, reply with a short list in this exact form
and nothing else:

  Week 1: <Month> <D1>-<D2>   (e.g. "January 4-10")
  Week 2: ...
  ...
  Total: N weeks
  Bible readings found: yes / no
  Songs found: yes / no

If you cannot read the PDF text layer, say "Cannot extract text — please
upload a text version" and STOP.

Do not produce the JSON yet. Wait for my "go ahead" reply.

==================== STEP 1 — OUTPUT FORMAT ====================

After I say "go ahead", reply with ONE fenced code block:

```json
{ ... }
```

No prose before or after. No explanations. No markdown around it.
The block must be valid JSON (paste-able directly into the app).

==================== STEP 2 — TOP-LEVEL SCHEMA ====================

The object has exactly these four keys, in this order:

"settings"   — object (see Step 3)
"people"     — array  (see Step 3)
"lastBackup" — "" (empty string)
"weeks"      — array  (see Step 4)

Do not add any other top-level keys. Do not rename them. Do not
reorder them. Order inside each object is also fixed — see examples.

==================== STEP 3 — SETTINGS AND PEOPLE ====================

If I pasted my current "settings" and "people" blocks at the top of my
message, copy them verbatim into the output.

If I did NOT paste them, use:

"settings": {
"cong": "",
"start": "19:00",
"adj": true,
"conc": true,
"lang": "en"
},

"people": [],

(Note: importing JSON in the app REPLACES settings and people. So if I
pasted my blocks, you MUST copy them — otherwise my congregation name
and people list would be lost.)

==================== STEP 4 — WEEK DATES ====================

Every week object has these fields IN THIS ORDER:

id, mon, cv, co, bible, songs, items

· "id":   "w" + mon       →  "w2027-01-04"
· "mon":  the Monday of that week, "YYYY-MM-DD"
· "cv":   true if the page is a Convention Week, else false
· "co":   true if the page is a Circuit Overseer visit week, else false
· "bible": the Bible reading printed at the TOP of the week page,
  uppercase, e.g. "EZEKIEL 11-12". If absent, use "".
· "songs": array of exactly 3 strings (opening, middle, concluding).
  If a song is missing, use "".
· "items": array (see Step 5)

How to derive the dates:

· The cover shows "JANUARY-FEBRUARY 2027" (or similar).
· Find the FIRST MONDAY of the first month of the cover.
· Week 1 = that Monday. Week 2 = +7 days. Week 3 = +7 more. Etc.
· Verify against the printed dates on the pages if visible.

For Jan-Feb 2027 the first Monday is 2027-01-04.
For Mar-Apr 2027 the first Monday is 2027-03-01.
For May-Jun 2027 the first Monday is 2027-05-03.
For Jul-Aug 2027 the first Monday is 2027-07-05.
For Sep-Oct 2027 the first Monday is 2027-09-06.
For Nov-Dec 2027 the first Monday is 2027-11-01.

==================== STEP 5 — ITEMS ====================

Every week has these items in this order:

1. Chairman            ty:"ch"  m:null   sec:0  t:"Chairman"
2. Opening Prayer      ty:"pr"  m:null   sec:0  t:"Opening Prayer"
3. Closing Prayer      ty:"pr"  m:null   sec:0  t:"Closing Prayer"
4. Treasures part 1    ty:"t1"  m:<N>    sec:1  t:<actual title>
5. Spiritual Gems      ty:"t2"  m:10     sec:1  t:"Spiritual Gems"
6. Bible Reading       ty:"t3"  m:4      sec:1  t:"Bible Reading"
   7-10. Ministry parts   ty:<see> m:<N>    sec:2  t:<actual title>
   ...   Living part      ty:"liv" m:<N>    sec:3  t:<actual title>
   or Local Needs      ty:"ln"  m:<N>    sec:3  t:"Local Needs"
   ...
   Congregation
   Bible Study    ty:"cbs" m:30     sec:3  t:"Congregation Bible Study"
   Reader           ty:"rd"  m:null   sec:3  t:"Reader"

Number of Ministry parts (7-10 above) varies by week:

· 2 parts: following-up pair
· 3 parts: starting/following/explaining
· 4 parts: "Making Disciples" series
  Use whatever the PDF prints. Keep them in printed order.

Ministry part type mapping (printed title → ty):
"Starting a Conversation"     → "sc"
"Following Up"                → "fu"
"Making Disciples"            → "md"
"Explaining Your Beliefs"     → "eb"
"Talk"                        → "tk"
"What Would You Say?"         → "ww"

Living part mapping:
"Local Needs"                 → "ln"
Anything else in Living       → "liv"
"Annual Service Report"       → "liv"
"Memorial Campaign ..."       → "liv"
"Convention/Assembly" notices → "liv"

Minutes ("m"):

· Parse from "(N min.)" or "(Simma N)" after the title.
· For range like "(3 or 4 min.)" use the larger number.
· Use null ONLY for ch, pr, rd.
· Use integers (no quotes) for everything else.

Section (sec):

· ch, pr                  → 0
· t1, t2, t3              → 1
· sc, fu, md, eb, tk, ww  → 2
· liv, ln, cbs, rd        → 3

Titles ("t"):

· For fixed parts (ch, pr, t2, t3, cbs, rd, ln) use the exact
  strings shown in the list above.
· For t1, sc, fu, md, eb, tk, ww, liv use the printed title from
  the PDF, WITHOUT the "(N min.)" suffix.
· Preserve curly quotes " " as printed.
· If the title is truncated on the page with "…", keep it.
· If the PDF is Twi, keep Twi titles verbatim.

==================== STEP 6 — n AND c ====================

THIS IS CRITICAL. READ TWICE.

Every item has exactly these two assignment fields:

"n": []          ← ALWAYS an empty array. NEVER put a name in it.
"c": "<value>"   ← fill using the table below.

The "c" value depends only on "ty":

ty    key template       fill "c" with
────────────────────────────────────────
ch    Eld                "Eld"
pr    Pub-Ms-Eld         "Pub"
t1    Eld-Ms             "Eld"
t2    Eld-Ms             "Eld"
t3    Pub                "Pub"
sc    Duet               "Duet"
fu    Duet               "Duet"
md    Duet               "Duet"
eb    Duet-Pub           "Duet"
tk    Pub                "Pub"
ww    Eld-Ms             "Eld"
liv   Eld-Ms             "Eld"
ln    LN                 ""
cbs   Eld                "Eld"
rd    Eld-Ms             ""

Two special cases override the table:

A) Convention Week (cv: true):
EVERY item gets  "n": [],  "c": ""
(no assignments at all)

B) Circuit Overseer Week (co: true):
The cbs item gets  "c": "C.O Talk"  (with "n": [])
Everything else follows the table.

Do NOT invent names. Do NOT try to balance or suggest people.
Do NOT add a "key" field. "c" IS the key per your instruction.

==================== STEP 7 — WORKED EXAMPLE ====================

Here is exactly what week 1 (2027-01-04) must look like. Use it as the
template for object key order and formatting:

{
"id": "w2027-01-04",
"mon": "2027-01-04",
"cv": false,
"co": false,
"bible": "EZEKIEL 11-12",
"songs": ["83", "2", "164"],
"items": [
{ "ty": "ch",  "t": "Chairman",                              "m": null, "sec": 0, "n": [], "c": "Eld"  },
{ "ty": "pr",  "t": "Opening Prayer",                        "m": null, "sec": 0, "n": [], "c": "Pub"  },
{ "ty": "pr",  "t": "Closing Prayer",                        "m": null, "sec": 0, "n": [], "c": "Pub"  },
{ "ty": "t1",  "t": "“Perhaps They Will Take Notice”",       "m": 10,   "sec": 1, "n": [], "c": "Eld"  },
{ "ty": "t2",  "t": "Spiritual Gems",                        "m": 10,   "sec": 1, "n": [], "c": "Eld"  },
{ "ty": "t3",  "t": "Bible Reading",                         "m": 4,    "sec": 1, "n": [], "c": "Pub"  },
{ "ty": "fu",  "t": "Following Up",                          "m": 3,    "sec": 2, "n": [], "c": "Duet" },
{ "ty": "fu",  "t": "Following Up",                          "m": 4,    "sec": 2, "n": [], "c": "Duet" },
{ "ty": "ww",  "t": "What Would You Say?",                   "m": 5,    "sec": 2, "n": [], "c": "Eld"  },
{ "ty": "ln",  "t": "Local Needs",                           "m": 15,   "sec": 3, "n": [], "c": ""     },
{ "ty": "cbs", "t": "Congregation Bible Study",              "m": 30,   "sec": 3, "n": [], "c": "Eld"  },
{ "ty": "rd",  "t": "Reader",                                "m": null, "sec": 3, "n": [], "c": ""     }
]
}

Note the key order inside each item: ty, t, m, sec, n, c.
Use that order EXACTLY, with the same spacing shown above.

==================== STEP 8 — WHAT NOT TO DO ====================

DO NOT:

· Put any name in any "n" field. Every "n" is [].
· Add extra fields (no "key", "assigned", "status", "notes", "title_extra").
· Remove any of the six required fields (ty, t, m, sec, n, c).
· Use 0 for m where null is required (ch, pr, rd).
· Use "" for m where a number is expected.
· Reorder top-level keys or item keys.
· Merge weeks.
· Skip weeks that "look like" convention weeks — still emit them with
  cv: true and all c: "".
· Add weeks that aren't in the PDF.
· Format as pretty-printed JSON spanning multiple pages; the app
  requires a single valid object (2-space indent is fine).
· Wrap the JSON block in commentary.

==================== STEP 9 — SELF-VERIFICATION ====================

Before outputting, silently check each of these:

[ ] Number of "weeks" equals the number confirmed in Step 0.
[ ] Every "mon" is a Monday (getUTCDay() === 1).
[ ] Every week has at least 12 items, at most 15.
[ ] Every item has exactly six fields in order: ty, t, m, sec, n, c.
[ ] Every "n" equals [].
[ ] Every "c" is one of: "", "Eld", "Ms", "Pub", "Duet", "LN", "C.O Talk".
[ ] Every "cv: true" week has every "c" equal to "".
[ ] Every "co: true" week's cbs item has "c": "C.O Talk".
[ ] "bible" is uppercase or empty.
[ ] "songs" has exactly 3 elements.
[ ] The whole thing parses as JSON.

If any check fails, fix it before outputting. Never output an invalid
object.

==================== STEP 10 — RESPOND ====================

Now produce the JSON code block as specified in Step 1.

After the code block, on a new line, add exactly one line:

Weeks: N · Bible readings: M/N · Songs: K/N

where N is total weeks, M is weeks whose "bible" is non-empty, K is
weeks whose "songs" has 3 non-empty entries. This is for me to verify
the AI didn't silently drop data.'''

SCRIPT_BLOCK = (
'<script type="text/plain" id="aiPrompt">\n'
+ PROMPT
+ '\n</script>\n'
)

AI_FN = r'''
function aiPromptSection(){
var det=el('details');
det.style.cssText='margin:0 0 12px;border:1px solid var(--bd);border-radius:10px;background:var(--card);overflow:hidden';
var sum=el('summary');
sum.textContent='AI Prompt: Convert workbook PDF to JSON';
sum.style.cssText='padding:12px 14px;cursor:pointer;font-weight:600;font-size:14px;background:var(--sec)';
det.appendChild(sum);
var inner=el('div');
inner.style.cssText='padding:12px 14px';
inner.appendChild(el('p','note','Use this when PDF import fails or misses data. It tells any AI (Claude, ChatGPT, Gemini) how to convert the workbook PDF into the exact JSON format this app imports.'));
var steps=el('ol');
steps.style.cssText='margin:0 0 10px;padding-left:20px;font-size:12px;line-height:1.6';
['Open an AI chat that can read PDFs (e.g. Claude.ai).',
'Attach the workbook PDF.',
'Copy the prompt below and paste it as your message.',
'Wait for the AI to list the weeks, then reply "go ahead".',
'Save the JSON block it returns as mwb-schedule-YYYY.json.',
'Settings → Backup → Import JSON → pick that file.'
].forEach(function(s){steps.appendChild(el('li','',s))});
inner.appendChild(steps);
var ta=el('textarea','cb');
var tpl=document.getElementById('aiPrompt');
ta.value=tpl?tpl.textContent.trim():'';
ta.readOnly=true;
ta.style.height='120px';
ta.style.fontSize='10px';
ta.spellcheck=false;
inner.appendChild(ta);
var row=el('div');
row.style.cssText='display:flex;gap:8px;margin-top:8px';
var cp=el('button','big','Copy prompt');
cp.style.flex='1';
cp.onclick=function(){
copyText(ta.value).then(function(ok){
if(ok){cp.textContent='Copied \u2713';setTimeout(function(){cp.textContent='Copy prompt'},2000)}
else{ta.focus();ta.select();alert('Select all and copy manually.')}
})
};
var dl=el('button','big','Download .txt');
dl.style.flex='1';
dl.onclick=function(){
var u=URL.createObjectURL(new Blob([ta.value],{type:'text/plain'}));
var a=document.createElement('a');
a.href=u;
a.download='workbook-to-json-prompt.txt';
a.click();
setTimeout(function(){URL.revokeObjectURL(u)},2000)
};
row.appendChild(cp);
row.appendChild(dl);
inner.appendChild(row);
det.appendChild(inner);
return det;
}
'''

(label, anchor, replacement, idempotency_marker)

All snippets are raw triple-quoted so no escaping is required.

PATCHES = [
(
"insert aiPrompt script tag",
r'''<script src="libs/jszip.min.js"></script>''',
SCRIPT_BLOCK + '<script src="libs/jszip.min.js"></script>',
'id="aiPrompt"',
),
(
"insert aiPromptSection() function",
r'''function plan(){var m=monOf(ui.cd),n=Math.max(1,parseInt(ui.cn)||1),o=[];''',
AI_FN + "\n" + r'''function plan(){var m=monOf(ui.cd),n=Math.max(1,parseInt(ui.cn)||1),o=[];''',
'function aiPromptSection(){',
),
(
"hook aiPromptSection() into createView",
r'''var pb=el('button','big','Import from workbook PDF');pb.style.marginBottom='12px';pb.onclick=function(){pickPdf(pb)};box.appendChild(pb);''',
r'''var pb=el('button','big','Import from workbook PDF');pb.style.marginBottom='12px';pb.onclick=function(){pickPdf(pb)};box.appendChild(pb);box.appendChild(aiPromptSection());''',
'box.appendChild(aiPromptSection());',
),
(
"nudge user when no weeks detected",
r'''if(!R.weeks.length){alert('No week headings such as "NOVEMBER 2-8" were found.');return}''',
r'''if(!R.weeks.length){alert('No week headings found in this PDF. Try the AI Prompt in the Create tab to convert it to JSON manually.');return}''',
'No week headings found in this PDF',
),
(
"nudge user when PDF unreadable",
r'''alert('Could not read the PDF. Check that libs/pdf.min.mjs and libs/pdf.worker.min.mjs are next to index.html and that the app is opened from Netlify, not from a file. ('+(e&&e.message||e)+')')''',
r'''alert('Could not read the PDF. Check that libs/pdf.min.mjs and libs/pdf.worker.min.mjs are next to index.html and that the app is opened from Netlify, not from a file. If it keeps failing, use the AI Prompt in the Create tab. ('+(e&&e.message||e)+')')''',
'use the AI Prompt in the Create tab',
),
]

def patch(html):
log = []
for label, old, new, marker in PATCHES:
if marker in html:
log.append(f"= {label}: already present")
elif old in html:
html = html.replace(old, new, 1)
log.append(f"+ {label}")
else:
log.append(f"! {label}: anchor not found (skipped)")
return html, log

def main():
target = Path(sys.argv[1] if len(sys.argv) > 1 else "index.html")
if not target.exists():
print(f"ERROR: {target} not found", file=sys.stderr)
return 1

if name == "main":
sys.exit(main())
