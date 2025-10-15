from pathlib import Path

# Extend the package search path so ``import app.*`` can locate modules that
# live alongside this package (for example ``app/websockets``).
_parent = Path(__file__).resolve().parent.parent
_parent_str = str(_parent)
if _parent_str not in __path__:
    __path__.append(_parent_str)

__all__ = []  # namespace-style package; submodules define their own exports
