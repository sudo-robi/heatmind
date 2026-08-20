"""Circuit breaker pattern for API calls (Winner 3: Kong AI Auto Rollback).

Trips after consecutive failures, opens for a cooldown period, then half-opens
to test if the service recovered. Prevents cascading failures and runaway costs.
"""

import logging
import threading
import time
from enum import Enum

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        half_open_max: int = 1,
        name: str = "default",
    ):
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max = half_open_max
        self._lock = threading.Lock()

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: float = 0
        self._half_open_attempts = 0

    @property
    def state(self) -> CircuitState:
        with self._lock:
            self._check_cooldown()
            return self._state

    def record_success(self):
        with self._lock:
            if self._state == CircuitState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.half_open_max:
                    self._state = CircuitState.CLOSED
                    self._failure_count = 0
                    self._success_count = 0
                    logger.info(
                        "CircuitBreaker[%s]: HALF_OPEN -> CLOSED (recovered)",
                        self.name,
                    )
            elif self._state == CircuitState.CLOSED:
                self._failure_count = max(0, self._failure_count - 1)

    def record_failure(self):
        with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()

            if self._state == CircuitState.HALF_OPEN:
                self._state = CircuitState.OPEN
                logger.warning(
                    "CircuitBreaker[%s]: HALF_OPEN -> OPEN (failed during recovery)",
                    self.name,
                )
            elif self._failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN
                logger.warning(
                    "CircuitBreaker[%s]: CLOSED -> OPEN (%d consecutive failures)",
                    self.name,
                    self._failure_count,
                )

    def allow_request(self) -> bool:
        state = self.state
        with self._lock:
            if state == CircuitState.CLOSED:
                return True
            if state == CircuitState.HALF_OPEN:
                return self._half_open_attempts < self.half_open_max
            return False

    def get_stats(self) -> dict:
        with self._lock:
            self._check_cooldown()
            return {
                "name": self.name,
                "state": self._state.value,
                "failure_count": self._failure_count,
                "success_count": self._success_count,
                "last_failure": self._last_failure_time,
            }

    def _check_cooldown(self):
        if self._state == CircuitState.OPEN:
            if time.time() - self._last_failure_time >= self.recovery_timeout:
                self._state = CircuitState.HALF_OPEN
                self._half_open_attempts = 0
                logger.info(
                    "CircuitBreaker[%s]: OPEN -> HALF_OPEN (cooldown elapsed)",
                    self.name,
                )
