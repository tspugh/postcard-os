"""Domain errors. Every message is actionable: it states the failed precondition
(quoting the relevant quality bar or guard) and the valid next action (PRD/TRD rule)."""


class DomainError(Exception):
    status_code = 409

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class ValidationRejected(DomainError):
    """Input fails a quality bar or vocabulary; restates the bar."""

    status_code = 400


class NotFound(DomainError):
    status_code = 404


class Conflict(DomainError):
    """A guard or state-machine precondition refused the transition."""

    status_code = 409
