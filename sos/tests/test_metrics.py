import unittest

from sos.observability.metrics import MetricsRegistry


class TestMetrics(unittest.TestCase):
    def test_counter_with_labels_renders_prometheus(self):
        registry = MetricsRegistry()
        counter = registry.counter(
            name="sos_requests_total",
            description="Total requests",
            label_names=("service", "status"),
        )

        counter.labels(service="engine", status="success").inc()
        counter.labels(service="engine", status="error").inc(2)

        rendered = registry.render_prometheus()
        self.assertIn("# TYPE sos_requests_total counter", rendered)
        self.assertIn('sos_requests_total{service="engine",status="success"} 1.0', rendered)
        self.assertIn('sos_requests_total{service="engine",status="error"} 2.0', rendered)

    def test_histogram_renders_buckets_sum_count(self):
        registry = MetricsRegistry()
        histogram = registry.histogram(
            name="sos_request_duration_seconds",
            description="Request duration",
            label_names=("service",),
            buckets=(0.1, 0.5),
        )

        histogram.labels(service="engine").observe(0.2)

        rendered = registry.render_prometheus()
        self.assertIn("# TYPE sos_request_duration_seconds histogram", rendered)
        self.assertIn('sos_request_duration_seconds_bucket{service="engine",le="0.1"} 0', rendered)
        self.assertIn('sos_request_duration_seconds_bucket{service="engine",le="0.5"} 1', rendered)
        self.assertIn('sos_request_duration_seconds_bucket{service="engine",le="+Inf"} 1', rendered)
        self.assertIn('sos_request_duration_seconds_sum{service="engine"} 0.2', rendered)
        self.assertIn('sos_request_duration_seconds_count{service="engine"} 1', rendered)


if __name__ == "__main__":
    unittest.main()

