from enum import IntEnum

from pydantic.dataclasses import dataclass


class MetricType(IntEnum):
    """
    Display types for `kevinbotlib.metrics.Metric`
    """

    RawType = 0
    """Display the value raw"""
    PercentageUsedType = 1
    """Display the value as a percentage used. Dashboards may assume that the percentage available is `1.0 - value`"""
    PercentageRemainingType = 2
    """Display the value as a percentage remaining. Dashboards may assume that the percentage used is `1.0 - value`"""
    TemperatureCelciusType = 3
    """Display the value as a temperature in Celcius. Dashboards may convert to Fahrenheit."""
    TemperatureFahrenheitType = 4
    """Display the value as a temperature in Fahrenheit. Dashboards may convert to Celcius."""
    BytesType = 5
    """Display the values as a number of bytes. Dashboards may convert it into human readable KB, MB, etc"""
    BooleanType = 6
    """Display the value as a boolean."""


@dataclass
class Metric:
    """
    A single system metric

    Examples: Memory Free, CPU Usage, CPU Temperature, etc
    """

    title: str
    """The title of the metric"""
    value: str | int | float | None = None
    """The value of the metric"""
    kind: MetricType = MetricType.RawType
    """How should the metric be displayed?"""


class SystemMetrics:
    """
    Keep track of various system metrics

    Example metrics: CPU usage, CPU temperature, Disk usage, etc...
    """

    def __init__(self) -> None:
        self._metrics: dict[str, Metric] = {}

    def add(self, identifier: str, metric: Metric) -> None:
        """Add a new metric

        Args:
            identifier (str): Metric identifier. Will not be displayed in dashboards.
            metric (Metric): The metric to add
        """
        self._metrics[identifier] = metric

    def update(self, identifier: str, value: str | float | None) -> None:
        """Update the value of a metric

        Args:
            identifier (str): The metric identifier to update
            value (str | int | float | None): The new value
        """
        self._metrics[identifier].value = value

    def get(self, identifier: str) -> Metric:
        """Retrieve the value of a metric

        Args:
            identifier (str): Identifier of the metric to get

        Returns:
            A system metric
        """
        return self._metrics[identifier]

    def getall(self) -> dict[str, Metric]:
        """Get all available system metrics

        Returns:
            Identifier-metric pair dictionary
        """
        return self._metrics
