import logging
import os
import ssl
import time
import warnings
from json import dumps
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from urllib3.exceptions import InsecureRequestWarning


def _parse_otlp_headers(raw_headers: str) -> dict[str, str]:
    headers: dict[str, str] = {}
    if not raw_headers:
        return headers

    for item in raw_headers.split(","):
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        key = key.strip()
        value = value.strip()
        if key:
            headers[key] = value
    return headers


def _signal_endpoint(base: str, suffix: str) -> str:
    endpoint = base.strip().rstrip("/")
    if endpoint.endswith(suffix):
        return endpoint
    return f"{endpoint}{suffix}"


def _is_true(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _build_exporter_kwargs(
    endpoint: str,
    headers: dict[str, str],
    allow_insecure_tls: bool,
) -> dict:
    kwargs = {
        "endpoint": endpoint,
        "headers": headers,
    }
    if allow_insecure_tls:
        # OTLP HTTP exporters pass this through to requests' `verify` argument.
        # False is required when endpoints use expired/self-signed certs.
        kwargs["certificate_file"] = False
    return kwargs


def _force_insecure_tls_on_exporter(exporter: object) -> None:
    # OTLP HTTP exporters keep a requests session internally.
    # This helper is intentionally defensive across SDK versions.
    direct_session = getattr(exporter, "_session", None)
    if direct_session is not None and hasattr(direct_session, "verify"):
        direct_session.verify = False

    # Some OTLP HTTP exporter versions read this value directly when calling
    # requests. Keep it explicitly false as a second safety net.
    if hasattr(exporter, "_certificate_file"):
        setattr(exporter, "_certificate_file", False)

    client = getattr(exporter, "_client", None)
    client_session = getattr(client, "_session", None) if client is not None else None
    if client_session is not None and hasattr(client_session, "verify"):
        client_session.verify = False

    if client is not None and hasattr(client, "_certificate_file"):
        setattr(client, "_certificate_file", False)


def _get_exporter_verify_value(exporter: object) -> object:
    direct_session = getattr(exporter, "_session", None)
    if direct_session is not None and hasattr(direct_session, "verify"):
        return getattr(direct_session, "verify")

    client = getattr(exporter, "_client", None)
    client_session = getattr(client, "_session", None) if client is not None else None
    if client_session is not None and hasattr(client_session, "verify"):
        return getattr(client_session, "verify")

    return "unknown"


def _get_exporter_certificate_value(exporter: object) -> object:
    certificate = getattr(exporter, "_certificate_file", "unknown")
    if certificate != "unknown":
        return certificate

    client = getattr(exporter, "_client", None)
    return getattr(client, "_certificate_file", "unknown")


class OTelContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        span = trace.get_current_span()
        span_context = span.get_span_context() if span else None
        if span_context and span_context.is_valid:
            record.trace_id = f"{span_context.trace_id:032x}"
            record.span_id = f"{span_context.span_id:016x}"
        else:
            record.trace_id = "-"
            record.span_id = "-"
        return True


class LokiHTTPHandler(logging.Handler):
    def __init__(
        self,
        push_url: str,
        service_name: str,
        environment: str,
        headers: dict[str, str],
        allow_insecure_tls: bool,
        timeout_seconds: float,
    ) -> None:
        super().__init__()
        self.push_url = push_url
        self.service_name = service_name
        self.environment = environment
        self.headers = headers
        self.allow_insecure_tls = allow_insecure_tls
        self.timeout_seconds = timeout_seconds

    def _context(self):
        if self.push_url.startswith("https") and self.allow_insecure_tls:
            return ssl._create_unverified_context()
        return None

    def emit(self, record: logging.LogRecord) -> None:
        try:
            ts_ns = str(int(time.time() * 1_000_000_000))
            message = self.format(record)
            labels = {
                "service": self.service_name,
                "env": self.environment,
                "level": record.levelname,
                "logger": record.name,
                "trace_id": getattr(record, "trace_id", "-"),
                "span_id": getattr(record, "span_id", "-"),
            }
            payload = {
                "streams": [
                    {
                        "stream": labels,
                        "values": [[ts_ns, message]],
                    }
                ]
            }

            req = Request(
                self.push_url,
                data=dumps(payload).encode("utf-8"),
                method="POST",
                headers={"Content-Type": "application/json", **self.headers},
            )
            with urlopen(req, timeout=self.timeout_seconds, context=self._context()):
                return
        except (HTTPError, URLError, TimeoutError):
            self.handleError(record)


def setup_observability() -> tuple[trace.Tracer, metrics.Meter, logging.Logger]:
    service_name = os.getenv("OTEL_SERVICE_NAME", "meal-agent-no-butter")
    service_version = os.getenv("OTEL_SERVICE_VERSION", "0.1.0")
    environment = os.getenv("OTEL_ENVIRONMENT", "dev")

    base_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "https://otel.internal.nivetek.com")
    traces_endpoint = os.getenv(
        "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT",
        _signal_endpoint(base_endpoint, "/v1/traces"),
    )
    metrics_endpoint = os.getenv(
        "OTEL_EXPORTER_OTLP_METRICS_ENDPOINT",
        _signal_endpoint(base_endpoint, "/v1/metrics"),
    )
    headers = _parse_otlp_headers(os.getenv("OTEL_EXPORTER_OTLP_HEADERS", ""))
    allow_insecure_tls = _is_true(os.getenv("OTEL_EXPORTER_OTLP_INSECURE", "true"))

    loki_url = os.getenv("LOKI_URL", "https://loki.internal.nivetek.com")
    loki_push_path = os.getenv("LOKI_PUSH_PATH", "/loki/api/v1/push")
    loki_push_url = os.getenv("LOKI_PUSH_URL", f"{loki_url.rstrip('/')}{loki_push_path}")
    loki_headers = _parse_otlp_headers(os.getenv("LOKI_HEADERS", ""))
    loki_tenant = os.getenv("LOKI_TENANT_ID")
    if loki_tenant:
        loki_headers["X-Scope-OrgID"] = loki_tenant

    if allow_insecure_tls:
        warnings.filterwarnings("ignore", category=InsecureRequestWarning)

    resource = Resource.create(
        {
            "service.name": service_name,
            "service.version": service_version,
            "deployment.environment": environment,
        }
    )

    tracer_provider = TracerProvider(resource=resource)
    trace_exporter = OTLPSpanExporter(
        **_build_exporter_kwargs(
            endpoint=traces_endpoint,
            headers=headers,
            allow_insecure_tls=allow_insecure_tls,
        )
    )
    if allow_insecure_tls:
        _force_insecure_tls_on_exporter(trace_exporter)
    tracer_provider.add_span_processor(
        BatchSpanProcessor(trace_exporter)
    )
    trace.set_tracer_provider(tracer_provider)

    metric_exporter = OTLPMetricExporter(
        **_build_exporter_kwargs(
            endpoint=metrics_endpoint,
            headers=headers,
            allow_insecure_tls=allow_insecure_tls,
        )
    )
    if allow_insecure_tls:
        _force_insecure_tls_on_exporter(metric_exporter)
    metric_reader = PeriodicExportingMetricReader(
        metric_exporter
    )
    meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
    metrics.set_meter_provider(meter_provider)

    logger = logging.getLogger("meal_agent")
    logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())
    logger.handlers.clear()

    context_filter = OTelContextFilter()
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [trace_id=%(trace_id)s span_id=%(span_id)s] %(message)s"
    )

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    stream_handler.addFilter(context_filter)
    stream_handler.setLevel(logging.INFO)

    loki_handler = LokiHTTPHandler(
        push_url=loki_push_url,
        service_name=service_name,
        environment=environment,
        headers=loki_headers,
        allow_insecure_tls=allow_insecure_tls,
        timeout_seconds=float(os.getenv("LOKI_TIMEOUT_SECONDS", "5")),
    )
    loki_handler.setLevel(logging.INFO)
    loki_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    )
    loki_handler.addFilter(context_filter)

    logger.addHandler(stream_handler)
    logger.addHandler(loki_handler)
    logger.propagate = False

    logger.info(
        "Observability initialized: traces=%s metrics=%s logs=%s",
        traces_endpoint,
        metrics_endpoint,
        loki_push_url,
    )
    logger.warning("OTLP insecure TLS mode is %s", "ENABLED" if allow_insecure_tls else "DISABLED")
    logger.info(
        "Exporter TLS verify flags: traces=%s metrics=%s",
        _get_exporter_verify_value(trace_exporter),
        _get_exporter_verify_value(metric_exporter),
    )
    logger.info(
        "Exporter certificate settings: traces=%s metrics=%s",
        _get_exporter_certificate_value(trace_exporter),
        _get_exporter_certificate_value(metric_exporter),
    )
    logger.info("Loki direct logging enabled at %s", loki_push_url)

    return (
        trace.get_tracer("meal-agent"),
        metrics.get_meter("meal-agent"),
        logger,
    )
