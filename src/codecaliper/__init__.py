"""codecaliper — a cross-language code readability + complexity measurement
instrument with a versioned metric-to-syntax specification.

Every emitted number is traceable (spec version, fired rulings, grammar
versions) and reproducible (clock-free, hash-seed-free, order-stable per
platform). See ARCHITECTURE.md; honesty boundaries are in the docs and encoded
in the result types.
"""

from codecaliper._version import __version__
from codecaliper.api import DEFAULT_METRICS, Session, measure, measure_file
from codecaliper.errors import (
    CodecaliperError,
    GrammarLoadError,
    LanguageDetectionError,
    SpecError,
    StrictParseError,
    UnsupportedLanguageError,
)
from codecaliper.languages import available_languages, detect_language
from codecaliper.model import (
    Diagnostic,
    FeatureVectorResult,
    FileReport,
    FunctionReport,
    GrammarInfo,
    MetricValue,
    Provenance,
    RulingTrace,
    Span,
)
from codecaliper.readability import BW_FEATURE_NAMES, BW_FEATURE_ORDER_SHA
from codecaliper.spec import Ruling, iter_rulings, ruling, spec_version

__all__ = [
    "BW_FEATURE_NAMES",
    "BW_FEATURE_ORDER_SHA",
    "CodecaliperError",
    "DEFAULT_METRICS",
    "Diagnostic",
    "FeatureVectorResult",
    "FileReport",
    "FunctionReport",
    "GrammarInfo",
    "GrammarLoadError",
    "LanguageDetectionError",
    "MetricValue",
    "Provenance",
    "Ruling",
    "RulingTrace",
    "Session",
    "Span",
    "SpecError",
    "StrictParseError",
    "UnsupportedLanguageError",
    "__version__",
    "available_languages",
    "detect_language",
    "iter_rulings",
    "measure",
    "measure_file",
    "ruling",
    "spec_version",
]
