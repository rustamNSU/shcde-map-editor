// File-only export from an existing Ghidra database. Run with -readOnly.
// @category SHCDE
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.DecompInterface;
import ghidra.app.decompiler.DecompileResults;
import ghidra.program.model.listing.Function;
import ghidra.program.model.listing.Instruction;
import ghidra.program.model.listing.InstructionIterator;
import ghidra.program.model.address.Address;
import ghidra.program.model.address.AddressSet;
import java.io.File;
import java.io.PrintWriter;
import java.nio.file.Files;

public class MapFormatExport extends GhidraScript {
    public void run() throws Exception {
        File output = new File(getScriptArgs()[0]); output.mkdirs();
        String expected = "fbcb93195fc7efca9bdac5204852efdd76f9818f59a6711750d77c9cef2831e2";
        if (!expected.equalsIgnoreCase(currentProgram.getExecutableSHA256()))
            throw new IllegalStateException("Ghidra program differs from pinned DLL");
        long base = currentProgram.getImageBase().getOffset();
        DecompInterface decompiler = new DecompInterface();
        decompiler.openProgram(currentProgram);
        try {
            for (String line : Files.readAllLines(new File(getScriptArgs()[1]).toPath())) {
                if (line.isBlank() || line.startsWith("#")) continue;
                String[] parts = line.split(":");
                String name = parts[0]; long rva = Long.parseLong(parts[1], 16);
                Address first = toAddr(base + rva); AddressSet body = new AddressSet();
                for (String range : parts[2].split(",")) {
                    String[] limits = range.split("-");
                    Address start = toAddr(base + Long.parseLong(limits[0], 16));
                    Function existing = getFunctionAt(start);
                    if (existing != null && !start.equals(first)) removeFunction(existing);
                    body.addRange(start, toAddr(base + Long.parseLong(limits[1], 16) - 1));
                }
                Function function = getFunctionAt(first);
                if (function == null) { disassemble(first); function = createFunction(first, name); }
                if (function == null) { printerr("Missing " + name); continue; }
                function.setBody(body);
                for (String range : parts[2].split(","))
                    disassemble(toAddr(base + Long.parseLong(range.split("-")[0], 16)));
                decompiler.flushCache();
                DecompileResults result = decompiler.decompileFunction(function, 60, monitor);
                if (result.decompileCompleted() && result.getDecompiledFunction() != null) {
                    try (PrintWriter w = new PrintWriter(new File(output, name + ".c"), "UTF-8")) {
                        w.println("/* File-only Ghidra reconstruction; entry RVA 0x" + Long.toHexString(rva) + " */");
                        w.println(result.getDecompiledFunction().getC());
                    }
                } else printerr("Decompiler failed " + name + ": " + result.getErrorMessage());
                try (PrintWriter w = new PrintWriter(new File(output, name + ".asm"), "UTF-8")) {
                    InstructionIterator instructions = currentProgram.getListing().getInstructions(body, true);
                    while (instructions.hasNext()) {
                        Instruction instruction = instructions.next();
                        w.printf("%08X %s%n", instruction.getAddress().getOffset() - base, instruction.toString());
                    }
                }
                println("Exported " + name);
            }
        } finally { decompiler.dispose(); }
    }
}
