"""
Domain Value Objects.
Immutable, self-validating objects representing domain concepts.
No infrastructure dependencies.
"""
from __future__ import annotations

import ipaddress
import re
from dataclasses import dataclass, field
from typing import ClassVar

from app.domain.exceptions import InvalidCIDRError, InvalidIPAddressError, ValidationError


@dataclass(frozen=True)
class IPAddress:
    """Validated IP address value object (IPv4 or IPv6)."""

    value: str
    _parsed: ipaddress.IPv4Address | ipaddress.IPv6Address = field(init=False, repr=False)

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "_parsed", ipaddress.ip_address(self.value))
        except ValueError as e:
            raise InvalidIPAddressError(self.value) from e

    @property
    def is_private(self) -> bool:
        return self._parsed.is_private

    @property
    def is_loopback(self) -> bool:
        return self._parsed.is_loopback

    @property
    def is_ipv4(self) -> bool:
        return isinstance(self._parsed, ipaddress.IPv4Address)

    @property
    def is_ipv6(self) -> bool:
        return isinstance(self._parsed, ipaddress.IPv6Address)

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class CIDRRange:
    """Validated CIDR notation network range."""

    value: str
    _parsed: ipaddress.IPv4Network | ipaddress.IPv6Network = field(init=False, repr=False)

    def __post_init__(self) -> None:
        try:
            object.__setattr__(self, "_parsed", ipaddress.ip_network(self.value, strict=False))
        except ValueError as e:
            raise InvalidCIDRError(self.value) from e

    @property
    def num_addresses(self) -> int:
        return self._parsed.num_addresses

    @property
    def is_private(self) -> bool:
        return self._parsed.is_private

    def contains(self, ip: IPAddress) -> bool:
        return ipaddress.ip_address(ip.value) in self._parsed

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class PortNumber:
    """Validated network port number."""

    MIN_PORT: ClassVar[int] = 1
    MAX_PORT: ClassVar[int] = 65535

    value: int

    def __post_init__(self) -> None:
        if not (self.MIN_PORT <= self.value <= self.MAX_PORT):
            raise ValidationError(
                field="port",
                message=f"Port must be between {self.MIN_PORT} and {self.MAX_PORT}, got {self.value}",
            )

    @property
    def is_well_known(self) -> bool:
        return self.value <= 1023

    @property
    def is_registered(self) -> bool:
        return 1024 <= self.value <= 49151

    def __str__(self) -> str:
        return str(self.value)


@dataclass(frozen=True)
class CVSSScore:
    """CVSS score value object with severity classification."""

    value: float

    def __post_init__(self) -> None:
        if not (0.0 <= self.value <= 10.0):
            raise ValidationError(
                field="cvss_score",
                message=f"CVSS score must be between 0.0 and 10.0, got {self.value}",
            )

    @property
    def severity(self) -> str:
        if self.value == 0.0:
            return "none"
        if self.value < 4.0:
            return "low"
        if self.value < 7.0:
            return "medium"
        if self.value < 9.0:
            return "high"
        return "critical"

    @property
    def is_critical(self) -> bool:
        return self.value >= 9.0

    def __str__(self) -> str:
        return f"{self.value:.1f}"


@dataclass(frozen=True)
class CVEIdentifier:
    """Validated CVE ID value object."""

    PATTERN: ClassVar[re.Pattern[str]] = re.compile(
        r"^CVE-\d{4}-\d{4,}$", re.IGNORECASE
    )

    value: str

    def __post_init__(self) -> None:
        normalized = self.value.upper()
        object.__setattr__(self, "value", normalized)
        if not self.PATTERN.match(normalized):
            raise ValidationError(
                field="cve_id",
                message=f"'{self.value}' is not a valid CVE identifier (expected CVE-YYYY-NNNNN)",
            )

    @property
    def year(self) -> int:
        return int(self.value.split("-")[1])

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class OrganizationSlug:
    """URL-safe organization identifier."""

    PATTERN: ClassVar[re.Pattern[str]] = re.compile(r"^[a-z0-9][a-z0-9-]{2,61}[a-z0-9]$")

    value: str

    def __post_init__(self) -> None:
        if not self.PATTERN.match(self.value):
            raise ValidationError(
                field="slug",
                message=(
                    "Slug must be 4-63 characters, lowercase alphanumeric and hyphens, "
                    "not starting or ending with a hyphen"
                ),
            )

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class SecurityHealthScore:
    """
    Computed security health score (0-100).
    Higher is better. Formula based on weighted vulnerability counts.
    """

    value: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int

    def __post_init__(self) -> None:
        if not (0 <= self.value <= 100):
            raise ValidationError(
                field="health_score",
                message=f"Health score must be 0-100, got {self.value}",
            )

    @classmethod
    def calculate(
        cls,
        critical: int,
        high: int,
        medium: int,
        low: int,
        total_assets: int = 1,
    ) -> SecurityHealthScore:
        """
        Score formula:
        - Start at 100
        - Deduct: critical * 20 + high * 8 + medium * 2 + low * 0.5
        - Normalize by asset count to avoid penalizing larger orgs unfairly
        - Floor at 0
        """
        if total_assets <= 0:
            total_assets = 1

        deduction = (
            (critical * 20)
            + (high * 8)
            + (medium * 2)
            + (low * 0.5)
        )
        normalized_deduction = deduction / total_assets
        raw_score = max(0, 100 - normalized_deduction)
        score = max(0, min(100, int(raw_score)))

        return cls(
            value=score,
            critical_count=critical,
            high_count=high,
            medium_count=medium,
            low_count=low,
        )

    @property
    def letter_grade(self) -> str:
        if self.value >= 90:
            return "A"
        if self.value >= 80:
            return "B"
        if self.value >= 70:
            return "C"
        if self.value >= 60:
            return "D"
        return "F"

    @property
    def label(self) -> str:
        if self.value >= 80:
            return "Healthy"
        if self.value >= 60:
            return "Fair"
        if self.value >= 40:
            return "At Risk"
        return "Critical"
