"""
Result monad for elegant functional error handling.

Provides a clean, composable way to handle errors without exceptions.
"""

from typing import TypeVar, Generic, Callable, Union, Any
from dataclasses import dataclass
from enum import Enum

T = TypeVar('T')
E = TypeVar('E') 
U = TypeVar('U')


class ErrorType(Enum):
    """Common error types in the application."""
    VALIDATION_ERROR = "validation_error"
    NOT_FOUND = "not_found"
    DATA_SERVICE_ERROR = "data_service_error"
    STRATEGY_ERROR = "strategy_error"
    INTERNAL_ERROR = "internal_error"


@dataclass(frozen=True)
class AppError:
    """Application error with type and message."""
    error_type: ErrorType
    message: str
    details: dict = None
    
    def to_dict(self) -> dict:
        return {
            "error": self.error_type.value,
            "message": self.message,
            "details": self.details or {}
        }


class Result(Generic[T, E]):
    """Result monad for handling success/failure without exceptions."""
    
    def __init__(self, value: Union[T, E], is_success: bool):
        self._value = value
        self._is_success = is_success
    
    @classmethod
    def ok(cls, value: T) -> 'Result[T, E]':
        """Create a successful result."""
        return cls(value, True)
    
    @classmethod
    def err(cls, error: E) -> 'Result[T, E]':
        """Create an error result."""
        return cls(error, False)
    
    def is_ok(self) -> bool:
        """Check if result is successful."""
        return self._is_success
    
    def is_err(self) -> bool:
        """Check if result is an error."""
        return not self._is_success
    
    def unwrap(self) -> T:
        """Get the success value (unsafe - raises if error)."""
        if not self._is_success:
            raise ValueError(f"Called unwrap on error result: {self._value}")
        return self._value
    
    def unwrap_or(self, default: T) -> T:
        """Get the success value or return default."""
        return self._value if self._is_success else default
    
    def unwrap_err(self) -> E:
        """Get the error value (unsafe - raises if success)."""
        if self._is_success:
            raise ValueError(f"Called unwrap_err on success result: {self._value}")
        return self._value
    
    def map(self, func: Callable[[T], U]) -> 'Result[U, E]':
        """Transform the success value."""
        if self._is_success:
            try:
                return Result.ok(func(self._value))
            except Exception as e:
                return Result.err(AppError(ErrorType.INTERNAL_ERROR, str(e)))
        return Result.err(self._value)
    
    def map_err(self, func: Callable[[E], U]) -> 'Result[T, U]':
        """Transform the error value."""
        if not self._is_success:
            return Result.err(func(self._value))
        return Result.ok(self._value)
    
    def and_then(self, func: Callable[[T], 'Result[U, E]']) -> 'Result[U, E]':
        """Chain operations that can fail (flatMap)."""
        if self._is_success:
            try:
                return func(self._value)
            except Exception as e:
                return Result.err(AppError(ErrorType.INTERNAL_ERROR, str(e)))
        return Result.err(self._value)
    
    def or_else(self, func: Callable[[E], 'Result[T, U]']) -> 'Result[T, U]':
        """Recover from error with alternative computation."""
        if not self._is_success:
            return func(self._value)
        return Result.ok(self._value)


# Type alias for common Result pattern
AppResult = Result[T, AppError]


def safe_call(func: Callable[[], T]) -> AppResult[T]:
    """Safely call a function and return Result."""
    try:
        return Result.ok(func())
    except Exception as e:
        return Result.err(AppError(ErrorType.INTERNAL_ERROR, str(e)))


def validate(condition: bool, error_msg: str) -> AppResult[None]:
    """Validate condition and return Result."""
    if condition:
        return Result.ok(None)
    return Result.err(AppError(ErrorType.VALIDATION_ERROR, error_msg))
