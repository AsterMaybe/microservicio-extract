from app.api.deps import default_runtime
from app.config.settings import Settings


def test_default_runtime_is_an_async_context_manager() -> None:
    cm = default_runtime(Settings())
    assert hasattr(cm, "__aenter__")
    assert hasattr(cm, "__aexit__")
