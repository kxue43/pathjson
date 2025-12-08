# Builtin
from __future__ import annotations
from collections.abc import Iterable
import re
from typing import (
    Callable,
    ClassVar,
    Dict,
    List,
    Pattern,
)

# Own
from .exceptions import BaseException
from ._nodes import (
    ArrayNode,
    CanGetItem,
    InternalNode,
    LeafNode,
    Nodal,
    Node,
    ObjectNode,
)


class JsonifyFunctionBuilder[T: CanGetItem]:
    _leaf_jsonpaths: List[str]

    _internal_nodes: Dict[str, InternalNode]

    _model: Node

    _JSONPATH: ClassVar[Pattern] = re.compile(
        r"^(?P<head>\$(\.[a-zA-Z]\w*|\[\d+\])*)(?P<tail>\.[a-zA-Z]\w*|\[\d+\])$"
    )

    class InvalidJSONPathException(BaseException):
        pass

    def __init__(self, leaf_jsonpaths: Iterable[str]) -> None:
        if isinstance(leaf_jsonpaths, list):
            self._leaf_jsonpaths = leaf_jsonpaths
        else:
            self._leaf_jsonpaths = list(leaf_jsonpaths)

        self._internal_nodes = {}

        self._model = self._get_model()

    def build(self) -> Callable[[T], Nodal]:
        def jsonifier(row: T) -> Nodal:
            return self._model.get_value(row)

        return jsonifier

    def _get_model(self) -> Node:
        for leaf in self._leaf_jsonpaths:
            leaf_node = LeafNode(leaf)

            parent = self._get_parent_jsonpath(leaf)

            self._join_nodes(parent, leaf_node)

        return self._internal_nodes["$"]

    def _join_nodes(self, parent: str, child_node: Node) -> None:
        if parent in self._internal_nodes:
            key = self._get_child_key_in_parent(child_node.jsonpath)

            parent_node = self._internal_nodes[parent]

            parent_node.add_child(key, child_node)

            if isinstance(child_node, InternalNode):
                self._internal_nodes[child_node.jsonpath] = child_node
        elif parent == "$":
            self._internal_nodes[parent] = self._create_internal_node(
                parent, child_node.jsonpath
            )

            self._join_nodes(parent, child_node)
        else:
            new_child_node = self._create_internal_node(parent, child_node.jsonpath)

            new_parent = self._get_parent_jsonpath(parent)

            self._join_nodes(new_parent, new_child_node)

            self._join_nodes(parent, child_node)

    def _get_parent_jsonpath(self, child: str) -> str:
        match = self._JSONPATH.match(child)
        if match is None:
            raise self.InvalidJSONPathException(
                rf"""
                JSONPath `{child}` is invalid. Allowed pattern is
                `"^(\$\.[a-zA-Z]\w*|\[\d+\])*(\.[a-zA-Z]\w*|\[\d+\])$"`.
                """
            )

        return match.group("head")

    def _get_child_key_in_parent(self, child: str) -> str:
        match = self._JSONPATH.match(child)
        if match is None:
            raise self.InvalidJSONPathException(
                rf"""
                JSONPath `{child}` is invalid. Allowed pattern is
                `"^(\$\.[a-zA-Z]\w*|\[\d+\])*(\.[a-zA-Z]\w*|\[\d+\])$"`.
                """
            )

        tail = match.group("tail")
        if tail.endswith("]"):
            return tail[1:-1]

        return tail[1:]

    def _create_internal_node(
        self, self_jsonpath: str, child_jsonpath: str
    ) -> InternalNode:
        if child_jsonpath.endswith("]"):
            return ArrayNode(self_jsonpath)

        return ObjectNode(self_jsonpath)
