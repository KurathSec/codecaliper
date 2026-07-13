---
name: Bug report
about: A wrong number, a crash, or a labelling/diagnostic problem
labels: bug
---

## What happened

<!-- The command or API call, what codecaliper reported, and what you expected. -->

## Minimal input

```python
# the smallest source snippet that reproduces it
```

## Environment

<!-- Paste the FULL output of `codecaliper env`. The spec, grammar and binding
     versions determine which calibration applies. -->

```
$ codecaliper env
```

## For wrong-number reports

Numbers here are ruled, not guessed: run with `--explain` and check the ruling
IDs against `docs/spec/rulings.md` (or `codecaliper spec show <ID>`). If the
behaviour matches a ruling you disagree with, this is a **calibration
discussion**: say which ruling, and cite the counter-evidence (the tool, paper
or spec you believe is right).
