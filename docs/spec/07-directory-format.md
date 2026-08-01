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

### What a Part-1 header may contain (normative)

Earlier revisions of this section described where the header is *composed*
(§7.7) but placed no constraints on its *content*, which read as "anything a
frame may contain is fine here". It is not, and the omission mattered: a server
may now accept header frames from users (they are no longer operator-authored
only), and each rule below exists because a specific renderer misbehaves without
it. A header frame **MUST**:

| Rule | Why |
|---|---|
| Draw only on **rows 0–5** | Part 1 is printed **over** the already-drawn template (§7.5). There is no clipping in the reference clients: printing on row 6 destroys the frame's top border, and lower still overwrites the breadcrumb, entries and footer. Past row 23 the C64 KERNAL scrolls the whole screen |
| Contain **no `$00`**, not even as an RLE operand (§6.4) | The C64 copies Part 1 with a **byte-level** loop that stops at the first `$00` and has no RLE awareness, so a `$00` used merely as a repeat count still ends the part — and everything after it is read as Part 2/3/4, desynchronising the six-part stream. This is the general §6.4 rule, and Part 1 is where its absence bit hardest |
| Contain **no `$93`** (clear screen) | The template is drawn first, so a clear-screen erases the entire directory — border, breadcrumb, entries and all — leaving only what the header itself then draws |
| Leave the character set as it found it | Nothing re-issues `$8E` after Part 1, so a `$0E` leaks the lower-case set into the rest of the screen |
| Leave reverse video off | An unmatched `$12` reverses the start of the next line drawn |
| Fit within the header buffer | The C64 stores Part 1 at `$D000` with **no length counter and no bounds check**; the next part's buffer begins at `$D300`, so **768 bytes** is the point at which a header silently corrupts the parts after it. A server accepting user-supplied headers should enforce a limit well below that |

⚠ **These are constraints on what a server may SEND, not licence for a client to
assume them.** A client is still responsible for its own display: bounding Part 1
to rows 0–5 costs little and turns a hostile or simply broken header into a
cosmetic problem rather than an unusable screen.

**A header cannot set the background, and authors must design against the one it
gets.** The C64 has a single background register for the whole screen (§8.4.3), so
Part 1 has no way to colour its own rows — it is printed onto the directory screen
the template already established. The reference client fixes that background at
**`$0F`, light grey** (`LDA #$0F` / `STA $D021`, `compunet.s:3785`), so ink in
colour 15 is invisible in a header, however it looked where it was drawn.

Two consequences for anyone building an authoring tool:

- **A header is stored as the frame BODY only** — no `[flags][border][background]`
  prefix (§7.2). Those three bytes are meaningless for Part 1, since it cannot
  apply them. An editor that saves whole page frames therefore produces a file
  that is *not* a header, and its flags byte is `$00`, which the "no `$00`" rule
  above rejects at offset 0. Strip the prefix before validating; the leading byte
  is unambiguous, because a valid header body can never contain `$00` at all.
- **Preview against light grey, not the editor's page colour.** An author designing
  on white or black will produce artwork whose contrast is wrong, and in the worst
  case a line that vanishes entirely, with nothing to warn them. Both traps were
  hit on the first real user submission (#126) — in the same file.

**Part 2 → Part 3 boundary — do not consume a `$00` after the footer (normative).** The footer
is exactly **two `$0D`-terminated lines** (empty lines if there is no advert); Part 2 does *not*
emit a `$00`. The very next `$00` in the stream is **Part 3's** terminator (its empty
field-definitions list). A parser that reads the two footer lines and then also consumes a
trailing `$00` as "Part 2's terminator" swallows Part 3's terminator and shifts **every later
part by one byte** — the entries spill into the path line. Read exactly two `$0D` lines for
Part 2, then let Part 3's loop consume the `$00`.

**⚠ The `1` on breadcrumb line 1 is not a page number.** Every content listing opens with
`"     1 *** COMPUNET ***"`, which reads as "page 1 is the root" — it is not. There is no page 1;
`GOTO 1` fails. The digit is part of the fixed system banner, occupying the same 6-character
page-number field as the line below it so the two align. Render Part 4 **verbatim** (§7.7) and
never parse a page number out of it: a client that did, to build a "go to root" affordance, would
produce a dead command — and would be inventing one, which §4.7 forbids. (VALIDATION.md, F54.)

