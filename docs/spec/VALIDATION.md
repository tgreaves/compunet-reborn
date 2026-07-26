# Validation record

> Part of the [Compunet Client Specification](README.md). Phase 5 of issue #111: confirm
> the spec explains the behaviour of both reference clients and the server, and record any
> residual gaps honestly. This is a companion note, not part of the normative spec.

## Method

The spec was written by **triangulation**: every normative claim was derived from the
server (`compunet_server.py` / `x25_protocol.py`, the protocol authority) and confirmed
against the two reference clients (C64 terminal in `compunet.s`; the reconstructed Amiga
client, disasm-verified). A claim was only accepted when it matched the bytes the server
emits/accepts **and** explained both clients' behaviour. The cross-reference in
[xref.md](xref.md) links each section to its implementation.

## Cross-checks confirmed

| Area | Server | C64 | Amiga | Result |
|---|---|---|---|---|
| Framing / stuffing / CRC | `x25_protocol.py` | PROTOCOL.md wire format | `protocol-analysis.md`, `cnet-device-re.md` | agree ✓ |
| Tokens (`DAT $22`, `COM $43`, `ACK $20`) | acted on as `$43` | login pkt `$43` | RE `serial_write(...,0x43)` | agree ✓ (resolved the `$26` doc error) |
| ACK pacing / EOS | `wait_for_ack` | ROM ACK path | link header no-EOS case | agree ✓ |
| Identification | `is_amiga`/`has_slash` detect | `{hash}/100` | doubled `C CNET` + 14 zeros | agree ✓ |
| Login packet layout | `[1:9]`/`[9:15]` | `$C100` build | — | agree ✓ |
| Command set (single letters) | `handle_command` | ROM dispatch | `identification-and-commands.md` | agree ✓ |
| Content grid **40×24** | — | 40×25 less status row | `frame_control.c` bounds `0x28`/`0x17` + `clear_screen` | agree ✓ |
| PETSCII→screen-code | — | ROM CHROUT | `frame.c` `render_char` | canonical ✓ |
| Palette (16 C64 colours) | — | VIC-II | `g_palette` remap + LUT | agree ✓ (remap reconciled) |
| Control codes `$00–$1F`/`$80–$9F` | — | ROM | `frame_control.c` (verified byte-for-byte) | agree ✓ |
| RLE `$06`/`$07`, `1+N` | — | PROTOCOL.md (`$06`) | `frame.c` `frame_rle_getchar` | ✓ (Amiga has both escapes; traced the `1+N` decrement) |
| Frame header (4-byte) | `_make_info_frame` | 3-byte + charset body | `frame.c` reads 4th byte | agree ✓ (offset 3 = charset in all) |
| Directory 6-part stream | `_make_page_response` | L_A5F3 parser | `directory_parse.c` | agree ✓ |
| Entry layout (dual constraint) | 27-char fixed + commas | comma-delimited | fixed-width 6/16/5 | agree ✓ (spec requires both) |
| Directory template | Part 1 empty → client | `$BCE1` frame | GUI equivalent | agree ✓ |
| Partyline raw session | `partyline.py` | downloaded chat prog | resident CnetTty | agree ✓ |

## Contradictions found and resolved (now correct in the spec)

1. `COM = $26` (docs/x25 constant) vs `$43` (what the server acts on) → §2.5 states `$43`.
2. Two identification handshakes, never unified → §3.3 specifies both + detection.
3. Frame header size (3-byte "content at byte 3" vs 4-byte charset) → §6.2 = 4-byte, byte 3
   is a charset control (what the server emits, what both clients consume).
4. RLE documented as `$06`-only vs `$06`+`$07` with `1+N` count → §6.4 specifies both.
5. Non-standard Amiga colour mapping → shown to be the `g_palette` pen remap; §5.5 keeps the
   standard C64 palette.
6. `CMD_EDITR = $45` constant vs `E` = LEAVE in dispatch → §4.4 states `E` = LEAVE.

## Residual gaps and caveats (honest limitations)

These are known, deliberately-bounded, and do not block building a conformant client:

- **Status-byte text mapping.** Non-`@` status bytes (`A`/`B`) trigger client-specific
  status messages (e.g. "Host error"); the exact text mapping is a client concern and is
  left non-normative (§4.3).
- **Editing UX.** §8.4 specifies only that the editor's output is a valid frame submitted via
  upload; the editing experience itself is deliberately unspecified.
- **Browser transport.** The spec is TCP-only; a browser cannot open a raw TCP socket, so a
  web client would need a WebSocket transport binding that this spec does not yet define. The
  abandoned `client/web/` experiment is **broken and non-compliant** (flagged in its README)
  and is **not** a reference — the spec's assets are extracted from the C64/Amiga clients only.
