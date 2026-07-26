# Conformance self-audit

> Part of the [Compunet Client Specification](README.md). A checklist to run **against a finished
> client**, to answer a question the rest of the spec cannot: *did you build the **right** thing?*
>
> This exists because the usual tests don't catch the usual failure. A client can be complete,
> correct on the wire, and pass every clean-room build, while still quietly diverging from
> Compunet — see §1.5.1 (*load-bearing details* and the **plausible edit**). Those divergences
> produce a **working** client, so nothing errors. They are caught only by a deliberate check.

## How to use it

Go through it with the client running. Each item is answerable by **looking**, not by reasoning
about the code — that matters, because the reasoning is what went wrong in the first place. Items
marked **⚠** are the ones known to have been got wrong in practice.

---

## A. Command set (the most common divergence)

- [ ] **⚠ Exactly the §4.7 vocabulary — no additions.** List every command your client offers.
      Is each one in §4.7? An invented command (a "join", "home" or "refresh" shortcut) is a
      conformance failure even if it is useful: it has no counterpart in Binding A (§1.8).
- [ ] **⚠ No omissions on "redundancy" grounds.** Is every §4.7 command reachable? Two commands
      sharing wire bytes are still two commands (§4.7 shared-encoding rule) — `BUY` is not a
      synonym for `SHOW`.
- [ ] **⚠ Availability matches §4.8 per context.** For each of welcome / directory / frame /
      mail / mail message / upload / editor / Partyline: does the offered set match the table?
      In particular `MORE`/`FINISH` must **not** be offered on a directory, and the normal
      command set must **not** be offered inside Partyline.
- [ ] **Selection-dependent commands disabled without a selection** — `SHOW`, `DIR`, `VOTE`,
      `LIFE`, `BUY` on an empty listing or an `(EMPTY)`/`(NO MAIL)` placeholder (§4.8).
- [ ] **Keyboard/shortcut paths obey the same table.** A shortcut must not reach a command the
      context forbids.
- [ ] **If you implemented a duckshoot, it matches §4.9** — the *row* scrolls and the centre is
      the selection (not a highlight moving along a fixed row); it sits outside the 40×24 grid;
      contents are the context's set in the §4.8 priority order, truncated **from the end**; and
      the row **wraps** at both ends rather than clamping.
- [ ] **⚠ A short row fills every cell by repeating.** Look at mail (six commands, seven cells):
      it must read `ID EDITR DONE [SEND] SHOW MORE ID` — `ID` twice, by design (§4.9.4). A row
      **blank on the left** means the repeat was suppressed.
- [ ] **⚠ No invented row for the disconnected state.** Offline, the editor is reached by a host
      affordance (menu/button), not by a command row holding a lone `EDITR` (§8.4).
- [ ] **If you show two contexts at once (§4.10):** each has its **own** command row; focus is
      **visible**; the unfocused one is **inert** (type into it — nothing should happen); and
      neither can obscure the other. Then check the whole command set is unchanged from a
      one-context client — simultaneous visibility must grant nothing extra (§1.8).
- [ ] **Partyline replaces rather than tiles** (§4.10.1) — it takes over the Compunet surface and
      restores it on exit, as the C64's chat program does. A Partyline pane sitting beside a live
      directory, with an empty command row, is the wrong shape.
- [ ] **`UPLD`/`SEND` put the editor in front of the user** (§4.10.2) and keep it there until the
      server responds; on refusal focus **stays** with the editor and the buffer is intact.
- [ ] **⚠ Rows return where you left them** (§4.9.4). From a directory, centre `SHOW`, run it,
      then `FINISH`. Is the row still on `SHOW`? Resetting to `HELP` is the known failure.
      Check mail and the editor keep their **own** positions, not one shared one.
- [ ] **⚠ Viewed pages land in the editor buffer** (§8.4.2), without moving the user's current
      page or stealing focus — and a **full** buffer is reported, not silently dropped.
- [ ] **⚠ Capture is verbatim** (§8.4.2). View a page with **several colours** and some
      **graphics characters**, then look at it in the editor: it must be identical, colour for
      colour. A monochrome or text-only rendering means the page model is lines, not cells.
- [ ] **⚠ An editor page is the full 40×24** — no row reserved for a status line or page
      counter (§8.4.2). Capture a page that uses all 24 rows and check the last one survives.
