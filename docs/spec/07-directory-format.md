# §7 — Directory format

> Part of the [Compunet Client Specification](README.md). Normative unless a passage is
> explicitly marked non-normative.
>
> Authority & triangulation: the server directory builder (`_make_page_response` in
> `server/compunet_server.py`), the C64 terminal parser (`docs/PROTOCOL.md`, L_A5F3), and
> the Amiga parser (`client/amiga/src/directory_parse.c`, verified against the original
> disassembly). All three agree on the six-part layout and the entry field positions.

Directories are how a user navigates Compunet: a list of entries (sub-directories, text
pages, programs, links) drawn inside a fixed template. The server sends only the **variable
data** — the entries and a few text lines — as a six-part stream; the surrounding chrome
(the box, column layout, title area) is a **client-side template** (§7.5) that the server
does not transmit. A Tier 1 client **MUST** implement this section.

## 7.1 When a directory response is produced

A directory response (type **DIR**, §4.3) is the reply to `P` (show current directory), and
to `D` / `B` / `L` / `M` / `I` / `C` when they land on a directory rather than a frame
(§4.4). It is delivered as a DAT stream + EOS (§2, §4.2).

## 7.2 The six-part stream

The response body is six consecutive parts. Each part has its own terminator; a leading
`$00` means "this part is empty, skip it". The parts are read in order from the stream.

| Part | Contents | Terminator / empty rule |
|---|---|---|
| **1 — Frame header** | An optional PETSCII header frame (§5–6, no 4-byte frame header — just body bytes) drawn above the list | ends at `$00`. A leading `$00` = no header → the client draws its **built-in template** (§7.5) |
| **2 — Footer text** | Two `CR`-terminated lines shown near the bottom (breadcrumb / advert) | two lines each ended by `$0D`; a leading `$00` = none |
| **3 — Field definitions** | Zero or more F-key shortcuts: `id` `=` `value` `$0D`, where `id` is 1–6 | terminated by `$00` |
| **4 — Path line** | The directory path / breadcrumb line(s) shown above the entries | terminated by `$00` |
| **5 — Column headers** | The column titles, comma-separated, `CR`-terminated, then a `$00` separator byte | one line ended by `$0D`, then a `$00` |
| **6 — Entries** | The directory entries, one per line (§7.3) | the stream ends (EOS) after the last entry's `$0D` |

**The Part-5 column headers are response-specific — read them, do not hard-code them.** The
top directory sends five: `PRICE`, `AUTHOR`, `VOTE/NUM`, `UPLDDATE`, `LIFE`. But other DIR-type
responses send a **different set** — e.g. `MAIL` (`M`) sends three: `SENDER`, `DATE`, `STATUS`.
A client **MUST** take the column names (and their count) from each response's own Part 5 and
label the entry columns from that, cycling among whichever columns that response defines. It
**MUST NOT** assume the five top-directory names apply everywhere.

**Encoding: the six-part stream's text is unshifted ASCII, but may carry inline control
codes.** Unlike the raw MOTD (§3.4), which is sent in PETSCII lowercase mode (`A`–`Z` as
`$C1`–`$DA`), the directory stream's text fields — titles, breadcrumb, footer, column headers —
use **plain, unshifted ASCII** for their letters (`"JUNGLE"`, `"WHAT'S NEW?"`, `"T+"`), and a
client **MUST NOT** apply the MOTD's PETSCII shift to them. The stream is **not** pure ASCII,
however: the server may embed **inline PETSCII control codes** — notably a `$1C` (red) colour
control in **Part 4** to draw the red `MAIL` unread-mail marker (§8.2), e.g.
`…600 JUNGLE           \x1cMAIL`. A client **MUST** preserve and act on such control bytes
(here, switch to red for the trailing `MAIL`) rather than assuming the field is letters only.
(Part 1, the header *frame*, is fully frame content, §6 — decoded with all its control codes
and RLE.)

## 7.3 Directory entries (Part 6)

Each entry is a single line: a fixed-layout **first field** naming the entry, then five
comma-separated **column fields**, then `$0D`:

```
<first field> , <PRICE> , <AUTHOR> , <VOTE/NUM> , <UPLDDATE> , <LIFE> $0D
```

The **first field** is a fixed 27-character layout:

| Chars | Content |
|---|---|
| 0–5 (6) | page number, right-justified, space-padded |
| 6 (1) | space |
| 7–23 (17) | title, left-justified, space-padded |
| 24–26 (3) | type indicator (§7.4), left-justified — so the type begins at **screen column 25** |

The five column fields (each ≤ 8 characters) carry the data under the Part-5 headers; any
of them may be empty (just the comma). `VOTE/NUM` is score, `/`, then vote count; `UPLDDATE`
is `D-MMM`; `LIFE` is the remaining life in days.

