import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.lang.Register;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import ghidra.program.model.scalar.Scalar;
import ghidra.program.model.mem.MemoryBlock;
import ghidra.program.model.lang.OperandType;
import java.math.BigInteger;
import java.util.*;

// Seed disassembly across the whole image, set A4 = 0x11d000 (SAS/C small-data
// base), then ITERATIVELY discover functions reached only via jsr/jmp/pea targets.
//
// The original version seeded only the 34 hunk starts, so functions reached solely
// through indirect/computed calls (e.g. do_connect @0x10343c, open_transport
// @0x1192b6) were never created — they were missing from the decompiled output.
// This version repeatedly scans instructions for absolute call/branch targets and
// pointer-sized constants that land in executable memory, disassembles + creates a
// function at each, and loops until no new functions appear.
public class SeedCode extends GhidraScript {
    long[] hunks = {
        0x100000L,0x102000L,0x103000L,0x104000L,0x105000L,0x106000L,0x107000L,0x108000L,
        0x109000L,0x10b000L,0x10c000L,0x10d000L,0x10e000L,0x10f000L,0x110000L,0x111000L,
        0x112000L,0x113000L,0x114000L,0x115000L,0x117000L,0x118000L,0x119000L,0x11a000L,
        0x11b000L,0x11c000L,0x124000L,0x125000L,0x126000L,0x127000L,0x128000L,0x129000L,
        0x12a000L,0x12b000L
    };

    // CODE hunk [start,end) ranges (from compunet_flat.map). The flat BinaryLoader
    // block is one region, so we can't rely on isExecute() to separate CODE from the
    // DATA/BSS hunks (0x116000, 0x11d000+). Discovered targets must land in one of
    // these ranges to be seeded as a function — prevents seeding into data.
    long[][] codeRanges = {
        {0x100000L,0x10184cL},{0x102000L,0x102b58L},{0x103000L,0x103850L},{0x104000L,0x10416cL},
        {0x105000L,0x1056f0L},{0x106000L,0x1062b0L},{0x107000L,0x1071b0L},{0x108000L,0x1082a4L},
        {0x109000L,0x10a5f0L},{0x10b000L,0x10b8acL},{0x10c000L,0x10c6fcL},{0x10d000L,0x10d264L},
        {0x10e000L,0x10e728L},{0x10f000L,0x10f5f4L},{0x110000L,0x110554L},{0x111000L,0x1117b8L},
        {0x112000L,0x1124c0L},{0x113000L,0x113108L},{0x114000L,0x1140bcL},{0x115000L,0x11526cL},
        {0x117000L,0x11764cL},{0x118000L,0x118168L},{0x119000L,0x119b68L},{0x11a000L,0x11a988L},
        {0x11b000L,0x11b4ccL},{0x11c000L,0x11c0dcL},{0x124000L,0x124014L},{0x125000L,0x1250dcL},
        {0x126000L,0x126024L},{0x127000L,0x127074L},{0x128000L,0x12813cL},{0x129000L,0x1291f8L},
        {0x12a000L,0x12a138L},{0x12b000L,0x12b28cL}
    };

    public void run() throws Exception {
        Register a4 = currentProgram.getRegister("A4");
        ProgramContext ctx = currentProgram.getProgramContext();
        Address min = currentProgram.getMinAddress();
        Address max = currentProgram.getMaxAddress();
        ctx.setValue(a4, min, max, BigInteger.valueOf(0x11d000L));

        addEntryPoint(toAddr(0x100000L));
        for (long a : hunks) {
            try { disassemble(toAddr(a)); createFunction(toAddr(a), null); } catch (Exception e) {}
        }

        // Seed on function prologues: scan CODE ranges for `link.w aN,#imm`
        // (opcode 0x4e5x) which begins nearly every SAS/C function. This catches
        // functions reached only through paths analysis hasn't walked yet (e.g.
        // do_connect @0x10343c, reached by a bsr from an un-analysed region).
        seedPrologues();

        // Iteratively discover call/branch targets until the function set is stable.
        FunctionManager fm = currentProgram.getFunctionManager();
        int pass = 0, prev = -1;
        while (true) {
            int before = fm.getFunctionCount();
            if (before == prev) break;      // stable
            prev = before;
            pass++;
            Set<Long> targets = scanTargets();
            int created = 0;
            for (long t : targets) {
                Address ta = toAddr(t);
                if (!isExecutable(ta)) continue;
                if (fm.getFunctionAt(ta) != null) continue;
                try {
                    disassemble(ta);
                    Function f = createFunction(ta, null);
                    if (f != null) created++;
                } catch (Exception e) {}
            }
            println("SeedCode pass " + pass + ": functions " + before + " -> " +
                    fm.getFunctionCount() + " (+" + created + ")");
            if (created == 0) break;
        }
        println("SeedCode: done, " + fm.getFunctionCount() + " functions, A4=0x11d000");
    }

    // Scan every CODE range for `link.w aN,#imm16` prologues (0x4e50..0x4e57) and
    // seed a function at each. This linear scan finds functions no control-flow path
    // reached during analysis.
    private void seedPrologues() throws Exception {
        ghidra.program.model.mem.Memory mem = currentProgram.getMemory();
        int found = 0;
        for (long[] r : codeRanges) {
            for (long off = r[0]; off + 2 <= r[1]; off += 2) {
                Address a = toAddr(off);
                int w;
                try { w = mem.getShort(a) & 0xffff; } catch (Exception e) { continue; }
                // link.w a0..a7 = 0x4e50..0x4e57
                if (w >= 0x4e50 && w <= 0x4e57) {
                    if (currentProgram.getFunctionManager().getFunctionAt(a) != null) continue;
                    try { disassemble(a); if (createFunction(a, null) != null) found++; }
                    catch (Exception e) {}
                }
            }
        }
        println("SeedCode: prologue scan seeded " + found + " link.w functions");
    }

    // Collect targets of actual call/branch instructions only. We use Ghidra's
    // decoded flow references for CALL/JUMP-kind references (covers pc-relative
    // bsr/jsr and jmp $abs), and restrict to call/branch mnemonics. Raw scalar
    // operands are deliberately NOT seeded — they produce spurious mid-instruction
    // "functions". Completeness comes from the link.w prologue scan instead.
    private Set<Long> scanTargets() {
        Set<Long> out = new HashSet<>();
        Listing listing = currentProgram.getListing();
        InstructionIterator it = listing.getInstructions(true);
        while (it.hasNext()) {
            Instruction ins = it.next();
            String mn = ins.getMnemonicString().toLowerCase();
            if (!(mn.startsWith("jsr") || mn.startsWith("jmp") || mn.startsWith("bsr")))
                continue;
            for (Reference r : ins.getReferencesFrom()) {
                if (r.getReferenceType().isCall() || r.getReferenceType().isJump()) {
                    Address to = r.getToAddress();
                    if (to != null && to.isMemoryAddress()) out.add(to.getOffset());
                }
            }
        }
        return out;
    }

    // A target is seedable only if it lands within a known CODE hunk range and is
    // even (68000 instructions are word-aligned).
    private boolean isExecutable(Address a) {
        long off = a.getOffset();
        if ((off & 1) != 0) return false;
        for (long[] r : codeRanges) if (off >= r[0] && off < r[1]) return true;
        return false;
    }
}
