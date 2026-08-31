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
      Also try a command that changes **nothing** — `SHOW` on a `D+` entry is inert (§4.7) and
      answers with the same listing. The row must not move: a client that restores its position
      only when the context *changes* still snaps back to `HELP` on every redraw within one.
      Check mail and the editor keep their **own** positions, not one shared one.
- [ ] **⚠ Viewed pages land in the editor buffer AND become the current page** (§8.4.2). Read a
      page, then look at the editor: it should be showing what you just read, not whatever was
      there before. It must **not** steal focus, and must not move the page during an edit in
      progress.
- [ ] **⚠ Capture is verbatim** (§8.4.2). View a page with **several colours** and some
      **graphics characters**, then look at it in the editor: it must be identical, colour for
      colour. A monochrome or text-only rendering means the page model is lines, not cells.
- [ ] **⚠ An editor page is the full 40×24** — no row reserved for a status line or page
      counter (§8.4.2). Capture a page that uses all 24 rows and check the last one survives.
- [ ] **⚠ The buffer survives restarting the client** (§8.4). Compose a page, close the client
      completely, reopen it: the page must be there, colours and all. This is the single most
      consequential editor check — the editor exists so work can be composed offline and uploaded
      later, and a buffer that dies with the window only delivers that within one session.
- [ ] **⚠ Corrupt stored pages do not prevent startup** (§8.4). Damage the stored data and
      reopen: the client must start with a blank page **and say the pages could not be read**.
      Silently starting blank is worse than crashing — the user assumes their work is still
      there.
- [ ] **⚠ A full buffer EVICTS the oldest page rather than refusing** (§8.4.2). Fill it past the
      limit and watch: capture must keep working, the oldest page must go, and the client must
      say so. A client that refuses looks safer and is wrong — on the original a long mail
      download never stalls. Check `NEW` and `COPY` behave the same way; enforcing the limit only
      on capture lets the user walk past it by hand.
- [ ] **The buffer holds at least 15 pages** (§8.4), ideally 50, and the limit is a setting with
      15 as its floor.
- [ ] **Unedited captured pages re-upload unchanged** — as their original bytes, not re-encoded
      (§8.4.2). Edit one character and the client must switch to sending the grid.
- [ ] **⚠ Graphics characters can be typed at all** (§8.4.3). Try to draw a box: `SHIFT`+letter
      must give a graphics glyph (screen codes `$41`–`$5A`), not a letter. A client that maps
      only letters and digits can compose **text pages and nothing else**, which is easy to miss
      because everything it *does* do works. If a bank is unreachable from the host's keyboard,
      a picker must cover it.
- [ ] **⚠ The pen colour can be set** (§8.4.3) — `CTRL`+`1`–`8` on the C64, `CTRL`+`4` giving
      cyan. Type a character, change the pen, type another: they must differ. A client that
      implements only the help frame's keys can produce **white text and nothing else**, which
      looks like a working editor until you try to author a coloured page.
- [ ] **⚠ Reverse video can be typed at all** (§8.4.3). `CTRL`+`9`, type, `CTRL`+`0`, type: the
      two runs must differ. Then check the **lifetime**, which is where this goes wrong — press
      `RETURN` and the mode must clear (§5.7), and type past column 40 with it on, where the wrap
      must **not** clear it. A client that renders reverse perfectly on pages it receives can
      still be unable to author a single reversed cell, and nothing on screen says so.
- [ ] **⚠ Any palette, picker or mode indicator follows the keys** (§8.4.3). Set the pen with
      `CTRL`+digit and watch the swatches; press f7/f8 with the target on screen or border; page
      with `LAST`/`NEXT`, which changes all three at once. An affordance that repaints only on its
      own click reports the previous state confidently, and the reverse toggle is worse than the
      palette here because `RETURN` changes the mode with no input the control can observe.
- [ ] **⚠ Changing the screen colour actually changes the screen** (§8.4.3). Press f7 and watch
      the whole 40×24 area, not the status line: if the model holds a background per cell, the
      page field and the cells will disagree and only newly typed cells change. f8 (border) is
      not affected, since there is only one border — so "border works, screen doesn't" is the
      signature of this bug.