- **PETSCII→screen-code table (§5.3)** is taken from the Amiga renderer (the canonical C64
  transform); it has not been independently diffed against the C64 KERNAL path. To confirm
  when a test client is built.
- **`xref.md` line numbers** drift as code changes; symbol names are the stable anchor.
- **Live wire trace.** §A.7 is a hand-constructed trace. A captured real session (byte dump)
  would strengthen it; none is bundled yet.

*(Resolved in a later pass, no longer gaps: §8.3.2 upload/mail-send is now specified
byte-exact from the server handlers; the §A.6 directory template was rendered to confirm what
it draws; §3.5 states the server ignores the login system-info field.)*

## Test-client validation (Tier 1)

A clean-room Tier-1 client (`client/pygame/`) was written **from `docs/spec/` alone** — not
referencing the server or the C64/Amiga source — and run against the live `docker.lan:6400`
server. It successfully connected, identified (native handshake), logged in, rendered the
welcome/personal-info frame, listed the top directory, selected an entry, and rendered the
live `WHO IS ONLINE?` page. The framing, CRC, ACK pacing, session flow, PETSCII display, and
directory parsing all matched the server on the wire. The build surfaced eight findings; the
substantive three were fixed in the spec this pass:

- **§6.2** — softened: byte 3 is *consumed* as the charset selector (non-`$0E` = uppercase);
  the server's own error frame carries `$0D` there, so a client must tolerate any value.
- **§5.6.1** (new) — the auto-wrap/`CR` guard ("just-wrapped" flag) is now spelled out; it was
  only alluded to before, which caused a blank line between every full-width row.
- **§7.7** — made explicit that each entry row shows only its first field + one selected
  column, never the whole comma-separated line (which overflows 40 columns).

Three further clarifications were added (§2.8 client sequence start, §3.2 initial handshake
byte, §4.5 reading the entry type from the first field). Two remain non-normative by design
(§6.3 pre-colour default, §4.2 non-DAT mid-stream).

A second round of testing (wiring up the commands) surfaced three more, all fixed:

- **§4.6** (new) — the spec described commands but never required a client to let the user
  *invoke* them; a conforming client now **MUST** provide a means to issue the commands of
  its tier (the interface — keys, menu, duckshoot — remains its choice).
- **§7.2/§7.7** — the top directory's **Part 1 header** (the COMPUNET logo) was being
  dropped; clarified that the template is always the base and Part 1 overlays the header
  region.
- **§4.4** — the `I` command was mislabelled "ID / WHO". It is an **ID lookup** (takes 8-byte
  user IDs, returns name pairs); with no argument it returns nothing. "Who is online" is a
  content page, not this command. Also noted: a client **MUST** read with a timeout, since a
  command can legitimately produce no response.
- **§4.7** (new) — the spec gave the *wire* commands but not the *user-facing* Compunet
  command names, so a builder invents labels and gets them wrong (the client first labelled
  the read-entry action "OPEN"). §4.7 now standardises the duckshoot vocabulary (DIR, SHOW,
  BACK, GOTO, ACCNT, MAIL, UCAT, MORE, FINISH…) and its mapping to the wire commands.
- **§4.4/§4.5/§4.7/§7.4/§8.3.2** — the DIR/SHOW/FINISH/MORE model was corrected. Earlier drafts
  conflated DIR and SHOW onto `D`+index. The right model: **SHOW** = `D`+index (show the
  highlighted entry's frame(s)/download; never enters a directory); **DIR** = `P`+index (enter
  the highlighted entry *as a directory*); **MORE** = `D` no-arg; **FINISH** = `P` no-arg
  (return from a frame). DIR on an entry that is not `D`/`+` opens an **empty latent**
  directory, which a subsequent upload materialises — this is how the directory hierarchy is
  built (the client issues DIR/upload; the **server** creates the directory). §8.3.2 corrected:
  the earlier "a client cannot create directories" was wrong — creation just isn't a dedicated
  command, it is the server's response to DIR + upload.

*(Caveat: the `client/pygame/` build above and its findings were produced by the spec author,
who carries the codebase in their head — so it is a contaminated test. Its value is real but
weaker than an independent build. See the clean-room run below.)*

## Independent clean-room run

To remove author contamination, `docs/spec/` (README + §§1–8 + appendices only — no
companion docs, no source) was copied to an isolated directory and handed to a **fresh agent
with no repository access and no knowledge of this project**. It built a Tier-1 client from
the spec alone and tested it live against `docker.lan:6400`. The procedure is
[CLEANROOM.md](CLEANROOM.md); the spec version under test was commit `52481d3`.

