"""Bounded PoC B demo runner exports."""

__all__ = ["CURATED_POC_B_DEMO_CASES", "run_poc_b_demo", "write_demo_artifact_bundle"]


def __getattr__(name: str):
    if name in __all__:
        from invoice_exception_poc_a.demo import runner

        return getattr(runner, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
