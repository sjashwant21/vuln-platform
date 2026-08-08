"""
IP address validation utilities for scan targets.

Rules enforced:
  - Must be a valid IPv4/IPv6 address or CIDR block
  - Private, loopback, link-local, multicast ranges are BLOCKED
  - Cloud metadata endpoints are explicitly BLOCKED (SSRF prevention)
  - Subnets larger than /24 (IPv4) or /120 (IPv6) are BLOCKED (DoS prevention)
  - Maximum 10 targets per scan request
"""

from __future__ import annotations

import ipaddress
import re

# Cloud metadata endpoints that must always be blocked (SSRF prevention)
_BLOCKED_HOSTS: frozenset[str] = frozenset(
    {
        "169.254.169.254",  # AWS / Azure / GCP IMDS
        "100.100.100.200",  # Alibaba Cloud IMDS
        "metadata.google.internal",  # GCP metadata
        "metadata.goog",  # GCP metadata alias
    }
)

# Maximum subnet prefix lengths (smaller number = bigger subnet = blocked)
_MAX_SUBNET_PREFIX_V4 = 24   # /24 = 256 hosts max per scan
_MAX_SUBNET_PREFIX_V6 = 120  # /120 = 256 hosts max per scan


def validate_scan_target(value: str) -> str:
    """
    Validate and normalise a single scan target (IP or CIDR).

    Raises ValueError with a user-safe message if the target is invalid,
    private, reserved, or a cloud metadata endpoint.

    Returns the normalised string representation.
    """
    value = value.strip()

    if not value:
        raise ValueError("Scan target cannot be empty")

    # Block cloud metadata hostnames before IP parsing
    if value.lower() in _BLOCKED_HOSTS:
        raise ValueError(
            f"Scanning '{value}' is not permitted (cloud metadata endpoint)"
        )

    # Reject anything that looks like a hostname (contains non-IP chars beyond dots/colons/slashes)
    # We only allow IP addresses and CIDR notation — no DNS resolution in the scanner
    if re.search(r"[a-zA-Z]", value) and not value.startswith("::"):  # allow ::1 IPv6 notation
        raise ValueError(
            f"'{value}' appears to be a hostname. Only IP addresses and CIDR blocks are allowed"
        )

    try:
        network = ipaddress.ip_network(value, strict=False)
    except ValueError as err:
        raise ValueError(
            f"'{value}' is not a valid IP address or CIDR block "
            f"(e.g. '93.184.216.34' or '203.0.113.0/24')"
        ) from err

    # Block private / reserved ranges
    if network.is_private:
        raise ValueError(
            f"Scanning private network '{value}' is not allowed. "
            f"Use an internal scanner for private ranges."
        )
    if network.is_loopback:
        raise ValueError(f"Scanning loopback address '{value}' is not allowed")
    if network.is_link_local:
        raise ValueError(f"Scanning link-local address '{value}' is not allowed")
    if network.is_multicast:
        raise ValueError(f"Scanning multicast address '{value}' is not allowed")
    if network.is_unspecified:
        raise ValueError(f"'{value}' is an unspecified address and cannot be scanned")
    if network.is_reserved:
        raise ValueError(f"'{value}' is a reserved address and cannot be scanned")

    # Block subnets that are too large (DoS prevention)
    if isinstance(network, ipaddress.IPv4Network):
        if network.prefixlen < _MAX_SUBNET_PREFIX_V4:
            raise ValueError(
                f"Subnet '{value}' is too large (/{network.prefixlen}). "
                f"Maximum allowed is /{_MAX_SUBNET_PREFIX_V4} (256 hosts)."
            )
    elif isinstance(network, ipaddress.IPv6Network):
        if network.prefixlen < _MAX_SUBNET_PREFIX_V6:
            raise ValueError(
                f"IPv6 subnet '{value}' is too large (/{network.prefixlen}). "
                f"Maximum allowed is /{_MAX_SUBNET_PREFIX_V6}."
            )

    # Double-check each individual IP in small ranges against blocked list
    # (handles cases like CIDR that includes a metadata IP)
    for host_ip in ([network.network_address] if network.num_addresses == 1 else []):
        if str(host_ip) in _BLOCKED_HOSTS:
            raise ValueError(
                f"Target '{value}' resolves to a blocked address (cloud metadata endpoint)"
            )

    return str(network)


def validate_scan_targets(values: list[str]) -> list[str]:
    """
    Validate a list of scan targets. Returns a list of normalised targets.
    Raises ValueError listing all invalid entries if any fail.
    """
    if not values:
        raise ValueError("At least one scan target is required")

    if len(values) > 10:
        raise ValueError(
            f"Too many scan targets ({len(values)}). Maximum is 10 per request."
        )

    errors: list[str] = []
    validated: list[str] = []

    for target in values:
        try:
            validated.append(validate_scan_target(target))
        except ValueError as exc:
            errors.append(str(exc))

    if errors:
        raise ValueError("; ".join(errors))

    return validated
