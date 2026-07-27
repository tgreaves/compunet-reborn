// Binding-B message contract, in code. Mirrors docs/spec/api/README.md — the
// same shapes the server serializes (server/api_binding.py). The compiler
// checks every message the client reads and every command it sends against
// these, so client and server can't silently drift.

/** One rendered cell of a 40x24 frame grid (spec §5). */
export interface Cell {
  /** glyph index 0-255 (0-127 uppercase/graphics set, 128-255 lowercase set) */
  g: number;
  /** foreground palette index 0-15 */
  fg: number;
  /** background palette index 0-15 */
  bg: number;
  /** reverse-video flag */
  rv: 0 | 1;
}

export interface FrameMsg {
  type: 'frame';
  id?: number | string;
  border: number;
  background: number;
  morePages: boolean;
  rows: number;
  cols: number;
  cells: Cell[];
  /** base64 of the exact §6 bytes this grid was rendered from. Opaque — the
   *  client never parses it; it stores it with a captured page so an unedited
   *  page re-uploads byte-for-byte (§8.4.2). */
  raw?: string;
  /** charset in force at the end of the stream — row 24 draws in it (§4.9.3) */
  lower?: boolean;
}

export interface Entry {
  index: number;
  page: number;
  title: string;
  /** base entry type letter (T/D/P/PP/S/L, §7.4) */
  type: string;
  size: number | null;
  hasSubdir: boolean;
  /** right-pane column values, parallel to DirectoryMsg.columns, already justified server-side */
  values: string[];
}

export interface DirectoryMsg {
  type: 'directory';
  id?: number | string;
  /** 'mail' when this listing is the mailbox (§8.2), else absent */
  context?: string;
  page: number;
  title: string;
  breadcrumb: string[];
  columns: string[];
  advert: string[];
  mailWaiting?: boolean;
  header: FrameMsg | null;
  hasMore: boolean;
  entries: Entry[];
}

export interface Account { user: string; credit: number; }
export interface ReadyMsg { type: 'ready'; account: Account; welcome: FrameMsg | null; }
export interface AccountMsg { type: 'account'; creditText: string; credit: number; }
export interface IdLookupMsg { type: 'idlookup'; id?: number | string; users: { id: string; name: string | null }[]; }
export interface DownloadMsg {
  type: 'download'; id?: number | string;
  page: number | null; title: string | null; size: number; machine: string;
}
export interface DownloadDataMsg {
  type: 'download.data'; id?: number | string;
  title: string | null; size: number; /** base64 */ bytes: string;
}
export interface ErrorMsg { type: 'error'; id?: number | string; code: string; message?: string; }
export interface AckMsg { type: 'ack'; id?: number | string; of?: string; }
export interface PartylineMsg { type: 'partyline'; line: string; }
export interface PartylineEnteredMsg { type: 'partyline.entered'; id?: number | string; room: string; }
export interface PartylineLeftMsg { type: 'partyline.left'; id?: number | string; }
export interface NoticeMsg { type: 'notice'; kind: string; [k: string]: unknown; }

/** Any message the server may send over the gateway. */
export type ServerMsg =
  | ReadyMsg | DirectoryMsg | FrameMsg | AccountMsg | IdLookupMsg
  | DownloadMsg | DownloadDataMsg
  | ErrorMsg | AckMsg | PartylineMsg | PartylineEnteredMsg | PartylineLeftMsg | NoticeMsg
  | { type: string;[k: string]: unknown };

/** Commands the client sends (spec §4 of the binding). */
export type ClientMsg =
  | { type: 'auth'; token: string }
  | { type: 'enter'; page: number; id?: number }
  | { type: 'open'; page: number; id?: number }
  | { type: 'more'; id?: number }
  | { type: 'finish'; id?: number }
  | { type: 'back'; id?: number }
  | { type: 'goto'; target: string; id?: number }
  | { type: 'account'; id?: number }
  | { type: 'dir'; id?: number }
  // Tier 2
  | { type: 'ucat'; id?: number }
  | { type: 'mail.list'; id?: number }
  /** DONE — leave Courier (§4.8). One command, not a run of `back`s. */
  | { type: 'mail.done'; id?: number }
  | { type: 'mail.read'; id_?: number; index?: number; id?: number }
  | { type: 'idlookup'; ids: string[]; id?: number }
  | { type: 'vote'; page: number; score: number; id?: number }
  | { type: 'life'; page: number; days: number; id?: number }
  | { type: 'download.fetch'; id?: number }
  // Tier 3
  /** `frames` are editor pages for `kind: 'T'`, and base64 PROGRAM BLOBS —
   *  bare strings — for `kind: 'P'` (§8.3.2). Each blob is an 8-byte header
   *  followed by the body: byte 0 machine type (0 C64 / 1 Amiga), bytes 4-5 the
   *  C64 load address, 6-7 the body size. */
  | { type: 'upload'; title: string; kind: string; price: number; life: number; frames: (EditorPage | string)[]; id?: number }
  | { type: 'mail.send'; to: string[]; subject: string; frames: EditorPage[]; id?: number }
  | { type: 'partyline.send'; text: string; id?: number }
  | { type: 'partyline.command'; text: string; id?: number }
  | { type: 'partyline.leave'; id?: number }
  | { type: 'leave'; id?: number };

/** A page submitted from the editor (§8.4). The server encodes it to a §6
 *  frame, so the client never has to produce PETSCII. Three forms (§5.4):
 *
 *  - `{raw}`   verbatim bytes — a captured page the user has not edited, sent
 *              back byte-for-byte (§8.4.2). Nothing is re-encoded.
 *  - `{cells}` a full 40x24 grid: per-cell colour, reverse video and charset.
 *  - `{lines}` the simple text form, one colour for the whole page.
 */
export type EditorPage =
  | { raw: string }
  | { cells: Cell[]; border?: number; background?: number }
  | { lines: string[]; colour?: number; border?: number; background?: number };

/** Client-side assets, extracted from the spec appendix (gen_assets.py). */
export interface Assets {
  /** 16 CSS colours, index 0-15 (§A.3) */
  palette: string[];
  /** 256 glyphs, each 8 bytes / 8 rows, MSB = leftmost pixel (§A.5) */
  font: number[][];
  /** the directory-template chrome, pre-rendered to a 40x24 cell grid (§A.6) */
  template: FrameMsg;
  /** the embedded HELP frame (§A.8) — client asset; the server never sends it */
  help: FrameMsg | null;
  /** the EDITOR's help frame (§A.9) — a DIFFERENT asset, shown by the editor's
   *  own HELP command (§8.4.1). Not interchangeable with `help`. */
  editorHelp: FrameMsg | null;
  /** the COURIER frame (§A.10) — the ID-check screen (§8.2.1) */
  courier: FrameMsg | null;
  /** the COURIER SEND frame (§A.11) — a DIFFERENT, larger frame carrying the
   *  FROM / DATE / TIME / SUBJECT / TO labels. Not interchangeable with `courier`. */
  courierSend: FrameMsg | null;
}