**The Part-5 column headers are response-specific — do not hard-code them.** The
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
The marker sits on breadcrumb **line 2** and, in the original's stream, begins at **column 25** —
the same column the entry rows put their type indicator in, so it lines up with a column that
already exists and stays clear of the divider at 30. A binding that carries the marker as a flag
rather than as inline text (Binding B's `mailWaiting`) **MUST** draw it at that position.
(VALIDATION.md, F37.)
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

**⚠ The placeholder is a LABEL, not an entry: its page-number and type columns are BLANK.**
It pads to the full 27 characters like any other row — the widths are what keep the parsers
alive — but it fills the page column with **spaces**, not `0`, and the type column with
**spaces**, not a base type. A `0` there advertises a page that does not exist, and a `T`
announces a text page, in a listing whose entire content is the statement that it holds
nothing. Only the title column carries anything.

The same holds for a listing rendered from a structured binding: the placeholder's page
number is the sentinel **0** ("not a real page", since no real page is numbered 0) and its
type is the **empty string**. A client **MUST NOT** draw a page number of 0, and **MUST NOT**
substitute a default type for an absent one. Getting this wrong is a §1.8 divergence in
miniature — one binding blanked both columns while the other sent `type: "T"`, so the same
empty directory read differently depending on which binding the user reached it through.

Placeholder rows are also **not selectable** for the entry-acting commands (§4.8): there is
nothing at that row to `SHOW`, `DIR`, `VOTE`, `LIFE` or `BUY`.

## 7.4 Entry types

The type indicator (first-field chars 24–26, from screen column 25) is **compound**, not a
single symbol. It is a **base type**, optionally followed by a **size** and/or a
**sub-directory marker**, in this order:

```
<base> [<size>] [+]
```

- **base** — one of `T`, `D`, `P`, `PP`, `S`, `L` (note `PP` is two letters). This letter
  determines what happens when the entry is selected (below). The original service also used
  `F` (IFF picture) and `A` (action) — both documented in §7.4.1. The reference server **serves
  `F`**; it does **not** serve `A`. A client **MUST NOT** assume the set is closed: see the
  fall-through rule below.
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
| `F` | IFF/ILBM picture (§7.4.1) | download and display the picture — Amiga and web; **refused to the C64** |
| `A` | Action: executable, run on arrival (§7.4.1) | download and immediately execute — **machine-specific; deliberately not served, and refused** |

**⚠ The base-type set is OPEN, and a client MUST fall through safely (normative).** The reference
server serves `F` (§7.4.1); it does **not** serve `A`, and a future producer MAY use a base
letter this table does not list. A client **MUST NOT** crash, hang, run, or corrupt the screen on
a base type it does not implement: it **MUST** treat an unrecognised base as inert (behave as for
`D` — SHOW does nothing) rather than fall into a default that feeds the bytes somewhere unsafe.
See §7.4.1 for why this rule is written down: the era clients did **not** all obey it, and that is
a property of those frozen binaries, not a licence for new clients to repeat it.

**⚠ SHOW on an entry with no frames does nothing (normative).** `SHOW` reads an entry's text
frames; if the entry has none — which is the normal case for a `D` (directory-only) entry — then
there is nothing to read and **SHOW is inert**: the screen does not change and the user stays in
the listing. It **MUST NOT** fall back to entering the sub-directory, because that would make
`SHOW` and `DIR` the same command on exactly the entries where the spec is at pains to keep them
apart (§4.7). Entering is `DIR`, and only `DIR`.

**How a server expresses "inert" on the wire.** There is no "do nothing" response — the client
has sent a command and is waiting. The server **SHOULD** answer with the **current directory
listing, unchanged**: same page, same highlighted entry. The user sees no change, which is the
required outcome, and the sequence stays in step. Answering `D` with a directory response is
already part of the protocol — it is what `MORE` returns once the last frame of an item has been
shown (§4.7) — so this needs no new client behaviour.

A server **SHOULD NOT** answer with an error frame (`NO CONTENT` or similar). The C64 client
dispatches on the response byte as *linking* (`$4C`), *ACK* (`$41`), or **anything else = data
follows**, so an error response is rendered like any other page: it paints over the screen. That
is a visible change, and therefore not inert.

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

### 7.4.1 The `F` (IFF picture, served) and `A` (action, not served) types

The reference server **serves `F`** (below) and does **not** serve `A`. Both are documented here
because the *protocol* the era clients speak is larger than the subset this service uses, and a
spec that hides that misleads anyone building a client against a real Amiga binary — the same
class of omission as §8.3.1's per-machine download descriptor before #123. Behaviour below is
verified against ground truth: the original Amiga client's download jump table (relocated
disassembly at `0x10b780`), its reconstructed source (`client/amiga/src/download.c`), and the C64
client source (`client/c64/src/compunet.s`).