- [ ] **Unedited captured pages re-upload unchanged** — as their original bytes, not re-encoded
      (§8.4.2). Edit one character and the client must switch to sending the grid.

## B. Behaviour that shares an encoding

- [ ] **⚠ `SHOW` refuses a paid page** with `PLEASE USE BUY`, sending nothing (§8.6.4).
- [ ] **⚠ `BUY` confirms** with `BUY FOR {price} - SURE?` and sends only on acceptance (§8.6.4).
- [ ] **`DIR` vs `SHOW`** — `DIR` enters an entry as a directory, `SHOW` only reads frames;
      on a `T+` entry the two do different things (§4.7).
- [ ] **`FINISH` returns the current directory**, not "home"; `BACK` ascends (§4.7).
- [ ] **⚠ `PUT` saves one page, `STORE` saves the buffer** (§8.4.1) — the editor's instance of
      the same trap; a single "save" is a merge.
- [ ] **⚠ The editor is a real context, not an upload form.** Is there a multi-page buffer with
      a current position, reachable via `LAST`/`NEXT`/`NEW`/`COPY`/`ERASE` (§8.4.1)? A title
      field and one text box is the known failure here.
- [ ] **Editor `HELP` shows §A.9**, not the §A.8 frame — they are different assets.
- [ ] **Editor row order ends `FREE`, `RETURN`, `DOS`** (§8.4.1) — storage order is not display
      order.
