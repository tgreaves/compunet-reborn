import ghidra.app.script.GhidraScript;
import ghidra.program.model.address.Address;
import ghidra.program.model.listing.Function;
import ghidra.program.model.symbol.SourceType;
import java.io.*;
import java.util.*;

// Apply confirmed names (functions + globals) from symbols.json to the Ghidra DB
// before ExportRecon runs, so recon.c decompiles with real identifiers
// (do_connect, serial_write, SysBase, g_write_req, ...).
//
// Minimal JSON reader (no external deps): the file is a flat two-object map of
// hex-address -> name under "functions" and "globals". Global labels are created
// as primary symbols; the decompiler renders references to them by name.
public class ApplySymbols extends GhidraScript {
    public void run() throws Exception {
        String dir = System.getenv("RECON_SRC");
        if (dir == null) dir = ".";
        File f = new File(dir, "symbols.json");
        if (!f.exists()) { println("ApplySymbols: no symbols.json at " + f); return; }
        String text = new String(java.nio.file.Files.readAllBytes(f.toPath()));

        int fn = applySection(text, "functions", true);
        int gl = applySection(text, "globals", false);
        println("ApplySymbols: named " + fn + " functions, " + gl + " globals");
    }

    // Extract the { ... } body of "section" and apply each "0xADDR": "name" pair.
    private int applySection(String text, String section, boolean isFunction) throws Exception {
        int key = text.indexOf('"' + section + '"');
        if (key < 0) return 0;
        int open = text.indexOf('{', key);
        int close = text.indexOf('}', open);
        if (open < 0 || close < 0) return 0;
        String body = text.substring(open + 1, close);
        int count = 0;
        // match "0x...." : "name"
        java.util.regex.Matcher m = java.util.regex.Pattern
            .compile("\"(0x[0-9a-fA-F]+)\"\\s*:\\s*\"([^\"]+)\"").matcher(body);
        while (m.find()) {
            long addr = Long.parseLong(m.group(1).substring(2), 16);
            String name = m.group(2);
            Address a = toAddr(addr);
            try {
                if (isFunction) {
                    Function fn = getFunctionAt(a);
                    if (fn == null) fn = createFunction(a, name);
                    if (fn != null) { fn.setName(name, SourceType.USER_DEFINED); count++; }
                    else println("  ! no function at " + a + " for " + name);
                } else {
                    createLabel(a, name, true, SourceType.USER_DEFINED);
                    count++;
                }
            } catch (Exception e) {
                println("  ! failed " + name + " @ " + a + ": " + e);
            }
        }
        return count;
    }
}
