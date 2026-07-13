"""The codecaliper CLI (stdlib argparse, zero extra dependencies).

    codecaliper FILE... [--lang auto|python|java] [--json|--csv] ...
    codecaliper spec version | list | show RULING-ID
    codecaliper env                  # the calibration plate
    codecaliper cite [--format ...]  # methods-section template

Diagnostics go to stderr, data to stdout, so the CLI is pipeline-safe. Exit codes:
0 success, 1 usage/internal error, 2 completed with error-severity diagnostics.
"""

from __future__ import annotations

import argparse
import platform
import sys

from codecaliper._version import __version__
from codecaliper.errors import CodecaliperError


class _Parser(argparse.ArgumentParser):
    """argparse exits 2 on usage errors; our contract reserves 2 for
    'completed with error-severity diagnostics', so usage errors exit 1."""

    def error(self, message: str) -> None:  # type: ignore[override]
        self.print_usage(sys.stderr)
        print(f"{self.prog}: error: {message}", file=sys.stderr)
        raise SystemExit(1)


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    if args and args[0] in ("spec", "env", "cite"):
        return _dispatch_subcommand(args)
    return _cmd_measure(args)


def _measure_parser() -> argparse.ArgumentParser:
    p = _Parser(
        prog="codecaliper",
        description="A cross-language code readability + complexity measurement instrument.",
    )
    p.add_argument("files", nargs="+", metavar="FILE")
    p.add_argument("--lang", default="auto", choices=["auto", "python", "java"])
    fmt = p.add_mutually_exclusive_group()
    fmt.add_argument("--json", action="store_true", help="JSON output (default)")
    fmt.add_argument("--csv", action="store_true", help="wide-format CSV output")
    p.add_argument("--metrics", default=",".join(
        ("cyclomatic", "cognitive", "halstead", "maintainability_index", "loc")))
    p.add_argument("--no-readability", action="store_true")
    p.add_argument("--bw-granularity", default="file",
                   choices=["snippet", "function", "file"])
    p.add_argument("--sonar-compat", action="store_true",
                   help="cognitive complexity in sonar-compat mode (default: whitepaper)")
    p.add_argument("--explain", action="store_true",
                   help="attach per-increment ruling traces (RulingTrace)")
    p.add_argument("--strict", action="store_true",
                   help="error exit on parse errors instead of measure-and-label")
    p.add_argument("-o", "--output", default=None)
    p.add_argument("--version", action="version", version=f"codecaliper {__version__}")
    return p


def _cmd_measure(argv: list[str]) -> int:
    from codecaliper import canonical
    from codecaliper.api import Session
    from codecaliper.errors import StrictParseError
    from codecaliper.languages import detect_language

    opts = _measure_parser().parse_args(argv)
    try:
        session = Session(
            metrics=tuple(m for m in opts.metrics.split(",") if m),
            readability=() if opts.no_readability else ("bw2010",),
            granularity=opts.bw_granularity,
            cognitive_mode="sonar-compat" if opts.sonar_compat else "whitepaper",
            explain=opts.explain,
            strict=opts.strict,
        )
    except CodecaliperError as exc:
        print(f"codecaliper: error: {exc}", file=sys.stderr)
        return 1
    reports = []
    had_error_diag = False
    try:
        for path in opts.files:
            lang = detect_language(path) if opts.lang == "auto" else opts.lang
            rep = session.measure_file(path, language=lang)
            reports.append(rep)
            for d in rep.diagnostics:
                print(f"{path}: {d.severity}: {d.code}: {d.message}", file=sys.stderr)
                if d.severity == "error":
                    had_error_diag = True
    except StrictParseError as exc:
        # --strict: an error-severity condition, per the documented exit contract
        print(f"codecaliper: error: {exc}", file=sys.stderr)
        return 2
    except (CodecaliperError, OSError) as exc:
        print(f"codecaliper: error: {exc}", file=sys.stderr)
        return 1

    if opts.csv:
        out = canonical.to_csv(reports)
    else:
        out = "".join(canonical.to_json(r) for r in reports)
    if opts.output:
        try:
            with open(opts.output, "w", encoding="utf-8") as f:
                f.write(out)
        except OSError as exc:
            print(f"codecaliper: error: {exc}", file=sys.stderr)
            return 1
    else:
        sys.stdout.write(out)
    return 2 if had_error_diag else 0


