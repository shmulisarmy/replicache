"""Custom exceptions for the application."""


class SyncError(Exception):
    """Base exception for sync-related errors."""
    pass


class DatabaseError(SyncError):
    """Exception raised for database operation errors."""
    pass


class ConflictError(SyncError):
    """Exception raised when data conflicts occur."""
    pass


class ClientError(SyncError):
    """Exception raised for client-related errors."""
    pass

