# API reference

Everything public is importable from the top-level `codecaliper` package.
All result types are frozen, slotted dataclasses: immutable, clock-free, and
serialized deterministically. The two entry points:

```python
from codecaliper import measure, measure_file, Session
```

`Session` caches loaded grammars across calls; `measure`/`measure_file` are
one-shot conveniences with the same keyword surface.

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

The mapping specification ships as package data and is queryable at runtime
(the CLI's `spec show` is a thin wrapper over this):

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