**`F` — IFF/ILBM picture, streamed (SERVED).** On the Amiga, `F` dispatches to a chunk state
machine (`iff_feed_byte`) that parses FORM/ILBM/BMHD/CMAP/BODY, opens a custom screen sized from
the BMHD, and blits the image **row by row as the bytes arrive** — both uncompressed and ByteRun1.
The picture painting in during the download was the point on a 1200-baud line. IFF is a 68k-era
bitmap format, so `F` content is **always Amiga** (`machine_type: amiga`).

> **`F` is delivered exactly like an Amiga `P` (normative).** The Amiga's `F` handler
> (`action_download_run`) reuses the very `file_download_xfer()` that programs use: the client
> sends the `D` command, the server replies with the **8-byte download descriptor** (§8.3.1,
> machine byte `1`, 32-bit big-endian size at 4–7, no load address), the client answers with the
> `$40` proceed token, and the server streams the body as DAT frames terminated by EOS. The **only**
> difference from a `P` is what the client does with the delivered bytes: a `P` is saved, an `F`
> is decoded and displayed. A server therefore needs no new transfer path — it emits the
> descriptor for an `F` entry just as for an Amiga `P`.

**Cross-client safety for `F` (normative).** Because IFF is Amiga-only, the server **MUST NOT**
hand the descriptor to a client that cannot render it. The reference server refuses an `F`
download to the **C64** (which has no IFF decoder) with an error response the C64 paints as a
page (`PICTURE - AMIGA ONLY`), and serves it to the native Amiga and to Binding B (the web /
Electron client, which carries its own ILBM decoder). This guard lives server-side because the
C64 is frozen (§1.8) and cannot be taught to refuse for itself.

**`A` — action: executable, downloaded and run (DELIBERATELY NOT SERVED).** On the Amiga, `A`
fetches an executable to `RAM:temp`, checks the machine byte is `1`, and `Execute()`s it —
printing **"Not for Amiga!"** if the machine type is wrong. It differs from `P`: a `P` is *saved*,
an `A` is *run* immediately. The payload is native code, so `A` is **machine-specific** even
though more than one client implements it.

The reference server **does not serve `A`, as a decision rather than an omission.** The type
downloads and immediately executes native code; the payload only runs on the CPU it was built
for; and the **C64 has no machine guard at all** — it zeroes three bytes at `$0801` and executes
whatever arrived, whoever it was meant for. The capability on offer (run-on-arrival software) does
not come close to justifying an arbitrary-code-execution path into clients that are frozen
binaries and cannot be fixed (§1.8).

> **⚠ A server that does not serve `A` MUST REFUSE IT EXPLICITLY (normative).** Not serving it is
> not the same as not implementing it, and the difference is dangerous. A client dispatches on the
> **type letter**, not on what the server sends: an `A` entry reaches the client's action handler,
> which expects the 8-byte download descriptor (§8.3.1) and then executes the result. If the
> server instead lets an `A` fall through to the ordinary frame path, the two ends disagree
> completely — the client reads the frame's leading bytes **as the descriptor**, and on a C64 goes
> on to execute the received data. The reference server therefore answers SHOW on an `A` with an
> error response (`NOT AVAILABLE`), which a client renders as a page (§7.4). The entry still
> appears in the listing, so an operator can see it exists; it simply cannot be selected.
>
> This matters even where `A` cannot be uploaded (see below): a hand-edited `directory.json`, an
> import, or a migration can still introduce one, and "unlikely" is not a guard against code
> execution.

> **⚠ A server MUST also gate CONTENT UPLOAD to the types it supports, on EVERY path a user can
> reach (normative).** Refusing to *serve* `A` is only half the guard: a stored `A` is an
> executable sitting in the tree waiting for the other half to be forgotten. Accept `T`, `P` and
> `F` (§8.3.2) and refuse every other letter with an error the user can see.
>
> The trap is that this is **reachable from an era client, not only from a crafted one**. The
> Amiga's publish requester takes the page type as a **free-text field**, and `put_frame`'s jump
> table (relocated `0x10c3c2`) routes `'A'`, `'S'`, `'P'` and `'F'` alike to `upload_file` — so a
> user can type `A`, and the client will happily stream a file for it. The reference server gated
> only its JSON binding for two releases while its X.25 binding and its PETSCII terminal accepted
> any letter and stored it verbatim; this specification asserted the gate existed while it did
> not. Put the check at each entry point (so the user learns before spending a transfer) **and**
> in the shared code that writes the page, so a binding added later inherits it.
>
> A path may legitimately gate **more narrowly** than the server as a whole: the reference
> PETSCII terminal accepts only `T` and `P`, because its upload path writes a `.prg` with no
> machine type and cannot store an `F` correctly. Refusing what a path cannot store is right;
> storing it wrongly is not.

