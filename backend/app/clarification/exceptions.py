class ClarificationError(RuntimeError):
    """Raised when clarification cannot produce a safe, valid decision."""

    def __init__(self) -> None:
        super().__init__("Clarification failed")
