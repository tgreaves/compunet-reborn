# Amiga Client — Modern UX Proposal

Status: **proposal / not yet started.** This describes an optional modernisation of the
Amiga client's *presentation* layer. It does not change the wire protocol or the frame
content, and it is deliberately kept separate from the faithful reconstruction.

## 1. Why

The reconstructed client's UX is Kickstart 1.2/1.3-era raw Intuition: hand-built `Gadget`
structs with custom `Image` rendering, fixed windows at hardcoded coordinates, a
fixed 11-row directory grid with *invisible* click-rows, a hand-rolled busy-pointer
sprite, and synchronous blocking I/O. That was faithful to 1989, but it is a poor fit for
how the client is actually run today, and it is where most of our recent bug class lives
(stale `ImageData` pointers, corrupt button images, blank-dir freezes, drain-loop stalls).

Kickstart 2.0+ and 3.x provide much better UX building blocks. Adopting them costs us no
compatibility we still have (see §3) and would retire whole categories of bugs.

## 2. The model / view boundary (the key idea)

The client already separates cleanly into two halves:

- **Model — stays faithful, untouched.** The X.25/TCP transport, the protocol engine, and
  the **PETSCII frame renderer**. The frames *are* the Compunet content; they must remain
  pixel-exact. This is what [CLAUDE.md](../CLAUDE.md)'s fidelity rule protects.
- **View — free to modernise.** The Intuition chrome: windows, gadgets, menus, the
  directory grid, the pointer, the layout. None of this is "Compunet content"; it is only
  how we present the model.

**Modernisation is a view rewrite over an unchanged model.** It should therefore be a
**separate track / client variant**: the faithful reconstruction remains the reference
and archival artifact; the modern client is the "product" build. Both share the same
transport + protocol + frame-render core.

## 3. We are already past KS 1.3

TCP needs `bsdsocket.library`, so **KS 2.04+ is already a hard requirement** in the mode
everyone uses. The 1.3-era raw-Intuition UX is not buying compatibility we still have — we
can freely adopt KS 2.0+ APIs (GadTools, ASL, gadtools menus, the 3D look), and 3.x APIs
(ReAction, datatypes) if we raise the floor, with no *additional* loss.

## 4. Toolkit options

| Option | Look / feel | Min OS | Dependency | Notes |
|---|---|---|---|---|
| **GadTools + ASL** | Native 3D, conservative | 2.04 | none (in ROM/2.0) | Standard button/listview/cycle/string gadgets, real menus, ASL file/screenmode requesters. Minimum credible modern step. |
| **ReAction** (BOOPSI) | Native, **resizable, font-sensitive** | 3.5 (or classes on 3.x) | ships with OS 3.5/3.9 | `window`/`layout`/`button`/`listbrowser`/`clicktab`/`chooser` classes. No third-party dep. **Recommended sweet spot.** |
| **MUI** | Most modern, dynamic, skinnable | 2.04+ (with MUI) | requires MUI installed | Best UX and the enthusiast standard, but a runtime dependency and a distinct look. |

## 5. How comparable modern Amiga apps did it

The apps most like a Compunet client are **online-service / content-navigation clients**
(a list of things → pick one → view content → navigate/reply). Their toolkit choices form
a clear pattern.

| App | Kind | Toolkit | Why it's relevant here |
|---|---|---|---|
| **Term** (Olaf Barthel) | Serial terminal / comms | **GadTools** (+ its own layer) | Closest single analogue — a polished comms terminal built on the native toolkit. |
| **AmIRC**, **AmFTP**, **AmTelnet** (Vapor suite) | Internet clients | **MUI** | The direct lineage: online clients with a list pane + content + input line, all MUI. |
| **YAM** ("Yet Another Mailer") | Email client | **MUI** | Message-list + read-pane + compose — mirrors the Courier/mail feature almost exactly. |
| **SimpleMail** | Email client | **MUI** | Modern mailer; same list/read/compose shape. |
| **Voyager** | Web browser | **MUI** | Navigate + render content + history/back — the browse loop. |
| **AWeb** (II / 3) | Web browser | **ClassAct → ReAction** | Same browse loop as Voyager but taking the *native-toolkit* route. |
| **IBrowse** | Web browser | **Custom BOOPSI** | The "roll your own BOOPSI class system" path — most control, most work. |
| **Directory Opus 5 / Magellan** | File manager | **Custom skinnable GUI** | The fully-bespoke, skinned extreme. |
| **Workbench 3.5 / 3.9 tools & prefs** | System utilities | **ReAction** | The "native OS toolkit" baseline that ships with the OS. |

**Pattern:** internet/online-service clients clustered on **MUI** (Vapor suite, YAM,
Voyager); the native-OS route for browsers/tools was **ReAction** (AWeb, OS 3.5/3.9);
terminal/comms programs of the 2.0 era used **GadTools** (Term). A Compunet client sits
squarely in the "internet client" family — which is exactly the MUI/ReAction territory.

## 6. Recommended redesign (per screen)

