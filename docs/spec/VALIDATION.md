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
  BACK, GOTO, ACCNT, MAIL, UCAT, MORE, FINISH…) and its mapping to the wire commands, and
  clarifies that opening an entry (DIR/SHOW) uses `D`+index — **not** `P` (FINISH), which
  carries no index and only refreshes the current directory. (The client had wired DIR→`P`,
  so DIR did nothing on a highlighted entry.)

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
entry**, the selected column header sits at row 7 in the right column, the advert is centred,
and the selection highlight is an explicitly **client-drawn full-width bar** in the entry's
colour (red first / blue rest) with white text — the server sends nothing about selection.

## Conclusion

The spec explains the observed behaviour of the server and both reference clients across
transport, session, commands, display, frames, directories, and subsystems, with the
contradictions above resolved in the server's favour. **Three independent clean-room readers**
built working clients from this document alone — Tier 1 twice and Tier 2 once, the latter two
with visual stages that confirmed the display down to the canonical directory layout. Protocol
findings have shrunk to fine detail and the transport/session core has been clean across every
run; the remaining work is presentation precision and the optional Tier-3 subsystems.
