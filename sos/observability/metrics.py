"""
SOS Metrics.

Lightweight Prometheus-compatible metrics primitives (no external deps).
"""

from __future__ import annotations

from dataclasses import dataclass
import re
import time
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

_METRIC_NAME_RE = re.compile(r"^[a-zA-Z_:][a-zA-Z0-9_:]*$")
_LABEL_NAME_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def _escape_label_value(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


def _format_labels(label_names: Sequence[str], label_values: Sequence[str]) -> str:
    if not label_names:
        return ""
    parts = [
        f'{name}="{_escape_label_value(value)}"'
        for name, value in zip(label_names, label_values, strict=True)
    ]
    return "{" + ",".join(parts) + "}"


def _validate_metric_name(name: str) -> None:
    if not _METRIC_NAME_RE.match(name):
        raise ValueError(f"Invalid metric name: {name!r}")


def _validate_label_names(label_names: Sequence[str]) -> None:
    for label in label_names:
        if not _LABEL_NAME_RE.match(label):
            raise ValueError(f"Invalid label name: {label!r}")


class MetricsRegistry:
    def __init__(self) -> None:
        self._metrics: Dict[str, Metric] = {}

    def register(self, metric: Metric) -> None:
        if metric.name in self._metrics:
            raise ValueError(f"Metric already registered: {metric.name}")
        self._metrics[metric.name] = metric

    def counter(self, name: str, description: str, label_names: Sequence[str] = ()) -> "Counter":
        metric = Counter(name=name, description=description, label_names=tuple(label_names))
        self.register(metric)
        return metric

    def gauge(self, name: str, description: str, label_names: Sequence[str] = ()) -> "Gauge":
        metric = Gauge(name=name, description=description, label_names=tuple(label_names))
        self.register(metric)
        return metric

    def histogram(
        self,
        name: str,
        description: str,
        label_names: Sequence[str] = (),
        buckets: Optional[Sequence[float]] = None,
    ) -> "Histogram":
        metric = Histogram(
            name=name,
            description=description,
            label_names=tuple(label_names),
            buckets=buckets,
        )
        self.register(metric)
        return metric

    def render_prometheus(self) -> str:
        lines: List[str] = []
        for metric in sorted(self._metrics.values(), key=lambda m: m.name):
            lines.extend(metric.render_prometheus())
        return "\n".join(lines) + ("\n" if lines else "")


class Metric:
    name: str
    description: str
    label_names: Tuple[str, ...]

    def render_prometheus(self) -> List[str]:
        raise NotImplementedError


class Counter(Metric):
    def __init__(self, name: str, description: str, label_names: Tuple[str, ...] = ()) -> None:
        _validate_metric_name(name)
        _validate_label_names(label_names)
        self.name = name
        self.description = description
        self.label_names = label_names
        self._values: Dict[Tuple[str, ...], float] = {}

    def labels(self, **labels: str) -> "CounterChild":
        if set(labels.keys()) != set(self.label_names):
            raise ValueError(f"Labels must match {self.label_names!r}")
        label_values = tuple(labels[name] for name in self.label_names)
        return CounterChild(self, label_values)

    def inc(self, amount: float = 1.0) -> None:
        if self.label_names:
            raise ValueError("This counter requires labels; use .labels(...).inc()")
        self._inc((), amount)

    def _inc(self, label_values: Tuple[str, ...], amount: float) -> None:
        if amount < 0:
            raise ValueError("Counter cannot be decreased")
        self._values[label_values] = self._values.get(label_values, 0.0) + amount

    def render_prometheus(self) -> List[str]:
        lines = [
            f"# HELP {self.name} {self.description}",
            f"# TYPE {self.name} counter",
        ]
        if not self._values:
            return lines
        for label_values, value in sorted(self._values.items()):
            labels = _format_labels(self.label_names, label_values)
            lines.append(f"{self.name}{labels} {value}")
        return lines


@dataclass(frozen=True)
class CounterChild:
    _parent: Counter
    _label_values: Tuple[str, ...]

    def inc(self, amount: float = 1.0) -> None:
        self._parent._inc(self._label_values, amount)


class Gauge(Metric):
    def __init__(self, name: str, description: str, label_names: Tuple[str, ...] = ()) -> None:
        _validate_metric_name(name)
        _validate_label_names(label_names)
        self.name = name
        self.description = description
        self.label_names = label_names
        self._values: Dict[Tuple[str, ...], float] = {}

    def labels(self, **labels: str) -> "GaugeChild":
        if set(labels.keys()) != set(self.label_names):
            raise ValueError(f"Labels must match {self.label_names!r}")
        label_values = tuple(labels[name] for name in self.label_names)
        return GaugeChild(self, label_values)

    def set(self, value: float) -> None:
        if self.label_names:
            raise ValueError("This gauge requires labels; use .labels(...).set()")
        self._set((), value)

    def inc(self, amount: float = 1.0) -> None:
        if self.label_names:
            raise ValueError("This gauge requires labels; use .labels(...).inc()")
        self._set((), self._values.get((), 0.0) + amount)

    def dec(self, amount: float = 1.0) -> None:
        self.inc(-amount)

    def _set(self, label_values: Tuple[str, ...], value: float) -> None:
        self._values[label_values] = value

    def render_prometheus(self) -> List[str]:
        lines = [
            f"# HELP {self.name} {self.description}",
            f"# TYPE {self.name} gauge",
        ]
        if not self._values:
            return lines
        for label_values, value in sorted(self._values.items()):
            labels = _format_labels(self.label_names, label_values)
            lines.append(f"{self.name}{labels} {value}")
        return lines


@dataclass(frozen=True)
class GaugeChild:
    _parent: Gauge
    _label_values: Tuple[str, ...]

    def set(self, value: float) -> None:
        self._parent._set(self._label_values, value)

    def inc(self, amount: float = 1.0) -> None:
        current = self._parent._values.get(self._label_values, 0.0)
        self._parent._set(self._label_values, current + amount)

    def dec(self, amount: float = 1.0) -> None:
        self.inc(-amount)


class Histogram(Metric):
    def __init__(
        self,
        name: str,
        description: str,
        label_names: Tuple[str, ...] = (),
        buckets: Optional[Sequence[float]] = None,
    ) -> None:
        _validate_metric_name(name)
        _validate_label_names(label_names)
        self.name = name
        self.description = description
        self.label_names = label_names
        self.buckets = tuple(sorted(buckets if buckets is not None else (0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0)))
        if not self.buckets:
            raise ValueError("Histogram buckets cannot be empty")

        self._bucket_counts: Dict[Tuple[str, ...], List[int]] = {}
        self._sums: Dict[Tuple[str, ...], float] = {}
        self._counts: Dict[Tuple[str, ...], int] = {}

    def labels(self, **labels: str) -> "HistogramChild":
        if set(labels.keys()) != set(self.label_names):
            raise ValueError(f"Labels must match {self.label_names!r}")
        label_values = tuple(labels[name] for name in self.label_names)
        return HistogramChild(self, label_values)

    def observe(self, value: float) -> None:
        if self.label_names:
            raise ValueError("This histogram requires labels; use .labels(...).observe()")
        self._observe((), value)

    def time(self) -> "HistogramTimer":
        if self.label_names:
            raise ValueError("This histogram requires labels; use .labels(...).time()")
        return HistogramTimer(self, ())

    def _observe(self, label_values: Tuple[str, ...], value: float) -> None:
        bucket_counts = self._bucket_counts.setdefault(label_values, [0 for _ in range(len(self.buckets) + 1)])
        index = None
        for i, boundary in enumerate(self.buckets):
            if value <= boundary:
                index = i
                break
        if index is None:
            index = len(self.buckets)  # +Inf bucket
        bucket_counts[index] += 1

        self._sums[label_values] = self._sums.get(label_values, 0.0) + value
        self._counts[label_values] = self._counts.get(label_values, 0) + 1

    def render_prometheus(self) -> List[str]:
        lines = [
            f"# HELP {self.name} {self.description}",
            f"# TYPE {self.name} histogram",
        ]
        if not self._counts:
            return lines

        for label_values in sorted(self._counts.keys()):
            counts = self._bucket_counts[label_values]
            cumulative = 0

            for i, boundary in enumerate(self.buckets):
                cumulative += counts[i]
                labels = _format_labels(
                    (*self.label_names, "le"),
                    (*label_values, str(boundary)),
                )
                lines.append(f"{self.name}_bucket{labels} {cumulative}")

            cumulative += counts[len(self.buckets)]
            labels = _format_labels(
                (*self.label_names, "le"),
                (*label_values, "+Inf"),
            )
            lines.append(f"{self.name}_bucket{labels} {cumulative}")

            labels = _format_labels(self.label_names, label_values)
            lines.append(f"{self.name}_sum{labels} {self._sums[label_values]}")
            lines.append(f"{self.name}_count{labels} {self._counts[label_values]}")

        return lines


@dataclass(frozen=True)
class HistogramChild:
    _parent: Histogram
    _label_values: Tuple[str, ...]

    def observe(self, value: float) -> None:
        self._parent._observe(self._label_values, value)

    def time(self) -> "HistogramTimer":
        return HistogramTimer(self._parent, self._label_values)


@dataclass(frozen=True)
class HistogramTimer:
    _histogram: Histogram
    _label_values: Tuple[str, ...]
    _start: float = 0.0

    def __enter__(self) -> "HistogramTimer":
        object.__setattr__(self, "_start", time.perf_counter())
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        duration = time.perf_counter() - self._start
        self._histogram._observe(self._label_values, duration)


REGISTRY = MetricsRegistry()


def render_prometheus(registry: MetricsRegistry = REGISTRY) -> str:
    return registry.render_prometheus()

