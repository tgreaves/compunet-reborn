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

## Conclusion

The spec explains the observed behaviour of the server and both reference clients across
transport, session, commands, display, frames, directories, and subsystems, with the
contradictions above resolved in the server's favour. An **independent** reader built a
working Tier-1 client from this document alone (see the clean-room run above), which is the
honest evidence that the spec is buildable; the residual gaps are confined to optional
subsystems and client-local presentation.