**Result: it worked.** The fresh reader connected, identified, logged in, browsed the
directory, opened entries, and rendered frames — transport (§2) and session (§3) matched the
server with *no* surprises, and none of the author-found issues above recurred (those fixes
held). It surfaced eight genuine gaps the author had missed, all folded into the spec this
pass:

- **§4.1** — the "arguments MUST be ASCII decimal digits" rule was too broad; `GOTO` (`L`)
  takes a **keyword** (case-insensitive), not digits.
- **§7.4** — entry types are **compound** (`<base>[<size>][+]`, e.g. `T2+`), not the flat
  list shown; dispatch is on the base letter, and `+` does not change the select action.
- **§4.4/§4.5** — `A` (ACCOUNT) returns a **10-byte ASCII credit balance**, not a §6 frame.
- **§4.5/§6.5** — `N` (MORE) returns a bare `$41` ACK at the last frame (not the directory),
  and a frame's bit-7 "more" flag is a **hint, not a guarantee** (a `T+` splash sets it with
  no further frames); page with `D` (no arg) and drive off the actual response.
- **§6.3/§6.4** — a **control byte inside a `$07` run** repeats the *control action*, not a
  glyph (the template's `$07 $0D $05` = six CRs); the spec had contradicted its own appendix.
- **§7.7** — Part 2's footer is **two** lines (rows 22–23), not one.
- **§7.6** — paging index stated: send `D` + the count of visible entries; an out-of-range
  index returns the `(EMPTY)` placeholder.
- **§2.9** — the ACK packet's fixed 6-byte format is now in prose, not only in the §2.7
  example.

Two of these the author had earlier *mis-classified as server-side quirks*; reading the
server handlers confirmed they are intended behaviour and the spec was wrong (ACCOUNT returns
credit; `A`-vs-frame). Non-issues: the §5.4 pixel-exact-font MUST vs. a text-mode render (a
test-harness artifact, not a spec defect), and Part 3 field-definitions (never exercised
live, so unverified rather than wrong).

## Second clean-room run (patched spec + visual client)

A second isolated agent built from the patched spec (commit `1504dde`), with a two-stage
brief: Stage 1 a text-mode Tier-1 client, then **Stage 2 a graphical client** to surface UX
gaps the text-mode run could not. **Regression held: none of the eight run-1 findings
recurred** — several are now cited as working. New items, all folded in:

Protocol:
- **§7.2** — the six-part directory stream's text is **plain ASCII**, not PETSCII-shifted like
  the MOTD (§3.4); a client must not apply the shift to directory text.
- **§7.2** — Part-5 column headers are **response-specific** (MAIL sends `SENDER,DATE,STATUS`,
  not the top directory's five); read them from each response, don't hard-code.
- **§7.6** — a paged listing signals "more pages" with a trailing synthetic `MORE >>>>` entry
  (outside the §7.4 type grammar).
- **README** — a stale banner still said "Skeleton (Phase 2), stubs until Phase 3"; corrected.

Display / UX (Stage 2, confirmed with the maintainer):
- **§7.7** — the directory **colour scheme** was unspecified and both the clean-room and the
  author's earlier §7.7 had it wrong. Correct scheme: breadcrumb, footer, and entries default
  to **blue**; the **first entry is always red**; a selection highlight is a bar in the
  entry's own colour (blue, or red on the first entry) with **white text**. Parts 2/4/6 carry
  no colour codes — the client applies these.
- **§7.7** — the selected **column header** (PRICE/AUTHOR…) must be *displayed* above the
  values; the spec previously described showing the values but not the header (a spec
  omission, not a client error).
- **§4.7** — the **duckshoot** appearance is now specified for clients that reproduce it:
  white-on-black command words, the selection centred and drawn inverse, scrolled left/right.

## Third clean-room run (Tier 2 + visual)

A third isolated agent built a **Tier 1 + Tier 2** client (mail, downloads, LIFE/VOTE/BUY),
text-mode then visual, with full write access to the dev server. Session (§3) was flawless and
the run-1/2 fixes held. New findings, folded in — protocol:

- **§7.2** — the directory stream is **not** pure ASCII after all: Part 4 can carry an inline
  `$1C` (red) control for the `MAIL` marker. The last round's "plain ASCII" claim was
  over-corrected.
- **§6.1** — a frame may have **no `$00`** and end only at EOS (the welcome frame does);
  the "`$00` and EOS coincide" claim was false.
- **§4.4 / §8.6** — **VOTE (`V`) and LIFE (`X`) are distinct commands**; the spec had
  conflated LIFE into `V`. `X` is the **LIFE** command (extend an entry's life, by index +
  amount); it is **not** BUY — "buying" (download/activate/pay) is the `D`+index select flow,
  not a separate command. Both `V` and `X` target the highlighted entry **by index**.
- **§8.7** — mail *send* was filed under Tier 3, contradicting §1.4/§8.2 (Tier 2); reconciled.
- **§8.3.1** — the `$40`/`$41` proceed/abort packet bytes were never shown; added. (Also noted
  that dev-server programs may return a placeholder frame instead of the 8-byte header.)
- **§4.5** — blessed the structural heuristic for the genuinely-ambiguous `D`-no-arg / `N`
  case (bare-ACK vs frame vs directory), which the "command+mode, not bytes" rule can't cover.
- **§3.8** — LEAVE sends a **goodbye frame** that a client must render before the close.

Display / UX — the visual client (and a maintainer-supplied C64 reference screenshot) drove a
precise §7.7 rewrite to the **canonical C64 directory layout**: the breadcrumb aligns with the
entry columns (Part 4 carries the padding), the page number shows **only for the selected
entry**, the selected column header sits in the right column, the advert is centred,
and the selection highlight is an explicitly **client-drawn full-width bar** in the entry's
colour (red first / blue rest) with white text — the server sends nothing about selection.

Between runs 3 and 4 the maintainer also corrected two commands directly (verified in the
server): `X` is **LIFE** (extend), not BUY — BUY is a duckshoot command that maps to `D`+index;
and `V`/`X` both target the highlighted entry **by index** (VOTE = index + score, LIFE = index +
amount), which the spec had omitted.

## Fourth clean-room run (Tier 3)

A fourth isolated agent built a full **Tier 3** client — content upload, a minimal frame
editor, and Partyline — text-mode then visual, with dev-server write access. Everything worked
end-to-end (an uploaded page appeared in the Jungle; Partyline chat + teardown succeeded). New
findings, folded in:

- **§4.4 vs §4.5** — the sharpest internal contradiction found: §4.4's table glossed `L`
  (GOTO) as "DIR or FRAME", but §4.5 (authoritative) and the live server make it **always a
  directory** — the directory containing the target. §4.4 corrected to DIR.
- **§8.3.2** — a content upload commits to the client's **current directory** (verified:
  `_complete_content_upload` adds to `current_page.children`), needs write permission and space,
  and is **not** a fixed "Jungle root". A client must navigate to the target directory first.
- **§4.5** — ACCOUNT's 10-byte reply is delivered as a **normal DAT stream + EOS**, not a bare
  ACK.
- **§4.3** — a native-identified client **always** gets the `@` prefix on `I`/mail-send replies
  and **must strip it** (or field-shift by one byte); the old "not sent to non-leading-ack
  clients" wording was misleading.
- **§8.5** — the Partyline `L` link is often **nested** inside a `PARTYLINE` directory (dispatch
  on the type letter, not the title); the default room may display as `Lobby` (cosmetic).

The UX findings were all presentation choices the spec deliberately leaves open (button bar vs
duckshoot, the highlight modelled as a flag distinct from reverse video, editor form, Partyline
chrome) — the client made reasonable ones and hit no new display gaps.

## Fifth clean-room run (Tier 3, full)

A fifth isolated agent built a full **Tier 3** client (browse, subsystems, upload, editor,
Partyline) text-mode then visual, against the live server. Everything worked end-to-end,
including directory creation via DIR-on-a-plain-entry and a materialising upload. Most findings
**confirmed** the spec was already correct (program-header-vs-placeholder fallback, structural
bare-ACK vs stream detection, ACCOUNT as a DAT stream, the native `@` prefix, VOTE/LIFE by
index, the latent-directory creation model). The genuine gaps folded in:

- **§3.2 (F1)** — the twelve `$20` handshake bytes are written **one at a time, ~100 ms apart**
  (verified in the server), so a single read catches only a few. Clarified: treat the run as
  opaque, never gate on the count or expect all twelve in one read.
- **§7.2 (F3)** — Part 2 (footer) has **no `$00` terminator of its own**: it is always two
  `$0D`-terminated lines, and the next `$00` belongs to Part 3. Consuming a "Part-2 terminator"
  shifts every later part by one byte. Added a normative boundary note.
- **§7.2 (F4)** — Part 4 carries **one or two** `$0D`-separated breadcrumb lines (plus an inline
  `$1C MAIL` marker) inside its single `$00` part; the table called it a singular "Path line".
- **§8.3.2 (F8)** — the per-frame `@`-accept is an ordinary DAT and **MUST be ACKed before the
  finish command**; without the ACK the finish read times out and the upload silently fails.
- **§8.5 (F6)** — the 8-byte Partyline link header is a no-EOS DAT that **must be ACKed** before
  the server sends the `01 01 01` preamble; the "hang" is a missing ACK, not a protocol error.
- **§8.5 (F7)** — on entry the server also pushes an **unprompted who-listing** after the join
  broadcast; a client renders whatever arrives rather than assuming only the one line.
- **§4.4/§4.7/§A.7 (F2/F20)** — bare `P` (**FINISH**) returns the **current** directory, not
  "home"; it reaches the root only right after login (current dir = root). To ascend, use `B`
  (BACK). The §A.7 trace comment was clarified accordingly.

**Layout corrections (maintainer screenshots).** Directory placement errors, the run-5 answer to
the open geometry finding **F13**. §7.3/§7.7/§A.6 carry the authoritative numbers; this entry
records only *why* they were wrong and how they were settled.

- **Vertical:** the selected column header (`PRICE`) sat one row too high — it belongs at
  **row 8**, level with breadcrumb line 2 (`100 WELCOME`).
- **Horizontal:** the entry rows and the right-hand pane were misplaced. This took two passes to
  get right, and the reason is instructive: the first pass shifted the spec's *absolute* column
  numbers to match a clean-room client, when that client's real fault was that **its own box**
  was drawn a column off. Correcting the spec to the client compounded the error rather than
  fixing it.

  It was settled by **rendering the §A.6 template and reading the actual column indices** — the
  box occupies `[0, 30, 39]` (left border, divider, right border). Content therefore sits at the
  **box interior**: entry rows from **column 1**, type at **column 25**, right-pane header and
  values from **column 31**.

  **Lesson (now baked into §7.7):** the layout is defined **relative to the box**, not as
  free-floating column numbers, so a client with a mispositioned box can no longer drag the spec
  out of alignment. Verified by a per-column ink census on the rendered screen rather than by eye.

The remaining run-5 findings (F5, F9–F12, F14–F19) were confirmations or UX choices the spec
deliberately leaves open.

## Sixth clean-room run (Tier 3, full) — the corrections landed

A sixth isolated agent built the full Tier-3 client against the live server and reported the
spec **buildable end-to-end**: every Tier 1–3 wire flow worked (login, navigation, frame/RLE,
mail read/send, download, VOTE/LIFE/UCAT/ID-lookup, content upload, directory creation,
Partyline). The run-5 fixes held — the byte boundaries, ACK timing, and bare-`P` semantics were
all confirmed correct (findings P5–P10), and the folded-in full-directory behaviour (P2) and
`@`-prefix (P6) matched. What remained were a protocol clarification and — from the maintainer's
review of the screenshots — several **client-obligation / command-surfacing** gaps the spec had
left too loose:

- **§4.4 (P1)** — GOTO wording refined: for a **leaf** target it returns the *containing*
  directory; for a **directory-typed** target it returns that directory **opened** (its own
  children). Either way, parse the reply as a §7 directory and take breadcrumb/selection from
  it — do not compute the parent locally.
- **§8.3.2 (P2 / maintainer)** — a **full** directory (11 entries) silently discards the upload
  with **no** error; the client **MUST** check the target has room *before* offering/attempting
  the upload and refuse if full, rather than run a throw-away exchange.
- **§8.3.2 (maintainer)** — the upload UI **MUST** prompt for the entry **type** (`T` text /
  `P` program) **and price** (and title, lifetime); the run's client collected neither, so it
  could not upload software or set a price.
- **§7.7 (maintainer)** — cycling the right-hand column through the Part-5 set is now
  **normative** (reference keys **`F7`/`F8`**); a client that pins the pane to one column
  (e.g. always `PRICE`) does not conform.
- **§4.7 (maintainer)** — the **welcome frame** is an entry point: the client **MUST** surface
  **`DIR`** there (it goes on the wire as a bare `P` and returns the root), not only
  `MORE`/`FINISH`. Confirmed against `docs/PROTOCOL.md` (bare `P` is sent "by DIR duckshoot and
  on terminal entry"; the online **Directory Duckshoot** includes `DIR`).
- **§4.6 (maintainer)** — prefer **one** primary command surface; two competing full command
  bars (a duckshoot *and* a duplicate button row) are confusing. Show the context-appropriate
  set.
- **§7.7 (maintainer)** — the selection **highlight** was botched again via per-cell
  reverse-video (a broken striped row, not a solid bar). Added an explicit "don't fake it with
  reverse-video — fill the whole row's background, draw white glyphs over it" note. This is an
  **implementation** error each time (the spec was already unambiguous), now guarded against.

The under-specified decode points the agent flagged (P3 frame-vs-directory discriminator, P4
bare-ACK-by-timeout) are inherent to a protocol with no in-band type/length markers; the agent's
structural + short-timeout heuristics worked, and the spec already prescribes them (§4.5/§4.2).

## Seventh clean-room run — **Binding B** (Tier 3, Electron)

The first clean-room validation of the **JSON API**. Isolated set: `api/README.md` plus the
shared model sections and the appendix (§§1, 4–8, 99) — `02-transport` and `03-session` withheld
as Binding-A wire detail. Server: an API-only listener with **no static file serving**, so the
builder could not fetch the reference client (`run_api_only.py`; `run_api_dev.py` serves
`client/web` on the same origin and would have voided the run). Account `TEST`, a normal GOLD
account, not an administrator — so the permission rules were actually exercised.

Result: a full Tier-3 Electron client, 22 screenshots, **41 findings**. Everything in Tiers 1–3
was reached except the items it listed as unverifiable (below). All findings are folded in.

**Server faults it found — all measured, not inferred:**

- **The `cells` encoder silently dropped screen code `$5F`.** Found by submitting a real frame's
  `cells` back through `mail.send` and **diffing the grids**: 14 of 960 cells differed, every one
  glyph 95 → 32 (space), with colour, background and reverse all intact. `$5F` sits between the
  `$40`–`$5D` graphics run and the `$60`–`$7F` one, and `$5E` (pi) had its own case, so it fell
  through to a default. Exactly one screen code of 128 was wrong — and it falsified §5.4's claim
  that "anything Binding A can display, Binding B can now author", breaking §1.8 in the direction
  the documents do *not* worry about. The inverse is now total, and checked as such.
- **`UCAT` returned the session's current listing** — the mailbox, if you had just opened mail.
  Binding A was never affected: `_render_ucat` builds the listing as *bytes* and never sets
  `current_page`, because a user catalogue is not a page in the content tree. Binding B discarded
  those bytes and serialized model state. UCAT is a **synthetic** listing and now has its own
  serializer. The general lesson is recorded in the code: any command whose reply is not "the
  session's current page" needs one.
- **An unknown `goto` target returned the current listing with no error** — the silent no-op this
  binding explicitly rejects for `vote`/`life`. Now `not_found`.
- **`mailWaiting` was never emitted**, so the unread-mail marker could only be derived by opening
  the mailbox — defeating a marker that exists to tell you about mail you have *not* opened. Now
  answered from the mailbox file with no session side-effects.
- Smaller: `mail.read` with an out-of-range index returned a directory instead of an error;
  mail entry `page` was a string where every other listing sends an integer; `advert` could be a
  zero-length array where §7.2 requires exactly two lines.

**Specification faults it found:**

- **§4.7 declared the vocabulary "closed and exhaustive" while leaving `ALL`, `LOAD` and `ABORT`
  undefined.** They had duckshoot cells and §4.8 context rows but no entry in §4.7's tables, so
  the builder had to invent all three — the precise failure §4.7 exists to prevent. Now defined,
  with a ⚠ that closing a vocabulary obliges the section to define everything it closes over.
- **The api document was wrong about its own client's obligations.** §7 said "no PETSCII/RLE
  logic in the client; the server did it" — true of server content, false of the **five** required
  client assets (§A.6, §A.8–§A.11), which are raw §6 frames. The builder implemented the full §6.3
  loop and verified it against the renders printed in §A.9/§A.10/§A.11 *before* touching the
  server. Called "the single biggest thing this document gets wrong".
- **`page` is scoped to the current listing, not a global address** — unstated, and it fails as a
  plausible `not_found`. Called "the single most consequential thing the API spec does not say".
- **§7.7 contradicted itself on the selection bar**: "columns 1–29 and 31–38" in one normative box
  and "all 40 columns" in the next. The first is correct; the second was describing the
  *technique* and has been reworded.
- **The duckshoot's geometry never added up**: seven 6-character cells is 42 columns against a
  40-column grid, and the visible cell count was only implied by a worked example. Both now
  stated — the row starts one column left and the outer cells clip, which is also why the centre
  cell lands dead centre.
- **The duckshoot loop length was ambiguous** (eleven displayed vs seventeen reachable); an
  eleven-long loop would make `VOTE` unreachable, which §4.9.4 forbids. Now stated as seventeen.
- Also folded in: the more-pages flag *may* choose the command row even though it must not drive
  paging (§4.5/§6.5 apply to paging, not to row selection); `SEND`/`FINISH` are a user-facing
  requirement that Binding B satisfies client-side; Partyline renders in the lowercase set;
  the `MAIL` marker's column; `HELP` returns by "press any key" rather than `FINISH`; and the
  `account`, `goodbye`, `context` and `selected` fields the binding was carrying undocumented.

**What it could not verify, and why** — recorded rather than glossed:

| Obligation | Why |
|---|---|
| A content upload succeeding | `permission_denied` on every directory tried; only the refusal path is proven |
| The `directory_full` error | The full directory also answered `permission_denied`, so the two are indistinguishable from outside |
| Latent-directory creation by `DIR` | `enter` on a `+`-less entry returned the listing unchanged |
| Directory paging | No listing on the test server exceeds 11 entries, so `hasMore` was never true |
| The paid half of the `BUY`/`SHOW` gate | No content on the server carries a price |
| Program **upload** | Behind the same `permission_denied`; program *download* works |

**All six were resolved after the run, and five were test-data gaps rather than faults:**

- The three write obligations were one question. `_can_upload_here` is correct — owner, or
  admin/editor, or an inherited `open_upload` — but **`open_upload` was set on no directory in
  the content tree**, and The Jungle's author is `JUNGLE`, not a real account, so neither branch
  could fire. A code rule with no data to trigger it. With The Jungle opened, all three verified:
  an upload lands and appears in the refreshed listing; the twelfth entry is refused with
  `directory_full`; and `DIR` on a `+`-less entry opens a new empty directory, which is §7.4's
  hierarchy-building mechanism.
- Paging needed a listing longer than 11 — but see the ninth entry below: the premise was wrong,
  and authored directories do not paginate at all.
- The price gate was a **misreading, not missing data**. The paid page existed and cost £2.50 —
  it showed blank because the test account had **already bought it**, and a purchased page
  correctly has no price. Only the free half of the table was ever reachable. With an unbought
  paid page the whole cycle checks out: the price appears right-justified in the PRICE column,
  opening it deducts the credit, and the price then blanks because the page is owned.

The fixtures are now listed in [CLEANROOM.md](CLEANROOM.md) — content is not tracked in git, so
they must be set up per server or the next run hits the same walls and reports them as faults.

While opening The Jungle, `open_upload` gained a proper inheritance model: it flows down, a child
may set it explicitly to `false` to stop that, and an owner is never locked out of their own
directory by an inherited `false`. That needed three changes, one of them latent and nasty — the
tree-save path wrote the flag back only when truthy, so saving a directory would have **dropped a
child's opt-out and silently reopened it**.

## Eighth clean-room run — Binding B again, on the corrected spec

A second isolated Tier-3 Electron build, on the spec as corrected by the seventh run, with the
fixture tree in place so nothing was out of reach. **44 findings.** The brief added one
instruction — *measure rather than infer* — and it changed the character of the results: this run
diffed grids, swept colour spaces and counted cells rather than reasoning about them.

**It cleared the previous run's headline fault, independently.** A grid exercising all 256 glyph
codes in **both** character sets, again with reverse video, plus a 16×16 foreground/background
sweep, uploaded and diffed over 960 cells: **glyphs 0 mismatches, reverse video 0, foreground 0**.
The `$5F` hole is gone. Their §6 decoder also agreed with the server on **14,400 of 14,400** cells,
and `raw` round-tripped byte-identically.

**Three of the four worst findings were regressions from the seventh run's own fixes** — which is
the honest lesson of this run:

- **`dir.more` stranded the session.** Added to give `hasMore` something to act on; paging past
  the last page returned a listing with **zero entries**, which then *became* the session's
  current listing. Because `page` is listing-scoped, every subsequent `open`/`enter`/`vote` then
  failed with a plausible `not_found` until the user escaped with `goto`. It also broke §7.3's
  **MUST** that an empty directory still carries one placeholder row. Both fixed: paging is
  clamped at both ends, and a listing is never serialized empty.
- **`goto` reported "no such page" for pages that exist.** The seventh run's fix for silent
  GOTO failure searched only the **visible** eleven entries, so any entry on page 2 or later
  looked missing — while REST fetched it perfectly well, so the two lookups disagreed. Now the
  whole listing is searched and the reply pages to the target.
- **The API document told clients to page with a `MORE` command**, in a context where §4.8 says
  there is no `MORE` and §4.7 declares the vocabulary closed. The builder resolved it better than
  the original: page when the **selection moves past the last entry**, mirroring the gesture
  Binding A uses on its synthetic pagination row — no word added to a closed vocabulary. Adopted,
  and §4.8 now says so. They also spotted that paging had **no reverse**, which cost *n* round
  trips to go back one page; `dir.back` added. **Both commands were later removed** — see below:
  the model has no paging, so both were invented vocabulary.

**Other faults, all measured:**

- `finish` and `dir` returned a **frame** after `mail.read`, wedging the session — only `back`
  recovered. `dir` is documented to always reply `directory`.
- `leave` never closed the socket: the session stayed fully usable, so a client waiting for the
  close to complete logout hangs. It cost the builder a two-minute timeout to notice.
- `life` validated nothing — no `days`, or a negative `days` on a page the user does not own,
  both returned `ack`, though §8.6 restricts shortening a page's life to its owner.
- The five-recipient cap and `upload`'s "required" `price`/`life` were client-side only.
- A stale build log in the API document still described an auto-directory after `ready` that §2
  forbids and the server has never sent.

**The one finding that was not a bug, and is the more interesting result.** Per-cell `bg` does not
survive a `cells` round-trip — 240 mismatches in the colour sweep. The builder's diagnosis is
right and better than the obvious one: the C64 has a single screen background, so §6 has nowhere
to put a per-cell value and **Binding A cannot express one either**. §1.8 is intact; what is wrong
is the *schema*, which carries a writable-looking `bg` on all 960 cells and silently discards it —
the §8.3.2 silent-failure pattern living in a data shape rather than in code. Now documented as
frame-level, with an editor obligation not to offer per-cell background painting.

**One report did not reproduce.** The Partyline who-listing was said to arrive twice on entry;
measured against the server it is pushed once. Recorded as probably client-side rather than
"fixed", since changing working code to chase an unreproducible symptom is how faults get
introduced.

## Root-cause correction: directories do not paginate

Three findings across both Binding-B runs (F15, F26, F35) concerned directory paging, and the
corrections made in response made things worse — culminating in `dir.more`/`dir.back`, two
commands with no Binding-A counterpart. The premise underneath all of it was wrong, and was
corrected by the project owner from knowledge of the original service.

**An authored directory shows 11 entries and does not paginate.** Overflow is *authored*: the
owner adds an ordinary `D` entry, conventionally titled `MORE`, whose sub-directory holds the
next batch, and the user enters it with DIR like any other. Three independent confirmations:

1. **The C64 client has no paging state.** No page offset, no scroll counter — nothing. A client
   that cannot remember which page it is on cannot page.
2. **§8.3.2's 11-entry upload cap only makes sense this way.** If the server paginated, refusing
   a twelfth upload would be pointless — it would spill onto page 2. The cap *is* the display
   limit, and the `MORE` entry is the user's answer to it.
3. **The manual quote was misread.** "A dummy page; cannot be shown. Use DIR to access the
   directory beneath" describes the **`D` entry type** — precisely the authored MORE entry. It
   was cited in `docs/PROTOCOL.md` as evidence for automatic pagination, which is the opposite
   of what it says. That section also claimed "12 entries per page" where the server uses 11 —
   the usual signature of an assumed passage rather than a verified one.

**Generated listings are the exception**, and the distinction is principled: the mailbox and UCAT
are assembled by the server, so their owner *cannot* author a MORE entry into them. Those, and
only those, carry a synthetic MORE row — which the client selects like any other entry, sending
an index one past the real ones. No paging command, and no client-side page state, in either
binding.

**What this cost.** §7.6 described a server-side pager that never existed; two clean-room builders
read it, found the server did not behave that way, and reported the discrepancy accurately. The
corrections then built machinery on the false premise — including inventing vocabulary inside a
specification whose §4.7 forbids exactly that. The clean rooms did their job; the spec was wrong
at the root, and no amount of building against it would have revealed that. It took someone who
knew the original service.

The lesson for §1.5.1's list: a **plausible edit** can also be made by the specification's own
author, in prose, years before anyone builds against it — and it will then be faithfully
reproduced by every reader.

## Conclusion

The spec explains the observed behaviour of the server and both reference clients across
transport, session, commands, display, frames, directories, and subsystems, with the
contradictions above resolved in the server's favour. **Five independent clean-room readers**
built working clients from this document alone — Tier 1 twice, Tier 2 once, and Tier 3 twice —
the visual stages confirming the display down to the canonical directory layout. By the sixth
run the protocol core was clean end-to-end; the remaining fixes were **client-obligation**
tightenings (surface `DIR` on the welcome screen, prompt for upload type/price, make column
cycling and the full-directory check mandatory) and one recurring **implementation** pitfall
(the reverse-video selection bar) now explicitly guarded — not gaps in the wire protocol.

**Binding B has now been clean-room validated too.** The seventh run built a full Tier-3 Electron
client from `api/README.md` and the model sections alone, and found four server faults and six
specification faults — including one, the `$5F` encoder hole, that no amount of reading would have
caught and that falsified a claim the specification made about itself. Both bindings have now been
built from the document by someone who had only the document.

The eighth run's lesson is narrower and sharper than the seventh's: **the corrections were the
most dangerous code in the project.** Three of its four worst findings were introduced by the
previous round of fixes — each one plausible, reviewed, and shipped without a test that would
have caught it. The protocol core, by contrast, has now been measured cell-by-cell and
byte-by-byte by an independent implementation and holds up exactly as written.