> **Dual parsing constraint (normative — a real cross-client requirement).** The two
> reference clients parse Part 6 differently, and an entry **MUST** satisfy both:
>
> - The **C64** parser reads the first field up to the comma (`$2C`) and pads it to 30
>   characters — it is **comma-delimited**.
> - The **Amiga** parser reads **fixed-width** columns from the first field (6 + 16 + 5
>   characters) and has **no end-of-stream guard**.
>
> Therefore a producer **MUST** emit the exact 27-character fixed layout above **and**
> terminate every field with its comma / `$0D`, and **MUST** end the stream cleanly right
> after a complete entry's `$0D`. An entry that is short, or a stream that ends mid-entry,
> will hang the Amiga parser (it spins with no EOF guard) and misalign the C64 parser. A
> consumer at Tier 1 **MUST** tolerate the full fixed-width layout.

A directory with no entries **MUST** still be represented by one placeholder entry in the
full fixed layout (e.g. an `(EMPTY)` line), for the same reason — an empty Part 6 hangs the
Amiga parser and leaves the C64 entry count uninitialised.

## 7.4 Entry types

The type indicator (first-field chars 24–26, from screen column 25) is **compound**, not a
single symbol. It is a **base type**, optionally followed by a **size** and/or a
**sub-directory marker**, in this order:

```
<base> [<size>] [+]
```

- **base** — one of `T`, `D`, `P`, `PP`, `S`, `L` (note `PP` is two letters). This letter
  determines what happens when the entry is selected (below).
- **size** — optional decimal digits: for programs the size in K, for text pages the page
  count. Informational only.
- **`+`** — optional marker meaning the entry **also has a sub-directory** beneath it.

Real examples seen on the wire: `T+`, `D+`, `T2`, `P18`, `P5`, `T2+` (= text, 2 pages, has a
sub-directory). A client **MUST** parse the type as this grammar and dispatch on the **base**
letter alone:

| Base | Meaning | Selecting it |
|---|---|---|
| `T` | Text page(s) | show the frame(s) (§6) |
| `D` | Directory (no content of its own) | enter it (new directory response) |
| `P` | Program / telesoftware | download (§8.3) |
| `PP` | Protected program | download; original required the modem as a dongle |
| `S` | Sequential file (word-processor format) | download / view |
| `L` | Link | activate the link subsystem (§8.5 — Partyline on the modern server) |

The `+` marker is **independent of the base** and does **not** change the select action: a
`T+` entry, when selected, shows its text frame(s) exactly like a bare `T` — it does **not**
enter the sub-directory. The `+` sub-directory is a *separate* listing reached by navigating
into the entry (a later `D` while viewing it) or by `GOTO` (§4.4) to the entry's keyword or
number, not by paging its frames (§6.5). A client **MUST** read the type from screen column
25 and dispatch on the base letter; it **MUST NOT** treat `+` as a directory-vs-frame
selector.

## 7.5 The built-in directory template

When Part 1 is empty (`$00`), the client draws the directory using a **built-in template** —
the fixed visual layout the server never sends. This template is what makes a directory
*look* like Compunet, so a faithful client **MUST** reproduce it. It defines:

- the bordered content box and title area (`  1 *** COMPUNET ***`);
- the **path line** at row 7 (Part 4);
- the **entry list** below it — up to **11 entries** per page (§7.6), each showing the
  page number, title, type (at column 25), and one selectable column value;
- the **footer** lines at row 22 (Part 2).

The reference clients hold this template as embedded data: the C64 terminal stores it as a
PETSCII frame at address `$BCE1` and renders it directly; the Amiga reproduces the same
layout through its native list/gadget UI (`directory_parse.c` builds up to 8 clickable link
gadgets plus the row table). Because the template is a required client asset that the
protocol does not carry, the canonical C64 PETSCII template is reproduced verbatim in
[Appendix §A](99-appendices.md) so a new client can render an authentic directory screen
from this specification alone.

*(Non-normative: a directory MAY override the template by supplying its own Part-1 header
frame — this is how special pages get custom graphics above the list.)*

## 7.6 Paging

A directory shows at most **11 entries** at a time. If more entries exist, the client pages
through them:

- Entry indices in `D` are **0-based relative to the current response** (not absolute across
  pages). To page forward, a client sends `D` + the index **one past the last visible entry**
  — i.e. the count of entries in the current listing (if 11 are shown, send `D 11`). The
  server advances its offset by 11 and returns the next page.
- If there is no next page, the server returns a directory whose only entry is the `(EMPTY)`
  placeholder (§7.3), which a client can treat as "no more entries".
- **A page that has more pages after it signals so with a trailing `MORE` entry.** When a
  listing is truncated to 11 because more entries follow, its **last row is a synthetic
  pagination entry**: an empty page number, the title `MORE        >>>>`, and an **empty type**
  field. This row is *not* real content and does **not** fit the §7.4 type grammar. A client
  **SHOULD** treat it as a "there is more" indicator; selecting it (or sending `D` + the entry
  count) pages forward — both reach the next page.
