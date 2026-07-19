struct T {
    char  pad0[4];
    short row;    /* +4 */
    short col;    /* +6 */
    char  pad8[2];
    short w10;    /* +10 */
};
void cursor_advance(struct T *c)
{
    c->col++;
    if (c->col == 40) {
        c->col = 0;
        if (c->row < 23)
            c->row++;
    }
    c->w10 = 0;
}