Highest-impact first:

1. **Directory → a real list** (ReAction `listbrowser` / GadTools `listview` / MUI
   `List`): columns for page# · title · type · price · author · date · life, sortable,
   scrollable, keyboard-navigable, double-click to enter. Retires the fixed 11-row PETSCII
   grid with invisible click-rows — the worst of the current UX, and the single biggest win.
2. **One resizable window with panes** (`layout.class` / MUI groups): directory list ·
   frame view · status bar. Replaces separate fixed windows at hardcoded coordinates.
3. **Frame view**: keep the PETSCII render **pixel-faithful** (it is the content), but host
   it in a resizable/scalable pane with a real button toolbar (Dir/Back/Goto/More). This
   also removes the custom `Image` structs — where the stale-`ImageData` and button-image
   corruption bugs lived.
4. **Mail**: message listbrowser + read pane (the YAM/SimpleMail shape).
5. **Requesters & chrome**: ASL for download/upload file selection; native gadtools/ReAction
   menus with proper shortcuts; `SetWindowPointer` for the busy state (retires the
   hand-built sprite); a status bar for connection state / credit / page info.

## 6a. Aspect ratio / pixel geometry

The PETSCII frames were authored on a **C64**, whose pixels are **not square** — on a PAL
C64 the 320×200 active picture is stretched to roughly fill a 4:3 TV, so each pixel is a
little **taller than wide**. The current client renders each cell as a fixed **8×8 square**
block 1:1, so the content is shown at the *wrong proportions* versus how its authors saw
it (characters/graphics look squashed). This is the same problem every C64 emulator solves,
and it should be solved the same way.

**Principle: decouple the render resolution from the display size.**

1. Render the frame into a **native offscreen BitMap** at its true pixel grid (40×25 cells
   × 8×8 = 320×200) — pixel-exact, unchanged from the faithful renderer. We already have an
   offscreen path (`frame_offscreen_*`), so this is where the render lands anyway.
2. **Scale that offscreen to the display**, applying the **C64 pixel-aspect-ratio (PAR)
   correction** — i.e. stretch it vertically so the authored proportions are restored
   (target = the PAL C64 look; match it to VICE's PAL output rather than guessing a number).
   Compunet was a UK/PAL service, so PAL PAR is the reference.

Because step 2 is just a scale, the *same* operation both fixes the aspect ratio **and**
lets the frame fill a resizable window (letterbox/pillarbox to preserve aspect). Mechanisms:

- **AGA / native chip:** `graphics.library/BitMapScale()` (KS 3.0+) — ROM-based bitmap scale.
- **RTG (CyberGraphX / Picasso96):** `ScalePixelArray()` — scale to any window size, with
  nearest-neighbour or smoothed output.

**Options worth exposing** (again, mirroring what emulators do):
- *Aspect correction* on/off (raw square-pixel vs PAL-correct).
- *Integer scaling* (crisp, blocky pixel-art) vs *smooth* scaling — integer is usually the
  authentic-looking choice for PETSCII, but non-integer aspect correction means at least one
  axis is fractional, so offer both and let the user pick.
- Optionally render the font into a **higher-resolution offscreen** first for cleaner
  large-window scaling.

This keeps the renderer 100% faithful (native 320×200) and moves all aspect/size handling
into a presentation-time scale — exactly the model/view boundary from §2.

## 7. The biggest win is architectural, not cosmetic

Make the transport **asynchronous**: run `bsdsocket` I/O in a **separate Process** that
talks to the UI via message ports, so the UI never blocks on a read. This one change:

- eliminates the whole **freeze class** we have been fixing (blank-dir hang, welcome-frame
  drain loops, the editor round-trip stalls);
- makes the client *feel* modern — responsive, cancellable operations, real progress/status;
- is **orthogonal to the toolkit** — worth doing whichever GUI we pick.

## 8. Suggested sequence

1. **Async transport** (separate Process + message ports) — biggest UX and stability win.
2. **Directory listbrowser** — biggest single view win.
3. **Resizable window + layout** (list · frame · status panes).
4. **Remaining chrome** — menus, requesters, toolbar, pointer, mail pane.

Each step is independently shippable and leaves the faithful model untouched.

## 9. Decisions needed

1. **Scope** — modern client as a *separate variant* sharing the faithful core
   (recommended), or an in-place evolution of the one client?
2. **Toolkit** — **ReAction** (native, no dependency, resizable) vs **MUI** (most polished,
   enthusiast standard, needs MUI installed) vs **GadTools** (most conservative/broadest).
   Given the app is an "internet client," ReAction or MUI both fit the lineage; ReAction
   avoids the runtime dependency.
3. **Minimum OS** — hold at KS 2.04 (GadTools only), or target 3.x to unlock ReAction /
   datatypes?

## Related

- Faithful reconstruction status: [amiga-client.md](amiga-client.md).
- Transport design: [../client/amiga/src/TCP-TRANSPORT.md](../client/amiga/src/TCP-TRANSPORT.md).
