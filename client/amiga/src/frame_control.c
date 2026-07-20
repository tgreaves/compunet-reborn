/*
 * frame_control.c — PETSCII control-code handlers + dispatch tables (reconstructed).
 *
 * render_char() (frame.c) dispatches control bytes through two function-pointer
 * tables: g_ctrl_lo for PETSCII 0x00-0x1F, g_ctrl_hi for 0x80-0x9F (indexed by
 * ch & 0x7f). This file reconstructs every handler and, crucially, the exact table
 * ordering — which was NOT guessed: the tables are data in the original binary
 * (recon addresses 0x11d8a8 / 0x11d928) and were read verbatim from the flat image
 * (see coverage-census.md / the tools/re extraction). Each entry below is annotated
 * with the recon handler address it came from.
 *
 * These are the canonical C64 PETSCII control codes: colour set (0x05/0x1c/0x1e/...
 * and 0x90-0x9f), reverse on/off (0x12/0x92), charset switch (0x0e/0x8e), cursor
 * home/up/down/left/right, CR, insert/delete line, clear screen. So Compunet Reborn
 * PETSCII frame content renders on the Amiga with no separate format — the whole
 * point of project goal #3.
 *
 * The handlers operate on the frame "page" via the same offsets frame.c uses:
 *   +0x04 row  +0x06 col  +0x08 colour  +0x09 attr(reverse<<7)  +0x0a wrap
 *   +0x0c lowercase-mode flag  +0x0f background  +0x10.. cell array
 */
#include <exec/types.h>

#include "compunet.h"

#define P_ROW(p)   (*(short *)((UBYTE *)(p) + 0x04))
#define P_COL(p)   (*(short *)((UBYTE *)(p) + 0x06))
#define P_COLOUR(p)(*(UBYTE *)((UBYTE *)(p) + 0x08))
#define P_ATTR(p)  (*(UBYTE *)((UBYTE *)(p) + 0x09))
#define P_WRAP(p)  (*(short *)((UBYTE *)(p) + 0x0a))
#define P_MODE(p)  (*(short *)((UBYTE *)(p) + 0x0c))

extern void frame_redraw(APTR page);          /* thunk FUN_00107156 — full re-blit */
extern void frame_clear_region(int r0,int c0,int r1,int c1,APTR page); /* FUN_0010544e */

/* ---- colour setters (recon 0x105000..0x10510c) — write the C64 colour index ---- */
static void set_colour_black (APTR p){ P_COLOUR(p)=0;  }
static void set_colour_white (APTR p){ P_COLOUR(p)=1;  }
static void set_colour_red   (APTR p){ P_COLOUR(p)=2;  }
static void set_colour_cyan  (APTR p){ P_COLOUR(p)=3;  }
static void set_colour_purple(APTR p){ P_COLOUR(p)=4;  }
static void set_colour_green (APTR p){ P_COLOUR(p)=5;  }
static void set_colour_blue  (APTR p){ P_COLOUR(p)=6;  }
static void set_colour_yellow(APTR p){ P_COLOUR(p)=7;  }
static void set_colour_orange(APTR p){ P_COLOUR(p)=8;  }
static void set_colour_brown (APTR p){ P_COLOUR(p)=9;  }
static void set_colour_lt_red(APTR p){ P_COLOUR(p)=10; }
static void set_colour_grey1 (APTR p){ P_COLOUR(p)=11; }
static void set_colour_grey2 (APTR p){ P_COLOUR(p)=12; }
static void set_colour_lt_grn(APTR p){ P_COLOUR(p)=13; }
static void set_colour_lt_blu(APTR p){ P_COLOUR(p)=14; }
static void set_colour_grey3 (APTR p){ P_COLOUR(p)=15; }

/* ---- reverse video (recon 0x10511e / 0x105130) — sets attr bit 7 ---- */
static void reverse_on (APTR p){ P_ATTR(p)=0x80; }
static void reverse_off(APTR p){ P_ATTR(p)=0x00; }

/* ---- charset switch (recon 0x105140 / 0x105162) — toggle mode + redraw ---- */
static void charset_lower(APTR p){ if (P_MODE(p)!=1){ P_MODE(p)=1; frame_redraw(p);} }
static void charset_upper(APTR p){ if (P_MODE(p)!=0){ P_MODE(p)=0; frame_redraw(p);} }

