# API reference

Everything public is importable from the top-level `codecaliper` package. All
result types are frozen, slotted dataclasses: immutable, clock-free, serialized
deterministically. The entry points:

```python
from codecaliper import measure, measure_file, Session
```

`Session` is a validated, reusable option set: metrics, feature sets,
granularity, cognitive mode, `explain` and `strict`, checked once in
`__init__` (an unknown metric or mode raises `CodecaliperError` there rather
than at the first file), then applied to every call. `measure` and
`measure_file` take the same keywords and build a throwaway `Session` per call,
so measuring a corpus one file at a time revalidates the same options once per
file. Use a `Session` when you are measuring more than one thing under one
configuration.

Grammar loading is not what a `Session` buys you. Adapters (and the tree-sitter
parser each one lazily loads) are cached process-wide by a `functools.cache` on
`get_adapter`, so the second plain `measure()` call reuses the same adapter
object the first one loaded, with or without a `Session`. A `Session` carries no
instance-level cache.

## Measuring

::: codecaliper.api.Session

::: codecaliper.measure

::: codecaliper.measure_file

## Results

::: codecaliper.model.FileReport

::: codecaliper.model.FunctionReport

::: codecaliper.model.MetricValue

::: codecaliper.model.FeatureVectorResult

::: codecaliper.model.Diagnostic

::: codecaliper.model.Provenance

::: codecaliper.model.GrammarInfo

::: codecaliper.model.Span

## Spec introspection

The mapping specification ships as package data and is queryable at runtime.
The CLI's `spec show` is a thin wrapper over these:

::: codecaliper.spec.spec_version

::: codecaliper.spec.ruling

::: codecaliper.spec.iter_rulings

::: codecaliper.spec.Ruling

## Errors

::: codecaliper.errors
    options:
      members:
        - CodecaliperError
        - GrammarLoadError
        - LanguageDetectionError
        - UnsupportedLanguageError
        - StrictParseError
        - SpecError
