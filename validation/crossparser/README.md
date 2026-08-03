# Cross-parser check: is the parse anatomy parser-stable?

The Buse-Weimer parse anatomy reported by the instrument (27/100 snippets
clean as written, 29 with the CORE-JAVA-0001 scaffold, 84 brace-balanced, 94
balanced+scaffold) is measured under one grammar family, tree-sitter-java.
This lane re-measures the same 100 tracked snippets, under byte-identical
repair variants, with two architecturally different Java front ends:

- **javac** (`JavacTask.parse()`, the JDK compiler's own parser, syntax only,
  no name resolution) -- a compiler-grade front end;
- **JavaParser** (`javaparser-core`, sha256-pinned by `fetch.py`) -- an
  independently implemented library parser common in SE research pipelines.

## Recorded result (`results.txt`, regenerate, never edit)

```
front ends: javac 21.0.11 (JavacTask.parse) | javaparser-core 3.26.2
javac (compilation-unit entry):
  as written                       clean=   0/100
  scaffold allowed                 clean=  27/100
  brace-balanced                   clean=   0/100
  brace-balanced + scaffold        clean=  84/100
javaparser (ParseStart=COMPILATION_UNIT):
  as written                       clean=   0/100
  scaffold allowed                 clean=  29/100
  brace-balanced                   clean=   0/100
  brace-balanced + scaffold        clean=  93/100
javaparser, as written, other entry points:
  classbody entry                  clean=   3/100
  block entry (brace-wrapped)      clean=  26/100
  any entry (cu|classbody|block)   clean=  29/100
reference, tree-sitter-java 0.23.5 (the instrument): as written 27, scaffold 29, brace-balanced 84, balanced+scaffold 94
```

## Reading it

Strict compilation-unit front ends accept ZERO snippets as written: none of
the 100 is a compilation unit. Once the entry-point mismatch is repaired (the
scaffold) or side-stepped (JavaParser's lenient entry points), the three front
ends agree closely on how many fragments remain interior-truncated: 27 (javac,
scaffolded), 29 (JavaParser, scaffolded or any entry), 27-29 (tree-sitter).
Under brace balancing plus scaffold they read 84, 93 and 94. So the anatomy is
parser-stable once entry-point tolerance is accounted for, and the
tree-sitter-based headline (73/100 fail as written) is the LENIENT reading: a
compiler-grade front end rejects all 100 as written.

## Reproducing

```bash
python validation/crossparser/fetch.py       # javaparser-core into cache/ (gitignored), sha256-verified
python validation/crossparser/run_crossparser.py   # needs a JDK (javac/java) on PATH or JAVA_HOME
```

Recorded results were produced under Temurin 21.0.11. The lane consumes only
the TRACKED snippet pins (`../bw_faithfulness/derived/arbitration_inputs/`);
nothing third-party is committed (`cache/` is gitignored). A missing
prerequisite is a hard error, never a SKIP.
