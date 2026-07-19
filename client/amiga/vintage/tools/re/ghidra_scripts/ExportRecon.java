import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.address.Address;
import ghidra.program.model.symbol.Reference;
import java.io.*;
import java.util.*;

// Export a function map + decompiled C for the whole program.
public class ExportRecon extends GhidraScript {
    public void run() throws Exception {
        String out = System.getenv("RECON_OUT");
        if (out == null) out = ".";
        DecompInterface d = new DecompInterface();
        d.openProgram(currentProgram);
        Listing listing = currentProgram.getListing();
        FunctionManager fm = currentProgram.getFunctionManager();
        PrintWriter fout = new PrintWriter(new FileWriter(out + "/recon_functions.txt"));
        PrintWriter cout = new PrintWriter(new FileWriter(out + "/recon.c"));
        fout.println("# addr  size  name  ncalls  strings");
        FunctionIterator it = fm.getFunctions(true);
        int n = 0;
        while (it.hasNext()) {
            Function f = it.next();
            Address ep = f.getEntryPoint();
            long size = f.getBody().getNumAddresses();
            int ncalls = f.getCalledFunctions(monitor).size();
            TreeSet<String> strs = new TreeSet<>();
            InstructionIterator ii = listing.getInstructions(f.getBody(), true);
            while (ii.hasNext()) {
                Instruction ins = ii.next();
                for (Reference r : ins.getReferencesFrom()) {
                    Data dat = listing.getDataAt(r.getToAddress());
                    if (dat != null && dat.hasStringValue()) {
                        String s = dat.getValue().toString().trim();
                        if (!s.isEmpty()) strs.add(s);
                    }
                }
            }
            String strtxt = String.join(" | ", strs).replace("\n", " ").replace("\r", " ");
            if (strtxt.length() > 240) strtxt = strtxt.substring(0, 240);
            fout.println(ep + "  " + size + "  " + f.getName() + "  " + ncalls + "  " + strtxt);
            try {
                DecompileResults res = d.decompileFunction(f, 60, monitor);
                if (res.decompileCompleted()) {
                    cout.println("/* ===== " + f.getName() + " @ " + ep + " (size " + size + ") ===== */");
                    if (!strs.isEmpty()) cout.println("/* strings: " + strtxt + " */");
                    cout.println(res.getDecompiledFunction().getC());
                    cout.println();
                }
            } catch (Exception e) {
                cout.println("/* decompile failed " + f.getName() + ": " + e + " */");
            }
            n++;
        }
        fout.close();
        cout.close();
        println("ExportRecon wrote " + n + " functions");
    }
}