def _dispatch_subcommand(argv: list[str]) -> int:
    cmd, rest = argv[0], argv[1:]
    if cmd == "spec":
        return _cmd_spec(rest)
    if cmd == "env":
        return _cmd_env()
    if cmd == "cite":
        return _cmd_cite(rest)
    return 1  # pragma: no cover


def _cmd_spec(argv: list[str]) -> int:
    from codecaliper.spec import iter_rulings, ruling, spec_version

    p = _Parser(prog="codecaliper spec")
    sub = p.add_subparsers(dest="action", required=True)
    sub.add_parser("version")
    lst = sub.add_parser("list")
    lst.add_argument("--metric", default=None)
    lst.add_argument("--lang", default=None)
    show = sub.add_parser("show")
    show.add_argument("ruling_id")
    opts = p.parse_args(argv)

    if opts.action == "version":
        print(spec_version())
    elif opts.action == "list":
        for r in iter_rulings(metric=opts.metric, language=opts.lang):
            mode = f" [{r.mode}]" if r.mode else ""
            print(f"{r.id}  {r.status:<10} {r.title}{mode}")
    elif opts.action == "show":
        try:
            r = ruling(opts.ruling_id)
        except CodecaliperError as exc:
            print(f"codecaliper: error: {exc}", file=sys.stderr)
            return 1
        print(f"{r.id}: {r.title}")
        print(f"metric: {r.metric}   language: {r.language}   status: {r.status}"
              + (f"   mode: {r.mode}" if r.mode else ""))
        if r.superseded_by:
            print(f"superseded by: {r.superseded_by}")
        print(f"since spec: {r.since_spec}")
        if r.node_types:
            print(f"node types: {', '.join(r.node_types)}")
        if r.examples:
            print(f"normative cases: {', '.join(r.examples)}")
        print()
        print(r.statement)
    return 0


def _cmd_env() -> int:
    """The calibration plate: what bug reports and papers should quote."""
    from codecaliper.languages import available_languages, get_adapter
    from codecaliper.spec import spec_version

    print(f"codecaliper {__version__}")
    print(f"spec {spec_version()}")
    print(f"python {platform.python_version()} ({platform.system()} {platform.machine()})")
    try:
        import importlib.metadata

        print(f"tree-sitter {importlib.metadata.version('tree-sitter')} (binding)")
    except Exception:  # noqa: BLE001 - env report must never crash
        print("tree-sitter binding: not installed")
    for lang in available_languages():
        try:
            info = get_adapter(lang).grammar_info()
            flag = "calibrated" if info.validated else "UNVALIDATED"
            print(f"{info.package} {info.version} (ABI {info.abi_version}, {flag})")
        except CodecaliperError as exc:
            print(f"{lang}: grammar unavailable: {exc}")
    return 0


def _cmd_cite(argv: list[str]) -> int:
    from codecaliper.languages import available_languages, get_adapter
    from codecaliper.spec import spec_version

    p = _Parser(prog="codecaliper cite")
    p.add_argument("--format", default="text", choices=["text", "bibtex"])
    opts = p.parse_args(argv)
    grammars = []
    for lang in available_languages():
        try:
            info = get_adapter(lang).grammar_info()
            grammars.append(f"{info.package} {info.version}")
        except CodecaliperError:
            pass
    if opts.format == "bibtex":
        print(
            "@software{codecaliper,\n"
            "  author  = {Ji, Yuxiang},\n"
            "  title   = {codecaliper: a cross-language code readability and "
            "complexity measurement instrument},\n"
            f"  version = {{{__version__}}},\n"
            f"  note    = {{spec {spec_version()}; grammars: {', '.join(grammars)}}},\n"
            "  url     = {https://github.com/KurathSec/codecaliper}\n"
            "}"
        )
    else:
        print(
            f"Metrics were computed with codecaliper {__version__} under mapping "
            f"specification {spec_version()} (grammars: {', '.join(grammars)}); "
            "cognitive complexity in whitepaper mode unless stated; readability "
            "vectors are the raw Buse-Weimer 2010 feature set, with granularity "
            "and extrapolation as labelled in the output."
        )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
