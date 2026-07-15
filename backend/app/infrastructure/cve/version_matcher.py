"""
CPE and version string matching engine.

This module solves the hardest part of CVE correlation:
determining whether a given version string is within a CVE's
affected version range.

Three matching strategies:
  1. CPE string parse   — extract product/version from CPE 2.3 string
  2. Version range      — compare against versionStart/End bounds
  3. Fuzzy semver       — normalise non-semver strings before comparison

CPE 2.3 format:
  cpe:2.3:{part}:{vendor}:{product}:{version}:{update}:{edition}:{language}
                                              ^^^^^^^^^
  e.g. cpe:2.3:a:apache:http_server:2.4.51:*:*:*:*:*:*:*
                                    ^^^^^^
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Sequence

import structlog

logger = structlog.get_logger(__name__)

# Regex to split a CPE 2.3 string into its components
_CPE_RE = re.compile(
    r"^cpe:2\.3:"
    r"(?P<part>[aoh\*\-]):"       # application | os | hardware
    r"(?P<vendor>[^:]+):"
    r"(?P<product>[^:]+):"
    r"(?P<version>[^:]+):"
    r"(?P<update>[^:]+):",
    re.IGNORECASE,
)

# Normalise version strings: strip leading 'v', collapse spaces
_VERSION_CLEAN_RE = re.compile(r"^v", re.IGNORECASE)
_NON_SEMVER_RE    = re.compile(r"[^0-9.\-+]")


@dataclass(frozen=True)
class CPEComponents:
    """Parsed components of a CPE 2.3 string."""
    part:    str
    vendor:  str
    product: str
    version: str    # "*" means any version
    raw:     str    # original CPE string


@dataclass(frozen=True)
class VersionRange:
    """Affected version range from a CPE match entry."""
    cpe_base:                str          # CPE without version (for product match)
    version_start_including: str | None
    version_start_excluding: str | None
    version_end_including:   str | None
    version_end_excluding:   str | None

    def is_any_version(self) -> bool:
        return all(
            v is None for v in [
                self.version_start_including,
                self.version_start_excluding,
                self.version_end_including,
                self.version_end_excluding,
            ]
        )


class VersionMatcher:
    """
    Matches a (service_name, version) pair against a set of CPE strings
    and version ranges.

    Usage:
        matcher = VersionMatcher()
        score   = matcher.score_cpe_list(
            service="apache http server",
            version="2.4.51",
            cpe_strings=["cpe:2.3:a:apache:http_server:2.4.51:*:*:*:*:*:*:*"],
        )
        # score > 0 → match
    """

    # Service name normalisation aliases
    # Maps common service names → CPE product substrings
    _ALIASES: dict[str, list[str]] = {
        "apache":          ["apache", "http_server", "httpd"],
        "apache httpd":    ["http_server", "httpd", "apache"],
        "apache http server": ["http_server"],
        "nginx":           ["nginx"],
        "openssh":         ["openssh"],
        "ssh":             ["openssh", "ssh"],
        "openssl":         ["openssl"],
        "mysql":           ["mysql", "mysql_server"],
        "mariadb":         ["mariadb"],
        "postgresql":      ["postgresql"],
        "postgres":        ["postgresql"],
        "redis":           ["redis"],
        "tomcat":          ["tomcat", "apache_tomcat"],
        "wordpress":       ["wordpress"],
        "php":             ["php"],
        "python":          ["python"],
        "node":            ["node.js", "nodejs"],
        "nodejs":          ["node.js", "nodejs"],
        "iis":             ["iis", "internet_information_services"],
        "vsftpd":          ["vsftpd"],
        "proftpd":         ["proftpd"],
        "exim":            ["exim"],
        "sendmail":        ["sendmail"],
        "dovecot":         ["dovecot"],
        "samba":           ["samba"],
        "bind":            ["bind", "named"],
        "dnsmasq":         ["dnsmasq"],
        "curl":            ["curl", "libcurl"],
        "log4j":           ["log4j", "log4j2"],
        "spring":          ["spring_framework", "spring_boot"],
        "struts":          ["struts", "apache_struts"],
    }

    def score_cpe_list(
        self,
        service: str,
        version: str,
        cpe_strings: Sequence[str],
    ) -> float:
        """
        Score how well this (service, version) matches the given CPE list.

        Returns:
            0.0  — no match
            0.5  — product matches but version not confirmable
            0.8  — product matches, version in range
            1.0  — exact CPE match including version
        """
        if not cpe_strings:
            return 0.0

        service_norm = self._normalise_name(service)
        version_norm = self._normalise_version(version)

        best_score = 0.0

        for cpe_str in cpe_strings:
            parsed = self._parse_cpe(cpe_str)
            if parsed is None:
                continue

            # Step 1: Does this CPE match the service name?
            if not self._product_matches(service_norm, parsed):
                continue

            # Step 2: Does the CPE version match?
            cpe_version = parsed.version
            if cpe_version in ("*", "-", ""):
                # Any-version CPE — product match confirmed, version unknown
                best_score = max(best_score, 0.5)
            elif cpe_version == version_norm:
                # Exact version match
                return 1.0
            elif self._version_in_range(version_norm, cpe_version):
                best_score = max(best_score, 0.8)
            else:
                # Product matched, version didn't
                best_score = max(best_score, 0.3)

        return best_score

    def match_version_range(
        self,
        version: str,
        vrange:  VersionRange,
    ) -> bool:
        """
        Check whether `version` falls within a VersionRange.
        Handles all four range bound types from NVD.
        """
        if vrange.is_any_version():
            return True

        version_norm = self._normalise_version(version)

        try:
            v = _parse_version(version_norm)

            if vrange.version_start_including:
                lo = _parse_version(self._normalise_version(vrange.version_start_including))
                if v < lo:
                    return False

            if vrange.version_start_excluding:
                lo = _parse_version(self._normalise_version(vrange.version_start_excluding))
                if v <= lo:
                    return False

            if vrange.version_end_including:
                hi = _parse_version(self._normalise_version(vrange.version_end_including))
                if v > hi:
                    return False

            if vrange.version_end_excluding:
                hi = _parse_version(self._normalise_version(vrange.version_end_excluding))
                if v >= hi:
                    return False

            return True

        except Exception as exc:
            logger.debug(
                "version_range_parse_error",
                version=version,
                error=str(exc),
            )
            # Fallback: string prefix match
            return self._fuzzy_version_match(version_norm, vrange)

    def service_matches_cpe(self, service: str, cpe_str: str) -> bool:
        """True if the service name plausibly matches the CPE product."""
        parsed = self._parse_cpe(cpe_str)
        if not parsed:
            return False
        return self._product_matches(self._normalise_name(service), parsed)

    # ── Private helpers ────────────────────────────────────────

    @staticmethod
    @lru_cache(maxsize=4096)
    def _parse_cpe(cpe_str: str) -> CPEComponents | None:
        m = _CPE_RE.match(cpe_str)
        if not m:
            return None
        return CPEComponents(
            part=    m.group("part").lower(),
            vendor=  m.group("vendor").lower(),
            product= m.group("product").lower(),
            version= m.group("version").lower(),
            raw=     cpe_str,
        )

    @staticmethod
    def _normalise_name(name: str) -> str:
        """Lowercase, strip punctuation, collapse spaces."""
        name = name.lower().strip()
        name = re.sub(r"[_\-/]", " ", name)
        name = re.sub(r"\s+", " ", name)
        return name

    @staticmethod
    def _normalise_version(version: str) -> str:
        """Strip leading 'v', lowercase."""
        v = version.strip().lower()
        v = _VERSION_CLEAN_RE.sub("", v)
        return v

    def _product_matches(self, service_norm: str, cpe: CPEComponents) -> bool:
        """
        Does the normalised service name match this CPE's product?
        Checks aliases and substring matches.
        """
        product = cpe.product.replace("_", " ").replace("-", " ")
        vendor  = cpe.vendor.replace("_", " ").replace("-", " ")

        # Direct substring check
        if service_norm in product or product in service_norm:
            return True
        if service_norm in vendor or vendor in service_norm:
            return True

        # Alias lookup
        for alias_key, alias_products in self._ALIASES.items():
            if alias_key in service_norm or service_norm in alias_key:
                for ap in alias_products:
                    if ap in cpe.product or cpe.product in ap:
                        return True

        # Token overlap check (≥50% of tokens match)
        service_tokens = set(service_norm.split())
        product_tokens = set(product.split()) | set(vendor.split())
        if service_tokens and product_tokens:
            overlap = service_tokens & product_tokens
            if len(overlap) / max(len(service_tokens), 1) >= 0.5:
                return True

        return False

    @staticmethod
    def _version_in_range(version: str, cpe_version: str) -> bool:
        """
        Lightweight check: does `version` match or extend `cpe_version`?
        e.g. version="2.4.51-r1" matches cpe_version="2.4.51"
        """
        return version.startswith(cpe_version) or cpe_version.startswith(version)

    def _fuzzy_version_match(
        self, version: str, vrange: VersionRange
    ) -> bool:
        """
        Last-resort string-based version range check for unparseable versions.
        Compares lexicographically — unreliable but better than no match.
        """
        try:
            lo_inc = vrange.version_start_including
            lo_exc = vrange.version_start_excluding
            hi_inc = vrange.version_end_including
            hi_exc = vrange.version_end_excluding

            if lo_inc and version < self._normalise_version(lo_inc):
                return False
            if lo_exc and version <= self._normalise_version(lo_exc):
                return False
            if hi_inc and version > self._normalise_version(hi_inc):
                return False
            if hi_exc and version >= self._normalise_version(hi_exc):
                return False
            return True
        except Exception:
            return False


# ── Version parsing helper ─────────────────────────────────────

class _ParsedVersion:
    """
    Simple version parser that handles semver + common non-semver patterns.
    Does not depend on `packaging` library to keep deps minimal.

    Supports: 1.2.3, 1.2.3-r4, 1.2.3p1, 1.2.3.4
    """

    def __init__(self, version_str: str) -> None:
        self._raw = version_str
        self._parts = self._parse(version_str)

    @staticmethod
    def _parse(v: str) -> tuple[int, ...]:
        # Strip non-numeric suffix for comparison (e.g. "2.4.51-r1" → "2.4.51")
        numeric_part = re.split(r"[^0-9.]", v)[0]
        parts = []
        for segment in numeric_part.split(".")[:4]:
            try:
                parts.append(int(segment))
            except ValueError:
                parts.append(0)
        # Pad to 4 components
        while len(parts) < 4:
            parts.append(0)
        return tuple(parts)

    def __lt__(self, other: "_ParsedVersion") -> bool:
        return self._parts < other._parts

    def __le__(self, other: "_ParsedVersion") -> bool:
        return self._parts <= other._parts

    def __gt__(self, other: "_ParsedVersion") -> bool:
        return self._parts > other._parts

    def __ge__(self, other: "_ParsedVersion") -> bool:
        return self._parts >= other._parts

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, _ParsedVersion):
            return NotImplemented
        return self._parts == other._parts

    def __repr__(self) -> str:
        return f"_ParsedVersion({self._raw!r} → {self._parts})"


def _parse_version(version_str: str) -> _ParsedVersion:
    return _ParsedVersion(version_str)
