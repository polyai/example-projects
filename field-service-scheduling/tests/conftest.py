import sys
import types
import warnings
from pathlib import Path

import pytest

warnings.filterwarnings(
    "ignore", message=r".*datetime\.datetime\.utcfromtimestamp.*", category=DeprecationWarning
)

# ---------------------------------------------------------------------------
# Bootstrap: stub _gen and make functions/ importable outside Agent Studio
# ---------------------------------------------------------------------------

_PROJECT_ROOT = Path(__file__).resolve().parent.parent

if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# Stub _gen so decorated functions are importable
if "_gen" not in sys.modules:
    _fake_gen = types.ModuleType("_gen")
    _fake_gen.func_description = lambda *a, **kw: lambda fn: fn
    _fake_gen.func_parameter = lambda *a, **kw: lambda fn: fn
    _fake_gen.func_latency_control = lambda *a, **kw: lambda fn: fn
    _fake_gen.Conversation = type("Conversation", (), {})
    _fake_gen.Flow = type("Flow", (), {})
    sys.modules["_gen"] = _fake_gen


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
    print(f"\n=== RUNNING: {item.nodeid} ===")
    outcome = yield
    print(f"=== {'DONE' if outcome.excinfo is None else 'FAILED'}: {item.nodeid} ===")
