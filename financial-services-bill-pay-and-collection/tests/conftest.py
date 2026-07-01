import warnings

import pytest

warnings.filterwarnings(
    "ignore", message=r".*datetime\.datetime\.utcfromtimestamp.*", category=DeprecationWarning
)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    print(f"\n=== RUNNING: {item.nodeid} ===")
    outcome = yield
    print(f"=== {'DONE' if outcome.excinfo is None else 'FAILED'}: {item.nodeid} ===")
