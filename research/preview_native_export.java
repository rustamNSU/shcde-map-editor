// Read-only native thumbnail producer investigation. @category SHCDE
import ghidra.app.script.GhidraScript;
import ghidra.app.decompiler.*;
import ghidra.program.model.address.*;
import ghidra.program.model.listing.*;
import ghidra.program.model.symbol.*;
import java.io.*;
import java.util.*;
public class preview_native_export extends GhidraScript {
  public void run() throws Exception {
    if (!"fbcb93195fc7efca9bdac5204852efdd76f9818f59a6711750d77c9cef2831e2".equalsIgnoreCase(currentProgram.getExecutableSHA256())) throw new IllegalStateException("wrong DLL");
    File out=new File(getScriptArgs()[0]);out.mkdirs();
    long base=currentProgram.getImageBase().getOffset();
    DecompInterface dec=new DecompInterface();dec.openProgram(currentProgram);
    Set<Address> entries=new LinkedHashSet<>();
    try(PrintWriter w=new PrintWriter(new File(out,"references.txt"),"UTF-8")) {
      for(int i=1;i<getScriptArgs().length;i++) {
        long rva=Long.parseLong(getScriptArgs()[i],16);Address a=toAddr(base+rva);
        w.printf("\nTARGET %x\n",rva);
        Function f=getFunctionAt(a);if(f!=null)entries.add(f.getEntryPoint());
        for(Reference r:getReferencesTo(a)){
          Function caller=getFunctionContaining(r.getFromAddress());
          w.printf("%x %s function=%s\n",r.getFromAddress().getOffset()-base,r.getReferenceType(),caller);
          if(caller!=null)entries.add(caller.getEntryPoint());
        }
      }
    }
    for(Address a:entries){
      Function f=getFunctionAt(a);String name="rva_"+Long.toHexString(a.getOffset()-base);
      disassemble(a);
      DecompileResults result=dec.decompileFunction(f,90,monitor);
      try(PrintWriter w=new PrintWriter(new File(out,name+".c"),"UTF-8")){
        if(result.decompileCompleted()&&result.getDecompiledFunction()!=null)w.println(result.getDecompiledFunction().getC());else w.println(result.getErrorMessage());
      }
      try(PrintWriter w=new PrintWriter(new File(out,name+".asm"),"UTF-8")){
        InstructionIterator it=currentProgram.getListing().getInstructions(f.getBody(),true);
        while(it.hasNext()){Instruction ins=it.next();w.printf("%08X %s%n",ins.getAddress().getOffset()-base,ins);}
      }
      println("Exported "+name);
    }
    dec.dispose();
  }
}
