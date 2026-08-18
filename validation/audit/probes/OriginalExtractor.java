// Drive the ORIGINAL Buse-Weimer feature extractor over a directory of
// snippets and print the 25 values IT computes, one row per snippet.
//
// Everything here is the original implementation's own code: the detectors
// come from its ReadabilityDetectorSuite.getDefaultSuite(), and each Snippet
// is built from raw text the way the tool builds its own embedded data
// (new Snippet(String, int)). The driver only reads values back out.
//
// Each detector runs on its OWN fresh block, and the single block-level
// feature it sets is read back from that block. That is a deliberate
// work-around for a defect in the tool: MaxLineValueDetector.featureName()
// returns "max " + fd.featureNames(), concatenating the ARRAY OBJECT rather
// than its first element, and featureNames() calls featureName() again, so
// each call mints a new array with a different identity hash. The name a max
// feature is stored under therefore never equals the name the suite
// advertises, and looking it up by the advertised name always misses. Running
// one detector per block sidesteps the lookup entirely, so the values printed
// here are the ones the tool computes for all 25 features, including the five
// its own pipeline cannot retrieve.
//
// Compile and run against readability-original.jar, which bundles both the
// raykernel classes and Weka. Consumer: original_extractor_rerun.py.

import raykernel.apps.readability.detectors.ReadabilityDetectorSuite;
import raykernel.apps.readability.snippet.Snippet;
import raykernel.ml.feature.DetectorSuite;
import raykernel.ml.feature.Feature;
import raykernel.ml.feature.FeatureDetector;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.DirectoryStream;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.Iterator;
import java.util.List;

public final class OriginalExtractor {
    public static void main(String[] args) throws IOException {
        if (args.length != 2) {
            System.err.println("usage: OriginalExtractor <dir> <glob>");
            System.exit(2);
        }
        DetectorSuite ds = ReadabilityDetectorSuite.getDefaultSuite();
        List<FeatureDetector> detectors = new ArrayList<>();
        for (FeatureDetector fd : ds) {
            detectors.add(fd);
        }

        List<Path> files = new ArrayList<>();
        try (DirectoryStream<Path> d = Files.newDirectoryStream(Path.of(args[0]), args[1])) {
            d.forEach(files::add);
        }
        files.sort((p, q) -> Integer.compare(stem(p), stem(q)));

        // Header: the suite's own position, so the consumer maps by position
        // (five advertised names are unusable, see the class comment).
        StringBuilder header = new StringBuilder("snippet");
        for (int i = 0; i < detectors.size(); i++) {
            header.append("\tf").append(i + 1);
        }
        System.out.println(header);

        for (Path f : files) {
            String src = new String(Files.readAllBytes(f), StandardCharsets.UTF_8);
            StringBuilder row = new StringBuilder(Integer.toString(stem(f)));
            for (FeatureDetector fd : detectors) {
                Snippet s = new Snippet(src, stem(f));
                fd.runDetector(s);
                Iterator<Feature> it = s.featureIterator();
                if (!it.hasNext()) {
                    throw new IllegalStateException("detector set no block feature");
                }
                Feature only = it.next();
                if (it.hasNext()) {
                    throw new IllegalStateException("detector set more than one block feature");
                }
                row.append('\t').append(Float.toString(only.value()));
            }
            System.out.println(row);
        }
    }

    private static int stem(Path p) {
        String s = p.getFileName().toString();
        int dot = s.lastIndexOf('.');
        return Integer.parseInt(dot < 0 ? s : s.substring(0, dot));
    }
}
