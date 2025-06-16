class CommPath:
    """
    Class representing a forward-slash-separated path for use in a comms client.
    """

    def __init__(self, path: "str | CommPath") -> None:
        """
        Create a new CommPath object.

        Args:
            path: Optional path to extend from
        """

        if isinstance(path, CommPath):
            path = path.path
        self._path = path

    def __truediv__(self, new: str):
        return CommPath(self._path.rstrip("/") + "/" + new.lstrip("/"))

    def __str__(self) -> str:
        return self._path

    @property
    def path(self) -> str:
        """
        Get the path as a string.

        Returns:
            Path
        """
        return self._path
