# Builtin
from __future__ import annotations
from abc import ABC, abstractmethod
from functools import wraps
from typing import (
    Callable,
    cast,
    Dict,
    List,
    Optional,
    Protocol,
    Union,
)

# Own
from .exceptions import BaseException


Scalar = Union[float, str, bool]
Nodal = Union[Scalar, Dict[str, "Nodal"], List["Nodal"]]


class CanGetItem(Protocol):
    def __getitem__(self, key: str) -> Optional[Scalar]: ...


class Node[S: Node](ABC):
    jsonpath: str

    _last_checked_row: Optional[CanGetItem]

    _intersected_last_time: bool

    class NoneValuesAccessedException(BaseException):
        pass

    def __init__(self, jsonpath: str) -> None:
        self.jsonpath = jsonpath

        self._last_checked_row = None

        self._intersected_last_time = False

    @abstractmethod
    def get_value(self, row: CanGetItem) -> Nodal: ...

    @abstractmethod
    def intersects(self, row: CanGetItem) -> bool: ...

    @staticmethod
    def cached(
        intersects: Callable[[S, CanGetItem], bool],
    ) -> Callable[[S, CanGetItem], bool]:
        @wraps(intersects)
        def cached_intersects(self: S, row: CanGetItem) -> bool:
            if self._last_checked_row is row:
                return self._intersected_last_time

            self._intersected_last_time = intersects(self, row)

            self._last_checked_row = row

            return self._intersected_last_time

        return cached_intersects

    @staticmethod
    def protected(
        get_value: Callable[[S, CanGetItem], Nodal],
    ) -> Callable[[S, CanGetItem], Nodal]:
        @wraps(get_value)
        def protected_get_value(self: S, row: CanGetItem) -> Nodal:
            if not self.intersects(row):
                error_message = (
                    f"Values at JSONPaths `{self.jsonpath}***` are all `None`."
                    if hasattr(self, "children")
                    else f"Value at JSONPath `{self.jsonpath}` is `None`."
                )

                raise self.NoneValuesAccessedException(error_message)

            return get_value(self, row)

        return protected_get_value


class LeafNode(Node):
    @Node.protected
    def get_value(self, row: CanGetItem) -> Scalar:
        return cast(Scalar, row[self.jsonpath])

    @Node.cached
    def intersects(self, row: CanGetItem) -> bool:
        return row[self.jsonpath] is not None


class InternalNode(Node):
    children: Dict[str, Node]

    class DuplicateNodeAdditionException(BaseException):
        pass

    def __init__(self, jsonpath: str) -> None:
        super().__init__(jsonpath)

        self.children = {}

    def add_child(self, key: str, child: Node) -> None:
        if key in self.children:
            raise self.DuplicateNodeAdditionException(
                f"""
                Child node `{child.jsonpath}` was added to parent node `{self.jsonpath}`
                more than once during model-building.
                """
            )

        self.children[key] = child

    @Node.cached
    def intersects(self, row: CanGetItem) -> bool:
        return any(map(lambda node: node.intersects(row), self.children.values()))


class ObjectNode(InternalNode):
    @Node.protected
    def get_value(self, row: CanGetItem) -> Dict[str, Nodal]:
        return {
            key: node.get_value(row)
            for key, node in self.children.items()
            if node.intersects(row)
        }


class ArrayNode(InternalNode):
    class MissingArrayIndexException(BaseException):
        pass

    @Node.protected
    def get_value(self, row: CanGetItem) -> List[Nodal]:
        length = len(self.children)

        for n in range(0, length):
            if str(n) not in self.children:
                raise self.MissingArrayIndexException(
                    f"Missing a JSONPath of the format `{self.jsonpath}[{n}]***`."
                )

        list_: List[Nodal] = []

        for n in range(0, length):
            if self.children[str(n)].intersects(row):
                list_.append(self.children[str(n)].get_value(row))

        return list_
