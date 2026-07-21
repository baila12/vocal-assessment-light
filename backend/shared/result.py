"""
Result[T, E] Monad — 函数式错误处理

替代 try/except 泛滥, 强制调用方处理错误路径。
"""

from __future__ import annotations
from typing import Generic, TypeVar, Callable, Union

T = TypeVar("T")
E = TypeVar("E")
U = TypeVar("U")


class Result(Generic[T, E]):
    """成功或失败的结果包装器。

    用法:
        def div(a: int, b: int) -> Result[float, str]:
            if b == 0:
                return Result.err("division by zero")
            return Result.ok(a / b)

        result = div(10, 2)
        if result.is_ok():
            print(result.unwrap())     # 5.0
        else:
            print(result.unwrap_err()) # "division by zero"
    """

    __slots__ = ("_value", "_error", "_is_ok")

    def __init__(self, value: T | None = None, error: E | None = None) -> None:
        if value is not None and error is not None:
            raise ValueError("Result cannot be both ok and err")
        if value is None and error is None:
            raise ValueError("Result must be either ok or err")
        self._value = value
        self._error = error
        self._is_ok = value is not None

    @classmethod
    def ok(cls, value: T) -> Result[T, E]:
        return cls(value=value)

    @classmethod
    def err(cls, error: E) -> Result[T, E]:
        return cls(error=error)

    def is_ok(self) -> bool:
        return self._is_ok

    def is_err(self) -> bool:
        return not self._is_ok

    def unwrap(self) -> T:
        if not self._is_ok:
            raise ValueError(f"Called unwrap on Err: {self._error}")
        return self._value

    def unwrap_err(self) -> E:
        if self._is_ok:
            raise ValueError(f"Called unwrap_err on Ok: {self._value}")
        return self._error

    def unwrap_or(self, default: T) -> T:
        return self._value if self._is_ok else default

    def map(self, fn: Callable[[T], U]) -> Result[U, E]:
        if self._is_ok:
            return Result.ok(fn(self._value))
        return Result.err(self._error)

    def map_err(self, fn: Callable[[E], U]) -> Result[T, U]:
        if self._is_ok:
            return Result.ok(self._value)
        return Result.err(fn(self._error))

    def __repr__(self) -> str:
        if self._is_ok:
            return f"Ok({self._value!r})"
        return f"Err({self._error!r})"
