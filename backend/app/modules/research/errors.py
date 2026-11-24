"""Public research application failures, independent of HTTP and model transport."""


class ModelError(Exception):
    pass


class ModelBudgetError(ModelError):
    """An exhausted run budget cannot be repaired by a validation retry."""


class ResearchQueueFull(RuntimeError):
    pass


class IndustryNotFound(KeyError):
    pass


class RunNotFound(KeyError):
    pass


class RunCancelledError(Exception):
    """Raised when a user explicitly stops a queued or running research run."""

    pass


class RunActiveError(RuntimeError):
    """Raised when attempting to delete a run that is still queued or running."""

    pass
