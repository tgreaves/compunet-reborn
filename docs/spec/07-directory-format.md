# §7 — Directory format

**Layer — Binding-A wire format** (§1.8). The six-part directory stream; a modern binding delivers the same listing as a JSON entry list instead (see [`api/README.md`](api/README.md)).

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

A directory response (type **DIR**, §4.3) is the reply to **DIR** (`P`+index, enter an entry as
a directory), **FINISH** (`P` no-arg, return from a frame), `B` (back), `L` (GOTO), `M` (mail),
`C` (UCAT), and to `D` no-arg (MORE) once it pages past the last frame (§4.4). It is delivered
as a DAT stream + EOS (§2, §4.2).

## 7.2 The six-part stream

The response body is six consecutive parts, read in order from the stream. Most parts end at a
`$00`; where a part is empty, its `$00` follows immediately. **Part 2 is the exception — it has
no `$00` terminator of its own** (see the boundary note after the table).

| Part | Contents | Terminator / empty rule |
|---|---|---|
| **1 — Frame header** | An optional PETSCII header frame (§5–6, no 4-byte frame header — just body bytes) drawn above the list | ends at `$00`. A leading `$00` = no header → the client draws its **built-in template** (§7.5) |
| **2 — Footer text** | The advert / footer, shown near the bottom — **always two** `$0D`-terminated lines (two *empty* `$0D` lines when there is no advert) | **two `$0D`-terminated lines, always.** Part 2 has **no `$00` terminator of its own** — see the note below |
| **3 — Field definitions** | Zero or more F-key shortcuts: `id` `=` `value` `$0D`, where `id` is 1–6 | terminated by `$00` (this is the first `$00` after the two footer lines) |
| **4 — Path line(s)** | The directory breadcrumb — **one or two** `$0D`-separated lines shown above the entries, and may carry an inline `$1C MAIL` marker (§8.2) | terminated by `$00` (the `$0D`-separated lines live **inside** this one part) |
| **5 — Column headers** | The column titles, comma-separated, `CR`-terminated, then a `$00` separator byte | one line ended by `$0D`, then a `$00` |
| **6 — Entries** | The directory entries, one per line (§7.3) | the stream ends (EOS) after the last entry's `$0D` |

