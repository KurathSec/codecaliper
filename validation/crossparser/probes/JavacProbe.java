// Parse every .java file in a directory with javac's own front end
// (JavacTask.parse(): syntax only, no name resolution) and print one line per
// file: "<name>\t<error-diagnostic-count>". Part of the cross-parser lane; the
// aggregate consumer is run_crossparser.py.

import com.sun.source.util.JavacTask;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.DirectoryStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

import javax.tools.Diagnostic;
import javax.tools.DiagnosticCollector;
import javax.tools.JavaCompiler;
import javax.tools.JavaFileObject;
import javax.tools.StandardJavaFileManager;
import javax.tools.ToolProvider;

public final class JavacProbe {
    public static void main(String[] args) throws IOException {
        if (args.length != 1) {
            System.err.println("usage: JavacProbe <dir-of-java-files>");
            System.exit(2);
        }
        JavaCompiler compiler = ToolProvider.getSystemJavaCompiler();
        List<Path> files = new ArrayList<>();
        try (DirectoryStream<Path> ds = Files.newDirectoryStream(Path.of(args[0]), "*.java")) {
            ds.forEach(files::add);
        }
        Collections.sort(files);
        for (Path file : files) {
            DiagnosticCollector<JavaFileObject> diags = new DiagnosticCollector<>();
            try (StandardJavaFileManager fm =
                    compiler.getStandardFileManager(diags, null, StandardCharsets.UTF_8)) {
                JavacTask task = (JavacTask) compiler.getTask(
                        null, fm, diags, List.of("-proc:none"), null,
                        fm.getJavaFileObjects(file));
                task.parse();
            }
            long errors = diags.getDiagnostics().stream()
                    .filter(d -> d.getKind() == Diagnostic.Kind.ERROR)
                    .count();
            System.out.println(file.getFileName() + "\t" + errors);
        }
    }
}
