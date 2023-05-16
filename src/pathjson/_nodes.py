# Builtin
from abc import ABC, abstractmethod
from functools import wraps
from typing import (
    Callable,
    cast,
    Dict,
    List,
    Optional,
    Protocol,
    TypeVar,
    Union,
)

# Own
from .exceptions import BaseException


Scalar = Union[float, str, bool]
Nodal = Union[Scalar, Dict[str, "Nodal"], List["Nodal"]]
S = TypeVar("S", bound="Node")


class CanGetItem(Protocol):
    def __getitem__(self, key: str) -> Optional[Scalar]:
        ...


class Node(ABC):
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
    def get_value(self, row: CanGetItem) -> Nodal:
        ...

    @abstractmethod
    def intersects(self, row: CanGetItem) -> bool:
        ...

    @staticmethod
    def cached(
        intersects: Callable[[S, CanGetItem], bool]
    ) -> Callable[[S, CanGetItem], bool]:
        @wraps(intersects)
        def cached_intersects(self: S, row: CanGetItem) -> bool:
            if self._last_checked_row is row:
                return self._intersected_last_time
            self._intersected_last_time = intersects(self, row)
            self._last_checked_row = row
            return self._intersected_last_time

        return cached_intersects


class LeafNode(Node):
    def get_value(self, row: CanGetItem) -> Scalar:
        if not self.intersects(row):
            raise self.NoneValuesAccessedException(
                f"Value at JSONPath `{self.jsonpath}` is `None`."
            )
        result = row[self.jsonpath]
        return cast(Scalar, result)

    @Node.cached
    def intersects(self, row: CanGetItem) -> bool:
        return row[self.jsonpath] is not None


class InternalNode(Node):
    childrens: Dict[str, Node]

    class DuplicateNodeAdditionException(BaseException):
        pass

    def __init__(self, jsonpath: str) -> None:
        super().__init__(jsonpath)
        self.childrens = {}

    def add_child(self, key: str, child: Node) -> None:
        if key in self.childrens:
            raise self.DuplicateNodeAdditionException(
                f"""
                Child node `{child.jsonpath}` was added to parent node `{self.jsonpath}`
                more than once during model-building.
                """
            )
        self.childrens[key] = child

    @Node.cached
    def intersects(self, row: CanGetItem) -> bool:
        return any(map(lambda node: node.intersects(row), self.childrens.values()))


class ObjectNode(InternalNode):
    def get_value(self, row: CanGetItem) -> Dict[str, Nodal]:
        if not self.intersects(row):
            raise self.NoneValuesAccessedException(
                f"Values at JSONPaths `{self.jsonpath}***` are all `None`."
            )
        return {
            key: node.get_value(row)
            for key, node in self.childrens.items()
            if node.intersects(row)
        }


class ArrayNode(InternalNode):
    class MissingArrayIndexException(BaseException):
        pass

    def get_value(self, row: CanGetItem) -> List[Nodal]:
        if not self.intersects(row):
            raise self.NoneValuesAccessedException(
                f"Values at JSONPaths `{self.jsonpath}***` are all `None`."
            )
        length = len(self.childrens)
        for n in range(0, length):
            if str(n) not in self.childrens:
                raise self.MissingArrayIndexException(
                    f"Missing a JSONPath of the format `{self.jsonpath}[{n}]***`."
                )
        list_: List[Nodal] = []
        for n in range(0, length):
            if self.childrens[str(n)].intersects(row):
                list_.append(self.childrens[str(n)].get_value(row))
        return list_