**Per-client behaviour (verified):**

| Client | `F` (IFF) | `A` (action) |
|---|---|---|
| **Amiga** | dedicated streaming ILBM viewer | runs it; guards on the machine byte (`"Not for Amiga!"`) |
| **C64** | **no handler — would garbage-render**; the server refuses it the download instead | **runs it as 6502 code, with no machine guard** |
| **Web / Electron** | decodes and displays the ILBM (Binding B) | not implemented |

**⚠ Why the fall-through rule in §7.4 exists.** The C64 client (frozen, era-accurate — see the
locked-client note below) does **not** degrade safely on `F`: it has no concept of the type, so
SHOW would fall through to its default page-display path and feed the ILBM bytes to the frame
interpreter, corrupting the screen — which is exactly why the server refuses it the `F` download.
And it will run an `A` payload as 6502 with no "is this for me?" check. These are properties of a
shipped 1980s binary that **cannot be changed**. A new client is therefore held to the higher bar
of §7.4: an unrecognised base type is **inert**, never executed and never fed to a renderer.
Because the era C64 cannot be fixed, any safety for a mixed directory that contains Amiga-only
content must live **server-side** (`machine_type`, §8.3.1, is the hook).

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

## 7.6 Overflow: how a directory holds more than 11 entries

A directory shows **11 entries**, and that is the whole of it — **an authored directory does not
paginate.** There is no page two, no paging command, and no client-side page state (the C64
client has none: no offset, no scroll counter, nothing).

**Overflow is authored, not automatic.** When a directory fills up, its owner adds an ordinary
**`D` entry** — conventionally titled `MORE` — whose sub-directory holds the next batch. The user
enters it with `DIR` like any other directory. That is what the original manual is describing when
it calls a `D` entry "a dummy page; cannot be shown; use DIR to access the directory beneath".

> **⚠ This is why §8.3.2 caps uploads at 11.** The cap looks arbitrary until you see that a
> directory *displays* 11 and there is no second page — the limit is the display, and the
> `MORE` entry is the user's answer to it. A specification that describes automatic paging makes
> that cap inexplicable. **Authored directories have no server-side pager and no synthetic `MORE`
> row** — do not implement one; the exceptions are the generated listings below.

**Generated listings are the exception.** UCAT (§8.6) and the mailbox (§8.2) are *assembled by the
server*, so their owner cannot author a `MORE` entry into them. Those, and only those, may
overflow, and the server supplies the row itself:

- The last row of a truncated generated listing is a **synthetic pagination entry**: no page
  number, the title `MORE        >>>>`, and an **empty type** field. It is not real content and
  does not fit the §7.4 type grammar.
- **Selecting it pages forward.** The client sends the entry's index like any other selection —
  which, being one past the real entries, the server reads as "next page". No paging command
  exists, and none is needed: the client keeps no page state, it just sends an index.
- A client **SHOULD** render the row as an ordinary entry and **MUST NOT** treat it as content.

> **Two different limits both happen to be 11 — do not conflate them.**
> - **A page shows 11 entries.** That is a *display* limit, and for authored directories it is
>   also the effective total.
> - **§8.3.2's 11 is a *capacity* limit on uploads** — the server refuses a 12th child. Same
>   number, different rule: one governs what is drawn, the other what may be written.

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
| 22–23 | Footer / advert — Part 2's two lines, **verbatim from column 0** (⚠ *not* centred — see below) | Part 2 |

**⚠ The footer / advert is drawn VERBATIM from column 0 — a client MUST NOT centre it
(normative).** Centring is the tempting mistake here, because it looks like a courtesy: the two
lines are printed exactly as Part 2 delivers them, and **any positioning is the author's**,
expressed as leading spaces.

Verified in the vintage binaries. Centring requires computing `(40 − length) / 2`, and across
**both** originals — the 8 KB ROM and the 7,699-byte terminal — there is not a single
instruction that halves a value, nor a division routine to call. Every `$4A`/`$6A` byte in them
is a `J` inside a string or the low byte of an address operand; the only genuine shifts are four
consecutively to print a hex nibble, and one `LDA #$00 / ROR` building a flag. The original
does not centre differently from us — **it cannot centre at all.**

