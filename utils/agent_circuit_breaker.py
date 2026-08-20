"""Circuit breaker pattern for LLM providers.

State machine: CLOSED → OPEN → HALF-OPEN → CLOSED

Prevents cascading failures by detecting degraded providers and falling back
automatically. Self-heals when the provider recovers.
"""

import logging
import time
from enum import Enum

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Blocked — provider failing
    HALF_OPEN = "half_open"  # Testing if provider recovered


class CircuitBreaker:
    """Per-provider circuit breaker with configurable thresholds."""

    def __init__(self, provider_name: str, failure_threshold: int = 3, cooldown_seconds: float = 60.0):
        self.provider_name = provider_name
        self.failure_threshold = failure_threshold
        self.cooldown_seconds = cooldown_seconds
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = 0.0
        self._half_open_allowed = True

    @property
    def state(self) -> CircuitState:
        """Current state, auto-transitioning OPEN → HALF_OPEN when cooldown expires."""
        if self._state == CircuitState.OPEN:
            elapsed = time.time() - self._last_failure_time
            if elapsed >= self.cooldown_seconds:
                self._state = CircuitState.HALF_OPEN
                self._half_open_allowed = True
                logger.info("Circuit breaker %s: OPEN → HALF_OPEN (cooldown expired)", self.provider_name)
        return self._state

    def record_success(self):
        """Record a successful call."""
        if self._state == CircuitState.HALF_OPEN:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count += 1
            logger.info("Circuit breaker %s: HALF_OPEN → CLOSED (provider recovered)", self.provider_name)
        elif self._state == CircuitState.CLOSED:
            self._failure_count = max(0, self._failure_count - 1)  # Decay failures on success
            self._success_count += 1

    def record_failure(self):
        """Record a failed call."""
        self._failure_count += 1
        self._last_failure_time = time.time()

        if self._state == CircuitState.HALF_OPEN:
            # Failed during half-open → back to OPEN with doubled cooldown
            self.cooldown_seconds *= 2
            self._state = CircuitState.OPEN
            logger.warning(
                "Circuit breaker %s: HALF_OPEN → OPEN (failed during test, cooldown now %ss)",
                self.provider_name,
                self.cooldown_seconds,
            )
        elif self._failure_count >= self.failure_threshold:
            self._state = CircuitState.OPEN
            logger.warning(
                "Circuit breaker %s: CLOSED → OPEN (%d consecutive failures)",
                self.provider_name,
                self._failure_count,
            )

    def allow_request(self) -> bool:
        """Check if a request should be allowed through."""
        current = self.state  # Trigger auto-transition check
        if current == CircuitState.CLOSED:
            return True
        if current == CircuitState.HALF_OPEN and self._half_open_allowed:
            self._half_open_allowed = False  # Only allow one test request
            return True
        return False

    def reset(self):
        """Reset the circuit breaker to closed state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self.cooldown_seconds = 60.0  # Reset doubled cooldown
        self._half_open_allowed = True

    def status(self) -> dict:
        """Return current circuit breaker status."""
        return {
            "provider": self.provider_name,
            "state": self.state.value,
            "failures": self._failure_count,
            "successes": self._success_count,
            "threshold": self.failure_threshold,
            "cooldown_seconds": self.cooldown_seconds,
        }


# Global circuit breaker registry — one per provider name
_breakers: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(provider_name: str, **kwargs) -> CircuitBreaker:
    """Get or create a circuit breaker for the given provider."""
    if provider_name not in _breakers:
        _breakers[provider_name] = CircuitBreaker(provider_name, **kwargs)
    return _breakers[provider_name]


def all_breakers_status() -> list[dict]:
    """Return status of all registered circuit breakers."""
    return [b.status() for b in _breakers.values()]