**Part 2 → Part 3 boundary — do not consume a `$00` after the footer (normative).** The footer
is exactly **two `$0D`-terminated lines** (empty lines if there is no advert); Part 2 does *not*
emit a `$00`. The very next `$00` in the stream is **Part 3's** terminator (its empty
field-definitions list). A parser that reads the two footer lines and then also consumes a
trailing `$00` as "Part 2's terminator" swallows Part 3's terminator and shifts **every later
part by one byte** — the entries spill into the path line. Read exactly two `$0D` lines for
Part 2, then let Part 3's loop consume the `$00`.

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
of them may be empty (just the comma). Each is **justified by the server** so it lands correctly
in the 8-character right-hand pane — a client renders the field **verbatim** from the pane's base
column, it does **not** re-justify. The exact formatting (from the server's Part-6 builder):

| Column | Header (Part 5) | Value formatting |
|---|---|---|
| PRICE | `" PRICE"` (leading space) | `" " + price.rjust(6)` (e.g. `"   5.00"`); empty if free/purchased |
| AUTHOR | `" AUTHOR"` (leading space) | the author, plain, truncated to 8 |
| VOTE/NUM | `"VOTE/NUM"` | `score.rjust(4) + "/" + count`, truncated to 8; **`"    -"`** when unvoted |
| UPLDDATE | `"UPLDDATE"` | `"D-MMM".rjust(7)` (e.g. `"  5-JAN"`); empty if none |
| LIFE | `" LIFE"` (leading space) | `"  " + life.rjust(3)` (e.g. `"   99"`); empty if none |

**⚠ Load-bearing.** The leading spaces on the `PRICE`/`AUTHOR`/`LIFE` **headers**, and the right-justification of the
**values**, are the positioning — they are what place the content one column in from the pane
edge and align the digits. A client that strips them or re-justifies will mis-place the column.

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

| Base | Meaning | SHOW action (`D`+index) |
|---|---|---|
| `T` | Text page(s) | show the frame(s) (§6) |
| `D` | Directory (no content of its own) | **nothing happens** — see below |
| `P` | Program / telesoftware | download (§8.3) |
| `PP` | Protected program | download; original required the modem as a dongle |
| `S` | Sequential file (word-processor format) | download / view |
| `L` | Link | activate the link subsystem (§8.5 — Partyline on the modern server) |

**⚠ SHOW on an entry with no frames does nothing (normative).** `SHOW` reads an entry's text
frames; if the entry has none — which is the normal case for a `D` (directory-only) entry — then
there is nothing to read and **SHOW is inert**: the screen does not change and the user stays in
the listing. It **MUST NOT** fall back to entering the sub-directory, because that would make
`SHOW` and `DIR` the same command on exactly the entries where the spec is at pains to keep them
apart (§4.7). Entering is `DIR`, and only `DIR`.

> **Known server deviation.** The Reborn server currently *does* fall back to entering the
> sub-directory when a selected entry has no frames (`_cmd_dir`, the `has_subdir()` branch), so
> `SHOW` on a `D+` entry navigates instead of doing nothing. The behaviour above is correct and
> the server should be corrected to match; until then a client may observe the fallback.

The table above is the **SHOW** action (`D`+index, §4.7) — reading an entry. **Entering** an
entry *as a directory* is a separate command, **DIR** (`P`+index): DIR works on **any** entry,
not just base `D`. On a `T+` the two differ — SHOW reads its text frame(s) while DIR descends
into its sub-directory — so a client **MUST** offer both and **MUST NOT** collapse them.

The `+` marker is **independent of the base**: it means the entry **already has** a
sub-directory beneath it. It does **not** change the SHOW action (a `T+` shows frames exactly
like a bare `T`) and it is **not** a directory-vs-frame selector. Crucially, DIR is **not**
gated on `+`: a user **MAY** issue DIR on an entry whose type is *not* `D` and has *no* `+`, on
which the **server** opens a fresh **empty** sub-directory under it. That directory is *latent*
— it becomes real only once content is uploaded into it (§8.3.2). This is the mechanism by which
the directory hierarchy is built: the client issues DIR, the server creates the directory. A
client **MUST** read the type from screen column 25, dispatch
SHOW on the base letter, and allow DIR regardless of base or `+`.

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
through them.

> **Two different limits both happen to be 11 — do not conflate them.**
> - **Here, 11 is a *page size*.** A listing may contain **any number** of entries and is served
>   11 at a time; mail (§8.2) and UCAT (§8.6) routinely exceed one page. A client **MUST**
>   implement paging and **MUST NOT** assume a listing fits in one response.
> - **In §8.3.2, 11 is a *capacity limit* on user uploads*** — the server refuses to add a
>   **12th** child to a directory via upload. That is a write-side rule; it does not mean a
>   directory can never *contain* more than 11 (system-authored and generated listings do).

The paging mechanics:

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
| 7 | Breadcrumb line 1, aligned with the entry columns (left) | Part 4 |
| 8 | Breadcrumb line 2, e.g. `100 WELCOME`, same alignment (left); **selected column header** e.g. `PRICE` (right column, one column in — see below) | Part 4 / Part 5 |
| 10–20 | The entry list — up to 11 entries, one per row (see below) | Part 6 (+ selected Part 5 column) |
| 22–23 | Footer / advert — Part 2's two lines, **centred** on their rows | Part 2 |

**Breadcrumb alignment.** Part 4's two lines are **not** drawn at column 1. They share the
entry columns: the leading **page number is right-justified** in the same left column the entry
page numbers use, and the title follows. Part 4 already contains the padding spaces
(`     1 *** COMPUNET ***`, `   100 WELCOME`), so a client renders each Part-4 line from the
entry list's **base column (screen column 1, above)** and the alignment falls out (the shorter
`1` ends up more indented than `100`), and the breadcrumb page numbers line up with the entry
page numbers directly below.

The **built-in template (§7.5) is always drawn first as the base chrome** — the bordered box,
column dividers, and the column-cycle indicator. The template intentionally begins with six
blank rows (its body opens with a six-fold `CR` run), leaving the **header region (rows 0–5)**
empty. A client then **overlays Part 1 there when it is non-empty** (e.g. the COMPUNET logo);
when Part 1 is empty (`$00`), rows 0–5 simply remain as the template left them. The path,
entries, and footer overlay on top as below. A client that draws only the template and skips
Part 1 will render every directory without its header graphic.

Within the entry rows, each entry occupies **one** row. A client **MUST NOT** render the whole
comma-separated Part-6 line — it is wider than 40 columns and would overflow.

Each entry's 27-character first field (§7.3) is rendered starting at **screen column 1** — the
box interior, just inside the left border (the template draws the left border at **column 0**,
the vertical divider at **column 30**, and the right border at **column 39**; §7.5/§A.6). So the
page-number sub-field occupies screen columns 1–6, the title 8–24, and the type 25–27. This
applies to the **whole row together** — page number, title, and type — and matches the base
column the Part-4 breadcrumb is rendered from (below), so the two align. The columns are
**relative to the box**: content sits at the interior (column 1), not offset from it; a client
that starts the row a column further in leaves a blank gap inside the border and pushes every
column one character too far right.

Each entry row shows:

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
highlighted", so the client draws the highlight itself. It is a **bar spanning the row across
both panes** — the entry columns **and** the right-hand value column — in **the entry's own
positional colour** (a **red** bar for the first entry, a **blue** bar for the others), with the
**text drawn in white** (index 1) on top.