- [ ] **⚠ The editor cursor blinks, and cannot become invisible** (§8.4.3). Two things to check
      separately, because each has its own mechanism and one can be present without the other:
      put the cursor on a cell whose colour **differs** from the drawing colour — it should
      **change colour** as it blinks, not merely invert. Then put it on a cell coloured the
      **same as the background** (type a character in the background's own colour): it must
      still be visible in **both** phases. A cursor that only inverts disappears there, and the
      disappearance is easy to miss because it looks like the cursor is simply "off".

## B. Behaviour that shares an encoding

- [ ] **⚠ `SHOW` refuses a paid page** with `PLEASE USE BUY`, sending nothing (§8.6.4).
- [ ] **⚠ `BUY` confirms** with `BUY FOR {price} - SURE?` and sends only on acceptance (§8.6.4).
- [ ] **⚠ EVERY downloadable type is charge-gated, text included** (§8.6.4). Put a priced entry
      of each base type your client handles — `T`, `P`, `S`, `L`, and `F`/`A` if you serve them —
      in a directory and select each one. Did every single one ask before charging? The reference
      Amiga client gated five of its six types for four releases: `T` went straight through, so a
      priced **text** page was fetched and billed silently. Text is the one that gets missed,
      because reading feels free. If you dispatch on the base type, the check belongs **before**
      the branch, not inside each arm.
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
- [ ] **⚠ `GET` reads a stored file to END OF FILE, not to the first `$00`** (§8.4.4, §6.3).
      `STORE` several pages, then `GET` the file back: do **all** of them return? A reader that
      applies §6.3's wire rule to a file loads **page 1 of N and reports success** — nothing
      errors, so this passes casual inspection. Check the boundary handling too: frames are
      separated by the terminator **immediately followed by** the next frame's flags byte, so a
      reader that assumes one byte between bodies parses everything after the first frame one byte
      out. **Round-tripping your own files does not test this** — write `$01` into a body and
      confirm the page truncates on load, or better, test against a file written by a real C64,
      which is the only place the `$01`→`$00` substitution shows up.

## C. Display fidelity

- [ ] **⚠ Selection bar leaves the divider intact** — filled either side of column 30, not
      straight across (§7.7).
- [ ] **⚠ First entry is red, others blue**, independent of selection; the bar takes the entry's
      own colour (§7.7).
- [ ] **⚠ The bar is reverse video, so its text is the SCREEN BACKGROUND colour — not white**
      (§7.7). Highlight a row and look at the characters *in* the bar: they should be the same
      light grey as the page behind the box, because reversing a cell knocks the glyph out in the
      background. White text means the client models the bar as a coloured background, which the
      hardware cannot do — and that model then leaks into anything else touching cell backgrounds
      (§8.4.3). Both look plausible; only one matches.
- [ ] **⚠ Right-pane content rendered verbatim** from column 31 — the server's leading spaces and
      right-justification are the positioning; do not re-justify (§7.3).
- [ ] **⚠ Footer / advert drawn verbatim from column 0, NOT centred** (§7.7). The original has no
      instruction that halves a value in either binary, so it cannot centre; authors position
      these lines with leading spaces. Centring re-centres already-padded text and shifts it
      right by a different amount on each line — which reads as "the advert is slightly off"
      rather than as a client bug.
- [ ] **Page number shown only on the selected row**, right-justified to column 6 (§7.7) — and
      **never for the `(EMPTY)` placeholder**, whose page and type columns are both blank (§7.3).
      A `0` there advertises a page that does not exist; a `T` announces a text page, in a listing
      whose whole message is that it holds nothing.
- [ ] **The highlight survives a return to the same listing** (§7.7) — read an entry, come back,
      and the bar is still on it. Easy to lose in a binding that re-sends the listing, where the
      obvious "reset selection on arrival" throws the user to the top every time they read
      anything.
- [ ] **The command row answers the keyboard as soon as the session starts** (§4.9.6), with no
      click needed. Check the *focus*, not the styling: a highlighted display with a login field
      still holding focus is still dead.
- [ ] **No spec section numbers in user-visible text.** `§8.3.2` in a dialog or status line means
      nothing to the person using the client and makes it read as a debug build. Cite the spec in
      source comments, where implementers will actually see it.
- [ ] **Column cycling works** through the whole Part-5 set, header and values together (§7.7).
- [ ] **Part-5 columns read from each response**, not hard-coded — mail's set differs from a
      content directory's (§7.2).
- [ ] **⚠ RLE counts are `1 + N`** (§6.4), and a control byte inside a `$07` run repeats the
      *action*, not the glyph.
- [ ] **A `$00` RLE operand ends the frame** (§6.4) — it is the terminator, not a zero count.
      Check this deliberately: reading `$06 $00` as "one space" is the natural implementation
      and it passes every test built from real content, because no encoder emits a zero count.
      It diverges only on hand-made bytes, and then your client draws a different screen from
      the C64, which stops at that byte. The spec said both things until recently; if you
      implemented from an older copy, this is the line to re-check.
- [ ] **The Part-1 header is bounded to rows 0–5** (§7.2, §7.7), and a header that tries to draw
      lower cannot reach the entry list. Directory headers may be **user-supplied**, so this is
      no longer only a question of trusting the operator: a header that runs long, clears the
      screen, or leaves the character set switched should cost you the header, not the page.
      Test with a deliberately broken one rather than assuming — the reference clients disagree
      here, and the failure is invisible until someone uploads the wrong file.
- [ ] **Welcome frame persists after login** until the user acts; `DIR` reaches the root (§4.7).
      And once anything replaces it, **it is gone** (§3.5) — it is sent once and no command
      brings it back. Check you have not offered a route to it: a "home" button that lands on
      the top directory instead is an invented command (§4.7), and one that appears to work by
      re-rendering a cached copy is describing your client, not Compunet.

## D. Silent-failure traps

The server does not report these; a client that ignores them looks fine and loses user data.

- [ ] **⚠ The packet `length` byte is advisory and wraps — never validate against it**
      (§2.4). It is one byte, so a payload over 250 cannot fit and it carries
      `(N + 5) mod 256`; a 4000-byte payload sends `length = $A5`. Derive the payload length
      from where the `$02` end marker fell. A receiver that rejects on a length mismatch
      breaks on every large transfer; a **sender** that builds the byte without truncating
      is worse — the reference server raised on any payload over 250 and dropped the
      connection mid-transfer, which the Amiga reported as "Fatal error: Comms problem".
      The CRC covers the truncated value, so both sides must truncate identically.
- [ ] **⚠ The download descriptor's bytes 4–7 are read per machine, not one way** (§8.3.1).
      Byte 0 selects: C64 takes the 16-bit size at **6–7** (4–5 being its load address), while
      Amiga and ST take a 32-bit **big-endian** size at **4–7**. Reading the C64 field on a 68k
      machine truncates to 16 bits *and* byte-swaps, so a 169,966-byte file reads as 61,079 —
      wrong, but not obviously so, and it only misbehaves above 64K. Both the spec and the
      reference server had this wrong until 2026-07-30. The mirror-image mistake on *upload*
      (sizing every body from 4–7) is documented in §8.3.2 and shipped once already: if you
      implement one direction from the other, you will reproduce one of the two.
- [ ] **A download is not complete because the client stopped receiving.** Verify the received
      length against the descriptor's size field, and treat a short transfer as a failure. A
      client that writes whatever arrived and reports success turns a desynchronised stream
      into a silently corrupt file — see the Amiga stale-response defect, where a download
      after other traffic wrote the *previous* command's response to disk and reported success.
- [ ] **An unrecognised machine type is an error, not a default.** If byte 0 is not one your
      client handles, refuse — do not fall through to "probably mine". Falling through means a
      desynchronised descriptor is accepted as valid and its garbage written to disk.
- [ ] **⚠ An unrecognised directory *base type* is inert, not fed somewhere unsafe** (§7.4,
      §7.4.1). The base-type set is open — beyond the six this client implements the service uses
      `F` (IFF picture) and the protocol also defines `A` (action), and a future producer may use
      more. On SHOW of a base you do not handle, do **nothing** (behave as for `D`): do not run
      it, do not write it, do not feed the bytes to your page renderer. The frozen C64 client
      fails this — it would garbage-render an `F` and runs an `A` as 6502 with no machine guard —
      which is exactly the behaviour a new client must **not** reproduce (its being era-accurate
      and feature-locked, §1.8, does not excuse yours).
- [ ] **⚠ A server REFUSES a base type it does not serve — it does not ignore it** (§7.4.1).
      Put an `A` (action) entry in a directory by hand and select it. Did the server answer with
      an error the client renders as a page, or did it send the entry's bytes as an ordinary
      frame? The second is the dangerous answer: the client dispatches on the TYPE LETTER, so it
      is already in its action handler expecting a download descriptor — it will read the frame's
      leading bytes as that descriptor and, on a C64, **execute what arrives**. "We never emit
      one" is not a guard; a hand-edited directory, an import or a migration can introduce one.
- [ ] **⚠ A server serving `F` (IFF) guards it per machine** (§7.4.1). An `F` is Amiga content
      and downloads through the very descriptor an Amiga `P` uses, so a client that cannot decode
      ILBM must be **refused the download**, not handed the bytes. The reference server refuses an
      `F` to the C64 with a message it paints as a page, and serves it to the Amiga and to
      Binding B (which decodes ILBM itself). If your server serves `F`, it owns this guard —
      the frozen C64 cannot refuse for itself.
- [ ] **⚠ A server gates the UPLOAD type too, on every path a user can reach** (§7.4.1, §8.3.2).
      Refusing to *serve* `A` is half a guard; a stored `A` is an executable waiting for the
      other half to be forgotten. Try uploading type `A` through **each** binding and terminal
      you offer — not just the one you were thinking about. This is reachable from an era
      client: the Amiga's publish requester takes the type as free text and routes `A` and `S`
      down the same file-upload path as `P` and `F`. The reference server gated its JSON binding
      only, for two releases, while its X.25 binding and its PETSCII terminal stored any letter
      verbatim — and this specification asserted the gate existed the whole time. Check each
      path yourself rather than trusting a shared-code claim; if a path's own transport is not
      shaped for a type, refusing it there is right (the reference terminal takes `T` and `P`
      only, because its XMODEM path re-wraps the file with a C64 load address and an IFF has
      none).
- [ ] **⚠ One writer, not one per surface** (§8.3.2). Upload the same page through every
      surface you offer and diff the stored entry, field by field. The reference server had
      the terminal carrying its own hand-copied writer, and the copies had drifted in four
      ways — one of them user-visible: a directory closed with `open_upload: false` stayed
      writable from the terminal while the C64 and the web client refused it. Duplicated
      write paths do not stay equal; the only reliable answer is that there is one of them.
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
- [ ] **⚠ Text replies land on the COMMAND ROW** (§4.8) — run `ACCNT`, and the editor's `FREE`.
      The answer must appear on the duckshoot line, not in a status bar or toast outside the
      40x24 screen, where the user is not looking and may never see it.
- [ ] **⚠ `PRESS ANY KEY` is LEFT justified** (§4.8) — column 0, where the duckshoot starts.
      Centred text looks perfectly reasonable in isolation; the tell is the bottom row jumping
      sideways as you move between reading and choosing.
- [ ] **⚠ The duckshoot inverts with the page** (§4.9.3). Look at the row over a **light**
      directory and over a **dark** page: the bar should swap between black and white, because
      its colour is derived from the background. A row that is always black-with-white-text is
      right on the directory and backwards on a dark page, and both look normal in isolation.
- [ ] **⚠ The duckshoot row starts at column 0** (§4.9.3) — cells at 0, 6, 12, 18, 24, 30, 36,
      so only the **rightmost** word is clipped. If the leftmost word is missing its first
      character, the client centred the 42-column overflow instead of starting at 0.
- [ ] **⚠ Multi-frame runs are PACED** (§4.7) — `ALL` and Courier's `SHOW` leave each frame up
      ~500 ms. Unpaced, the run completes in a single flash and the user sees only the last
      frame; count the pages in the **editor buffer** to see that the rest did arrive. This one
      cannot be caught by reading the code — the loop is correct either way.
- [ ] **If you offer a line speed (§5.5.1):** Fastest is the **default**; the duration comes
      from the frame's **bytes**, so a sparse page paints faster than a dense one (time two of
      each — equal times mean it is counting cells, and every RLE'd frame is mistimed); a
      keypress completes the frame; and the §4.7 run pacing **stands down** while it is on —
      a multi-frame download must not pay both. Check the **welcome** frame paces too: it is
      delivered with the session rather than as an ordinary frame (§3.5), so it takes a
      different path and is the one most likely to have been missed. Check the embedded
      **help** frame does **not** — it never crossed the line. And check **no command row is
      shown while a page arrives**: the original draws the row only when it is about to block for
      a key, so a row visible mid-paint is one the user cannot use.
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