- [ ] **⚠ The editor opens with no session.** Close the connection (or don't make one) and reach
      it: compose, `PUT`, `STORE`, `GET`, `FREE`, `HELP` must all work offline (§8.4). Then
      reconnect — **is the buffer still there?** Clearing it on disconnect is the known failure.

## C. Display fidelity

- [ ] **⚠ Selection bar leaves the divider intact** — filled either side of column 30, not
      straight across (§7.7).
- [ ] **⚠ First entry is red, others blue**, independent of selection; the bar takes the entry's
      own colour with white text (§7.7).
- [ ] **⚠ Right-pane content rendered verbatim** from column 31 — the server's leading spaces and
      right-justification are the positioning; do not re-justify (§7.3).
- [ ] **Page number shown only on the selected row**, right-justified to column 6 (§7.7).
- [ ] **Column cycling works** through the whole Part-5 set, header and values together (§7.7).
- [ ] **Part-5 columns read from each response**, not hard-coded — mail's set differs from a
      content directory's (§7.2).
- [ ] **⚠ RLE counts are `1 + N`** (§6.4), and a control byte inside a `$07` run repeats the
      *action*, not the glyph.
- [ ] **Welcome frame persists after login** until the user acts; `DIR` reaches the root (§4.7).

## D. Silent-failure traps

The server does not report these; a client that ignores them looks fine and loses user data.

- [ ] **Upload into a full directory is refused by the client** (11 entries) rather than
      attempted — the server discards it with no error (§8.3.2).
- [ ] **Upload prompts for type *and* price** — omitting type makes program upload impossible
      (§8.3.2).
- [ ] **"The exchange completed" is not treated as success** — confirm the entry appears in the
      refreshed listing (§8.3.2).
- [ ] **⚠ Mail recipients are validated before sending** (§8.2.1). Send to a made-up ID: the
      client must refuse. The server accepts unknown recipients silently, so an unvalidated
      typo is mail that vanishes with no error.
- [ ] **⚠ No input uses `window.prompt()`/`confirm()`.** They are **not implemented in
      Electron** and throw, so any command relying on them (`ID`, `GOTO`, `VOTE`, `LIFE`, `BUY`)
      silently does nothing in a desktop build while working in a browser.
- [ ] **⚠ `SEND` and `ID` use DIFFERENT frames** — §A.11 (with `FROM`/`DATE`/`TIME`/`SUBJECT`/
      `TO`) and §A.10 (bare slots). They open identically, so reusing the `ID` frame for `SEND`
      looks right and drops the whole message header. Both show **five** slots.
- [ ] **`ID` results are `PRESS ANY KEY`**, not a command row, and any key returns to the
      mailbox (§8.2.1). IDs and found names **blue**; `*** NO SUCH USER ***` **black**.
- [ ] **⚠ `SHOW` in Courier downloads the WHOLE message** (§8.2) — every frame, as fast as the
      line allows, ending on `PRESS ANY KEY` with **no duckshoot**, and every frame captured
      into the editor so the mail can be read offline. A client that shows one frame and offers
      the mail row has implemented content paging instead, and it *looks* right: the first frame
      appears, the row is populated, nothing errors. Check the **editor buffer** afterwards —
      if only one page arrived, this is wrong.
- [ ] **⚠ `MORE` in Courier pages the MAILBOX** (§8.2), and there is no `MORE` while reading.
      If MORE opens the highlighted message, the client is sending `D` where it should send `M`.
- [ ] **⚠ `PRESS ANY KEY` is LEFT justified** (§4.8) — column 0, where the duckshoot starts.
      Centred text looks perfectly reasonable in isolation; the tell is the bottom row jumping
      sideways as you move between reading and choosing.
- [ ] **⚠ Multi-frame runs are PACED** (§4.7) — `ALL` and Courier's `SHOW` leave each frame up
      ~500 ms. Unpaced, the run completes in a single flash and the user sees only the last
      frame; count the pages in the **editor buffer** to see that the rest did arrive. This one
      cannot be caught by reading the code — the loop is correct either way.
- [ ] **⚠ `ALL` is not `MORE`** (§4.7) — `MORE` advances one frame, `ALL` runs to the end. If
      pressing `ALL` moves a single page, the client has issued one paging command instead of
      looping, collapsing two commands onto one.
- [ ] **Mail composition offers `SEND FINISH LAST NEXT EDITR`** (§8.2.2), with `SEND` adding
      **one** frame and `FINISH` completing the message — not one combined "send".
- [ ] **Re-entering mail starts on `SEND`** (§4.9.4) — the mail row resets on leaving Courier.
- [ ] **The mailbox breadcrumb shows `USER ID : <id>` and the real name** (§8.2), not a
      content-tree trail — and the mailbox has its **Part-1 header** like any directory.
- [ ] **⚠ Recipient names appear on the envelope** before `OKAY?` (§8.2.1) — an ID alone does
      not confirm the right person. Blue when found, black `*** NO SUCH USER ***` when not.
- [ ] **⚠ Composition shows the frame being sent**, not the envelope (§8.2.2). `SEND` adds the
      frame **on screen**, so choosing blind is the failure to look for.
- [ ] **⚠ A prompt must not hide what it is asking about.** `OKAY?` confirms the envelope, so the
      envelope has to stay visible behind it (§8.2.1). A centred modal over the screen fails this.
- [ ] **Mail confirmation names the recipients** — mail lands in *their* mailbox, not the
      sender's, so "sent" with no addressee reads as nothing having happened (§8.2.1).
- [ ] **The seven editing controls work** (§8.4.3): STOP stores, RUN restores, case change,
      f3/f4 line delete/insert, f5 auto-repeat, f6 colour, f7/f8 screen/border.
- [ ] **⚠ `DONE` after `ID` returns to the mailbox**, not out of Courier (§8.2.1). Sending `B`
      here unwinds one level too many.
- [ ] **⚠ `SEND`/`UPLD` work with an empty buffer** (§8.2.1) — address first, compose second.
      Refusing at step one is the known failure; the addressing must survive to the second
      attempt.

## E. Mechanical checks (automate these)

These are cheap to script and catch drift that reading cannot:

- [ ] **Command table vs implementation, both directions.** Diff the commands your client can
      send against §4.7/§4.8 (and, for Binding B, against the server's dispatch). *Zero* drift
      either way — implemented-but-undocumented is as much a defect as the reverse.
- [ ] **Context table vs UI state.** For each context, assert the enabled set equals §4.8's row.
      *(The reference client's implementation of both of the above is
      `server/tests/test_client_conformance.py` — it parses the two sections out of this
      specification, so the spec stays the authority rather than being copied into a test.)*
- [ ] **Geometry by pixel census, not by eye.** Sample the rendered screen per column to confirm
      borders, divider and content columns (§7.7) — the layout errors in this project's history
      were all invisible to casual inspection and obvious to a census.

---

## If something fails

Prefer "the spec is under-explained" over "the spec is wrong". Every divergence recorded in
[VALIDATION.md](VALIDATION.md) turned out to be a fact the spec stated **without its reason** —
so the fix is usually to add the reason (and a ⚠), not to change the requirement.
