import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.lang.Register;
import ghidra.program.model.listing.ProgramContext;
import java.math.BigInteger;

// Seed disassembly at every CODE hunk base so auto-analysis reaches all modules,
// and set A4 = 0x11d000 (the SAS/C small-data base) across the whole image so the
// analyzer resolves a4-relative globals and string references.
public class SeedCode extends GhidraScript {
    long[] addrs = {
        0x100000L,0x102000L,0x103000L,0x104000L,0x105000L,0x106000L,0x107000L,0x108000L,
        0x109000L,0x10b000L,0x10c000L,0x10d000L,0x10e000L,0x10f000L,0x110000L,0x111000L,
        0x112000L,0x113000L,0x114000L,0x115000L,0x117000L,0x118000L,0x119000L,0x11a000L,
        0x11b000L,0x11c000L,0x124000L,0x125000L,0x126000L,0x127000L,0x128000L,0x129000L,
        0x12a000L,0x12b000L
    };
    public void run() throws Exception {
        // set A4 small-data base across the whole program
        Register a4 = currentProgram.getRegister("A4");
        ProgramContext ctx = currentProgram.getProgramContext();
        Address min = currentProgram.getMinAddress();
        Address max = currentProgram.getMaxAddress();
        ctx.setValue(a4, min, max, BigInteger.valueOf(0x11d000L));

        addEntryPoint(toAddr(0x100000L));
        for (long a : addrs) {
            Address ad = toAddr(a);
            try { disassemble(ad); createFunction(ad, null); } catch (Exception e) {}
        }
        println("SeedCode: seeded " + addrs.length + " hunk starts, A4=0x11d000");
    }
}
