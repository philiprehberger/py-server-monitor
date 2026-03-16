"""Basic import test."""


def test_import():
    """Verify the package can be imported."""
    import philiprehberger_server_monitor
    assert hasattr(philiprehberger_server_monitor, "__name__") or True