- A client **MUST** support paging and **MUST NOT** assume a directory fits in one response.

*(Non-normative: the modern server reloads its content tree on each directory request, so
listings reflect live content changes without a reconnect.)*

## 7.7 Screen composition

The six parts (§7.2) and the template (§7.5) are composed onto the 40×24 grid to reproduce the
**canonical C64 directory screen** — the reference look a conforming client should match. The
template provides the bordered box, the **vertical divider** between the entry list and the
right-hand column, and the column-cycle indicator; the parts overlay onto it:

| Rows | Content | Source |
|---|---|---|
| 0–5 | Header region — Part 1 overlaid if present, else the template's own top | Part 1 |
| 7 | Breadcrumb line 1, aligned with the entry columns (left); **selected column header** e.g. `PRICE` (right column) | Part 4 / Part 5 |
| 8 | Breadcrumb line 2, e.g. `100 WELCOME`, same alignment (left) | Part 4 |
| 10–20 | The entry list — up to 11 entries, one per row (see below) | Part 6 (+ selected Part 5 column) |
| 22–23 | Footer / advert — Part 2's two lines, **centred** on their rows | Part 2 |

**Breadcrumb alignment.** Part 4's two lines are **not** drawn at column 1. They share the
entry columns: the leading **page number is right-justified** in the same left column the entry
page numbers use, and the title follows. Part 4 already contains the padding spaces
(`     1 *** COMPUNET ***`, `   100 WELCOME`), so a client renders each Part-4 line from the
entry list's base column and the alignment falls out (the shorter `1` ends up more indented
than `100`).

The **built-in template (§7.5) is always drawn first as the base chrome** — the bordered box,
column dividers, and the column-cycle indicator. The template intentionally begins with six
blank rows (its body opens with a six-fold `CR` run), leaving the **header region (rows 0–5)**
empty. A client then **overlays Part 1 there when it is non-empty** (e.g. the COMPUNET logo);
when Part 1 is empty (`$00`), rows 0–5 simply remain as the template left them. The path,
entries, and footer overlay on top as below. A client that draws only the template and skips
Part 1 will render every directory without its header graphic.

Within the entry rows, each entry occupies **one** row. A client **MUST NOT** render the whole
comma-separated Part-6 line — it is wider than 40 columns and would overflow. Each entry row
shows:

1. the **page number** — right-justified in the left page-number column — **only for the
   currently-selected entry**. Non-selected entries leave that column blank and show just the
   title. (So as the selection moves, the page number appears on whichever row is selected.)
2. the **title**, then the **type** (§7.3), with the type at **screen column 25**;
3. in the **right column** (past the vertical divider), the value of the currently-selected
   Part-5 column (§*The selected column header*, below) for that entry.

The other Part-6 column fields are **not** displayed until the user cycles to that column.

### Directory colours (client-applied)

Parts 2, 4, and 6 (footer, breadcrumb, entries) are mostly plain text and carry **no colour
codes of their own** (aside from the occasional inline control such as the red `MAIL` marker,
§7.2); only Part 1 (the header frame) is fully colour-coded. So the **client colours the list
itself**, and a conforming client **MUST** use this scheme so the directory looks right:

- The **breadcrumb** (Part 4) and the **footer / advert** (Part 2) are drawn in **blue**
  (colour index 6).
- Each entry has a **positional** colour, independent of selection: the **first entry in the
  list is always red** (index 2); **every other entry is blue** (index 6).

**The selection highlight is drawn by the client — the server sends nothing about it.**
Selection is entirely client-local (§4.5): there is no wire field for "which row is
highlighted", so the client draws the highlight itself. It is a **bar spanning the full row
width** — across both the entry columns **and** the right-hand value column — in **the entry's
own positional colour** (a **red** bar for the first entry, a **blue** bar for the others),
with the **text drawn in white** (index 1) on top. This "colour bar + white text" cannot be
expressed with a single PETSCII cell attribute, which is another reason it is client chrome,
not wire content. A client **MUST** draw the highlight this way (not a single fixed colour),
and the red-first / blue-rest entry colouring is **required** either way — it is part of the
authored Compunet look.

### The selected column header

The header of the currently-selected column (the Part-5 name — `PRICE`, `AUTHOR`, …) **MUST**
be displayed so the user can see which column the right-hand values belong to. It sits in the
**right-hand column, at row 7** (level with breadcrumb line 1, the top of the box), and is
drawn in blue. A client that shows the column *values* but omits this header leaves them
unlabelled.

A client **MUST** reproduce this canonical C64 layout so that content authored for Compunet —
which assumes this geometry — lands correctly.
