import pytest

import utils.auth_rate_limit as auth_rate_limit
import utils.rate_limit as rate_limit


@pytest.fixture(autouse=True)
def reset_rate_limit_state():
    """Rate limiters keep counters in module-level memory, which would
    otherwise bleed across tests — and across test files, since they all
    share one pytest process — unless cleared before and after every test."""
    rate_limit._reset_state()
    auth_rate_limit._reset_state()
    yield
    rate_limit._reset_state()
    auth_rate_limit._reset_state()