/* ---- cursor movement (recon 0x105180..0x10521e) ---- */
static void cursor_home(APTR p){ P_ROW(p)=0; P_COL(p)=0; P_WRAP(p)=0; }
static void cursor_down(APTR p){ if (P_ROW(p)<0x17) P_ROW(p)++; P_WRAP(p)=0; }
static void cursor_up  (APTR p){ if (P_ROW(p)>0)    P_ROW(p)--; P_WRAP(p)=0; }
static void cursor_right(APTR p){
    if (++P_COL(p)==0x28){ P_COL(p)=0; if (P_ROW(p)<0x17) P_ROW(p)++; }
    P_WRAP(p)=0;
}
static void cursor_left(APTR p){
    if (--P_COL(p)<0){ P_COL(p)=0x27; if (P_ROW(p)>0) P_ROW(p)--; }
    P_WRAP(p)=0;
}

/* ---- carriage return (recon 0x105250): if not just-wrapped, advance a row ---- */
static void carriage_return(APTR p){
    if (P_WRAP(p)==0 && P_ROW(p)<0x17) P_ROW(p)++;
    P_COL(p)=0; P_WRAP(p)=0; P_ATTR(p)=0;
}

/* ---- insert / delete char in the current line (recon 0x10527e / 0x105376) ---- */
extern void frame_insert_char(APTR page);  /* FUN_0010527e */
extern void frame_delete_char(APTR page);  /* FUN_00105376 */
static void insert_char(APTR p){ frame_insert_char(p); }
static void delete_char(APTR p){ frame_delete_char(p); }

/* ---- clear screen (recon 0x1054bc) ---- */
static void clear_screen(APTR p){
    frame_clear_region(0,0,0x17,0x27,p);
    P_ROW(p)=0; P_COL(p)=0; P_WRAP(p)=0;
}

/* ---- no-op (recon 0x1054f0): unused control codes ---- */
static void ctrl_nop(APTR p){ (void)p; }

/*
 * g_ctrl_lo — PETSCII 0x00-0x1F. Ordering read verbatim from the binary's table at
 * recon 0x11d8a8. Unused codes map to ctrl_nop.
 */
void (*g_ctrl_lo[32])(APTR page) = {
    /*00*/ ctrl_nop,       /*01*/ ctrl_nop,       /*02*/ ctrl_nop,   /*03*/ ctrl_nop,
    /*04*/ ctrl_nop,       /*05*/ set_colour_white,/*06*/ ctrl_nop,  /*07*/ ctrl_nop,
    /*08*/ ctrl_nop,       /*09*/ ctrl_nop,       /*0a*/ ctrl_nop,   /*0b*/ ctrl_nop,
    /*0c*/ ctrl_nop,       /*0d*/ carriage_return,/*0e*/ charset_lower,/*0f*/ ctrl_nop,
    /*10*/ ctrl_nop,       /*11*/ cursor_down,    /*12*/ reverse_on, /*13*/ cursor_home,
    /*14*/ insert_char,    /*15*/ ctrl_nop,       /*16*/ ctrl_nop,   /*17*/ ctrl_nop,
    /*18*/ ctrl_nop,       /*19*/ ctrl_nop,       /*1a*/ ctrl_nop,   /*1b*/ ctrl_nop,
    /*1c*/ set_colour_red, /*1d*/ cursor_right,   /*1e*/ set_colour_green,/*1f*/ set_colour_blue
};

/*
 * g_ctrl_hi — PETSCII 0x80-0x9F (render_char indexes it with ch & 0x7f, so entries
 * 0x00-0x1F correspond to 0x80-0x9F). Ordering read verbatim from recon 0x11d928.
 * Only 0x00-0x1F are ever indexed; the rest of the 128-entry array in the binary is
 * font bitmap data that follows the table and is never called, so we leave it nop.
 */
void (*g_ctrl_hi[128])(APTR page) = {
    /*80*/ ctrl_nop,        /*81*/ set_colour_orange,/*82*/ ctrl_nop, /*83*/ ctrl_nop,
    /*84*/ ctrl_nop,        /*85*/ ctrl_nop,        /*86*/ ctrl_nop,  /*87*/ ctrl_nop,
    /*88*/ ctrl_nop,        /*89*/ ctrl_nop,        /*8a*/ ctrl_nop,  /*8b*/ ctrl_nop,
    /*8c*/ ctrl_nop,        /*8d*/ carriage_return, /*8e*/ charset_upper,/*8f*/ ctrl_nop,
    /*90*/ set_colour_black,/*91*/ cursor_up,       /*92*/ reverse_off,/*93*/ clear_screen,
    /*94*/ delete_char,     /*95*/ set_colour_lt_red,/*96*/ set_colour_grey3,/*97*/ set_colour_grey2,
    /*98*/ set_colour_lt_grn,/*99*/ set_colour_lt_blu,/*9a*/ set_colour_grey1,/*9b*/ set_colour_brown,
    /*9c*/ set_colour_purple,/*9d*/ cursor_left,    /*9e*/ set_colour_yellow,/*9f*/ set_colour_cyan
    /* 0x20-0x7f: unused (font data in original) — zero-initialised, never indexed */
};
