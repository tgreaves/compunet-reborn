/*
 * test_flash.c — minimal toolchain sanity check (TEMPORARY).
 *
 * Does NOT open any library or touch any of the reconstruction. It just slams the
 * Amiga background-colour register red, forever. Built with the exact same
 * vc +kick13 toolchain/startup/config as the real client.
 *
 *   - If booting this shows a RED screen  -> the toolchain/startup/link/config are
 *     fine and main() is reached; the crash is somewhere in our reconstructed code.
 *   - If booting this GURUs with no red   -> the fault is in the C startup / link /
 *     config itself (independent of our code), and that's what we fix next.
 */
int main(void)
{
    volatile unsigned short *color00 = (volatile unsigned short *)0xDFF180;
    volatile unsigned short *color01 = (volatile unsigned short *)0xDFF182;
    unsigned long i;

    for (;;) {
        for (i = 0; i < 100000UL; i++) *color00 = 0x0f00;   /* red   */
        for (i = 0; i < 100000UL; i++) *color00 = 0x000f;   /* blue  */
        (void)color01;
    }
    return 0;
}