Two consequences a client author should keep in mind:

- **Re-centring an already-centred line moves it.** Authors centre by padding, so a client that
  also centres adds the padding twice and shifts the text right — by a different amount per
  line, which makes the two rows look misaligned with each other rather than merely offset.
- **Centring is lossy.** Because Part 2 arrives as typed, an author can left-align, right-align
  or indent deliberately. A client that centres takes that away and offers no means to express
  it.

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
positional colour** (a **red** bar for the first entry, a **blue** bar for the others).

**⚠ The highlight SURVIVES a return to the same listing (normative).** Read an entry and come
back — by `FINISH`, by paging off the end of a multi-frame page, or by any route that lands on
the listing you were already on — and the bar **MUST** still be on the entry you read. It moves
only when the user moves it, or when a **different** listing is displayed, which starts at the
first entry. The chosen right-hand column (§7.7, `f7`/`f8`) persists on the same terms.

This is free in the original and easy to lose elsewhere. The C64 never reloads a directory to
return to it: the listing sits in client RAM (`$D500` names, `$D600` details) and returning
re-renders that cache, so the highlight index is simply never touched — "no automatic directory
reload". A binding that **re-sends** the listing on the way back (as Binding B does) has no such
cache, and a client that resets its selection whenever a listing arrives will throw the user to
the top of the directory every time they read anything. Judge "the same listing" by its **page
number and its entries**, not the page number alone: a mailbox `MORE` keeps the page number while
replacing every row, and that is a new set of things to choose from.

**⚠ The bar is REVERSE VIDEO, and the text in it is the SCREEN BACKGROUND colour — not white
(normative).** Verified in the original client at `$A6DC`, which walks the row doing
`LDA ($D1),Y / ORA #$80 / STA ($D1),Y` — setting bit 7 of each screen code — and writes the bar
colour to **colour RAM**. It cannot work any other way: the C64 has **one** background register
for the whole screen (§8.4.3), so "a coloured background behind white text" is not something the
hardware can express, and `cnet.prg` contains no colour-RAM write that could fake it.

The consequence is what a client must reproduce: reversing a cell fills it with the
**foreground** and knocks the character out in the **background**, so the text inside the bar
appears in the screen's background colour. Selected and unselected rows therefore differ by
**`rv` alone** — one bit, exactly as they do on the original. A client that models the bar as a
per-cell background gets a *visibly* different result (white text instead of background-coloured)
and, worse, builds a page model the hardware cannot produce, which then leaks into everything
that touches cell backgrounds (§8.4.3).

**The glyphs keep their own colour — they do not turn white.** A bar of positional colour with
white text on it is *not* what the original draws, and a client **MUST NOT** render it that way.

> **The bar must not overwrite the vertical divider (normative).** The template's divider at
> **column 30** (§7.7 geometry) stays visible *through* the highlighted row: the bar is drawn in
> the box interior on **either side** of it — columns **1–29** and **31–38** — leaving column 30
> as the template drew it. The row reads as two highlighted panes separated by the divider, not
> as one bar painted over the box furniture. A client that fills straight across the row erases
> the divider on whichever row is selected, so the column separator appears to break as the
> user moves the highlight. A client **MUST** draw the highlight this way (not a single fixed
> colour), and the red-first / blue-rest entry colouring is **required** either way — it is part
> of the authored Compunet look.
>
> *(Verified: the original's loop runs `LDY #$26` down to 1 with `CPY #$1E / BEQ` skipping the
> divider — columns 1–38 except 30, which is exactly the extent above. ⚠ Not all 40 columns.)*

> **Draw the bar with per-cell reverse video, setting the whole row to one colour.** For each
> cell in the extent: set **bit 7** of the screen code and write the **bar colour** to that
> cell's foreground. The row then reads as a solid bar with the text knocked out of it in the
> screen's background colour.
>
> The trap is doing only half of it. Reverse video **alone** — flipping each cell while leaving
> its own colour — gives a broken row of coloured stripes, because each glyph keeps whatever
> colour it had. What makes it a *bar* is that the original writes the **same** colour to every
> cell in the row before reversing it (`TXA / STA ($F3),Y` at `$A6F2`), so the whole extent
> shares one foreground. Reverse video plus a uniform row colour is the mechanism; reverse video
> by itself is the failure.
>
> **⚠ Do not reach for a background fill instead.** Filling the row's background with the
> positional colour and rendering white glyphs over it is not available to the hardware at all:
> there is **one** background register for the whole screen (§5.5). Verified at `$A6DC`.

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
