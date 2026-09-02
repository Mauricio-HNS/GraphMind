# GraphMind analysis prompt

Analyze all charts in `charts/` as one dataset.

Answer only with findings supported by extracted evidence.

Focus on:

- trends over time;
- comparisons between charts and series;
- highest and lowest values;
- rankings;
- significant changes;
- possible anomalies.

For every numeric assertion, preserve the source chart and extracted values when available.
If the evidence is insufficient or confidence is low, explicitly mark the finding as requiring review instead of guessing.
