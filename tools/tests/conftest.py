import os
import sys

import pytest

# The tools are plain scripts rather than a package, so make them importable from the tests
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(autouse=True)
def not_running_in_github_actions(monkeypatch):
    """
    The validator prints extra annotation lines when GITHUB_ACTIONS is set, which it is when these tests
    are run by the workflow. Clear it so that every test sees the same output wherever it runs. A test
    that wants the annotations sets the variable itself.
    """
    monkeypatch.delenv('GITHUB_ACTIONS', raising=False)
