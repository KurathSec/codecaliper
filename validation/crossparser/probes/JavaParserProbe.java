// Parse every .java file in a directory with JavaParser (an independently
// implemented Java parser) at a chosen entry point and print one line per
// file: "<name>\t<problem-count>". Entry points: cu (compilation unit),
// classbody (class body declarations), block (statement block). Part of the
// cross-parser lane; the aggregate consumer is run_crossparser.py.

import com.github.javaparser.JavaParser;
import com.github.javaparser.ParseResult;
import com.github.javaparser.ParseStart;
import com.github.javaparser.ParserConfiguration;
import com.github.javaparser.Providers;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.DirectoryStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

public final class JavaParserProbe {
    public static void main(String[] args) throws IOException {
        if (args.length != 2) {
            System.err.println("usage: JavaParserProbe <dir-of-java-files> <cu|classbody|block>");
            System.exit(2);
        }
        JavaParser parser = new JavaParser(new ParserConfiguration());
        List<Path> files = new ArrayList<>();
        try (DirectoryStream<Path> ds = Files.newDirectoryStream(Path.of(args[0]), "*.java")) {
            ds.forEach(files::add);
        }
        Collections.sort(files);
        for (Path file : files) {
            String src = Files.readString(file, StandardCharsets.UTF_8);
            ParseResult<?> result;
            switch (args[1]) {
                case "cu" -> result = parser.parse(src);
                case "classbody" -> result =
                        parser.parseBodyDeclaration(src);
                case "block" -> result = parser.parseBlock("{\n" + src + "\n}");
                default -> throw new IllegalArgumentException(args[1]);
            }
            System.out.println(file.getFileName() + "\t" + result.getProblems().size());
        }
    }
}
