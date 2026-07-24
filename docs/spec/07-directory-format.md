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

The five column headers the server emits in Part 5 are, in order: `PRICE`, `AUTHOR`,
`VOTE/NUM`, `UPLDDATE`, `LIFE`. A client cycles which column is shown alongside each entry.

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

The type indicator (first-field chars 24–26, from screen column 25) tells the client how an
entry behaves when selected:

| Type | Meaning | Selecting it |
|---|---|---|
| `T` | Text page(s) | show the frame(s) (§6) |
| `D` | Directory (no content of its own) | enter it (new directory response) |
| `+` | Has a sub-directory beneath it | enter it |
| `P` | Program / telesoftware | download (§8.3) |
| `PP` | Protected program | download; original required the modem as a dongle |
| `S` | Sequential file (word-processor format) | download / view |
| `L` | Link | activate the link subsystem (§8.5 — Partyline on the modern server) |

A number after the letter indicates size (K for programs, page count for text). A client
**MUST** read the type from screen column 25 and dispatch selection accordingly.

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

- The server tracks a page offset and returns the next 11 entries when the client requests
  more (selecting past the last visible entry advances the offset by 11; §4.4 `D`).
- A client **MUST** support paging and **MUST NOT** assume a directory fits in one response.

*(Non-normative: the modern server reloads its content tree on each directory request, so
listings reflect live content changes without a reconnect.)*

## 7.7 Screen composition

The six parts (§7.2) and the template (§7.5) are composed onto the 40×24 grid at **fixed
rows**. These positions are verified against both reference clients (the C64 and the Amiga
`parse_directory_frame` agree), so a client reproduces the layout by placing each part at the
row below:

| Rows | Content | Source part |
|---|---|---|
| 0–5 | Header region | Part 1 header frame, else the built-in template (§7.5) |
| 7 | Path / breadcrumb line (from column 1); page-number column at column 31 | Part 4 |
| 10–20 | The entry list — up to 11 entries, one per row, starting at column 1 | Part 6 (+ selected Part 5 column) |
| 22 | Footer / advert line | Part 2 |

Within the entry rows, each entry occupies one row: the fixed-layout first field (§7.3) —
page number, title, and type at column 25 — plus the currently-selected column value (the
Part-5 header the user has cycled to with the column toggle). The **normal** text uses colour
index 2 and the **highlighted / selected** entry uses colour index 6 (the reference clients'
`frame_pen_lower` / `frame_pen_upper`); a client **MUST** visually distinguish the selected
entry so the user can see the current selection.

A client **MUST** place the parts at these rows (or reproduce the equivalent visual layout)
so that content authored for Compunet — which assumes this geometry — lands correctly.
