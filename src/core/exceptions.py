"""Custom exceptions for the application."""


class DataAccessException(Exception):
    """Exception raised for data access errors."""
    def __init__(self, message: str, original_exception: Exception = None):
        self.message = message
        self.original_exception = original_exception
        super().__init__(self.message)


class PlayerNotFoundException(Exception):
    """Exception raised when a player is not found."""
    def __init__(self, player_id: int):
        self.player_id = player_id
        self.message = f"Player with ID {player_id} not found"
        super().__init__(self.message)


class InvalidFilterException(Exception):
    """Exception raised for invalid filter parameters."""
    def __init__(self, message: str):
        self.message = message
        super().__init__(self.message)


class WatchlistException(Exception):
    """Exception raised for watchlist operations errors."""
    def __init__(self, message: str, operation: str = None):
        self.message = message
        self.operation = operation
        super().__init__(self.message)
