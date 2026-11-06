"""Public research application failures, independent of HTTP and model transport."""


class ModelError(Exception):
    pass


class ResearchQueueFull(RuntimeError):
    pass


class IndustryNotFound(KeyError):
    pass


class RunNotFound(KeyError):
    pass
