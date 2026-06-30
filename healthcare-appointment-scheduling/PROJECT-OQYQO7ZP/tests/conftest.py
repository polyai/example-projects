import warnings

import pytest

warnings.filterwarnings(
    "ignore",
    message=r".*datetime\.datetime\.utcfromtimestamp\(\) is deprecated.*",
    category=DeprecationWarning,
)
warnings.filterwarnings(
    "ignore",
    message=r".*datetime\.datetime\.utcnow\(\) is deprecated.*",
    category=DeprecationWarning,
)


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    print(f"\n=== RUNNING: {item.nodeid} ===")
    outcome = yield
    if outcome.excinfo is None:
        print(f"=== DONE: {item.nodeid} ===")
    else:
        print(f"=== FAILED: {item.nodeid} ===")