> **The bar must not overwrite the vertical divider (normative).** The template's divider at
> **column 30** (§7.7 geometry) stays visible *through* the highlighted row: the bar is drawn in
> the box interior on **either side** of it — columns **1–29** and **31–38** — leaving column 30
> as the template drew it. The row reads as two highlighted panes separated by the divider, not
> as one bar painted over the box furniture. A client that fills straight across the row erases
> the divider on whichever row is selected, so the column separator appears to break as the
> user moves the highlight. This "colour bar + white text" cannot be
expressed with a single PETSCII cell attribute, which is another reason it is client chrome,
not wire content. A client **MUST** draw the highlight this way (not a single fixed colour),
and the red-first / blue-rest entry colouring is **required** either way — it is part of the
authored Compunet look.

> **Do not fake the bar with per-cell reverse-video.** Reverse-video swaps each cell's
> foreground and background independently, so the "bar" only appears in the cells that happen to
> be blank and the glyph cells stay their own colour — you get a broken row of coloured stripes,
> not a solid bar with white text. Draw it as a genuine two-layer highlight: fill the **entire**
> row's background (all 40 columns of that row, both panes) with the positional colour, then
> render the glyphs in **white** over it. The bar's colour is the *background* of every cell in
> the row, independent of each glyph's own colour.

### The selected column header

The header of the currently-selected column (the Part-5 name — `PRICE`, `AUTHOR`, …) **MUST**
be displayed so the user can see which column the right-hand values belong to. It sits in the
**right-hand pane at row 8** (level with breadcrumb line 2, `100 WELCOME`), drawn in blue. Both
the header and every entry's value are rendered **from the pane's base column — screen column 31
(one past the divider at column 30)** — **verbatim**: the server has already justified them
(§7.3), including the leading space on the `PRICE`/`AUTHOR`/`LIFE` headers that indents the text
one column into the pane. So the client does **not** re-indent or re-justify; it draws the
Part-5 header string and the per-entry value string as-is at column 31. A client that shows the
column *values* but omits this header leaves them unlabelled.

**Cycling the right-hand column is a required capability (normative).** The right-hand pane
shows only **one** Part-5 column at a time, and the user **MUST** be able to **rotate** it
through the whole Part-5 set (for the top directory: `PRICE → AUTHOR → VOTE/NUM → UPLDDATE →
LIFE → PRICE …`). Both the displayed header **and** every entry's value in that pane change
together as the user cycles. The reference control is the **`F7` / `F8`** keys (`F7` = previous
column, `F8` = next), which is why the template draws the **`<F7)(F8>`** indicator in the box
(§7.5/§A.6) — a client **SHOULD** honour `F7`/`F8`, and the rotation itself is **not** optional.
A client that pins the pane to a single column (e.g. always `PRICE`) does not conform.

**Clicking an entry (pointer clients).** Selection is client-local (§4.5), so a client with a
pointer **MAY** let the user click a directory entry:

- **Single click — highlight it.** The equivalent of moving the highlight with the cursor keys.
  Nothing is sent; no command is invoked.
- **Double click — `DIR`.** Entering the entry as a directory (§4.7) is the *only* command a
  click may invoke. This is the **Amiga client's** behaviour and is the reference for pointer
  clients: its event loop tests Intuition's `DoubleClick()` against the same gadget and passes a
  click count to the entry's handler, so a double click is a distinct signal from a single one.

**In Courier (§8.2) a double click does nothing.** `DIR` is not part of the mail command set
(§4.8), so there is no command for a double click to invoke — a single click still highlights a
message, and reading it is `SHOW` from the row. This is not a special case so much as the
general rule holding: a double click means `DIR`, and where `DIR` does not apply, it means
nothing.

A click **MUST NOT** invoke any other command — in particular **not `SHOW` and not `BUY`**, so a
pointer user can never be charged for a paid page by clicking (§8.6.4); reading and buying stay
deliberate acts through the duckshoot. Nothing here adds to the vocabulary (§4.7): the single
click is *selection*, which is not a wire operation at all, and the double click is `DIR`, which
already exists.

**Clicking the indicator (pointer clients).** The template draws `<F7)(F8>` in the box precisely
because those are the controls, so a client with a mouse or other pointer **MAY** make that
indicator **clickable** — the `F7` half cycling back, the `F8` half forward, with the same effect
as the keys. This is the recommended way to offer column cycling on a pointer device: it reuses
the affordance already drawn on screen. Note the rotation is **not** a Compunet command and has
no entry in the §4.7 vocabulary, so it **MUST NOT** be added to the duckshoot as a word of its
own (§4.7 — the vocabulary is closed); a client that adds a `COL` or `COLUMN` command has
invented one. Internally this selects
among the columns the way the ROM's `$C002` column index does; the client tracks it locally.

A client **MUST** reproduce this canonical C64 layout so that content authored for Compunet —
which assumes this geometry — lands correctly.
