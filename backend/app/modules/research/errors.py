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
