# Builtin
from functools import wraps
from textwrap import dedent


class BaseException(Exception):
    @classmethod
    def __init_subclass__(cls, /, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        cls.__init__ = BaseException.__init_method_wrapper(cls.__init__)  # type: ignore

    @staticmethod
    def __init_method_wrapper(func, /):
        @wraps(func)
        def wrapped_init_method(self, /, *args):
            func(self, *args)
            if len(self.args) > 0 and isinstance(self.args[0], str):
                one_line_exception_message = (
                    dedent(self.args[0]).replace("\n", " ").strip()
                )
                self.args = (one_line_exception_message, *self.args[1:])

        return wrapped_init_method


class DuplicateNodeAdditionException(BaseException):
    pass


class MissingArrayIndexException(BaseException):
    pass


class NoneValuesAccessedException(BaseException):
    pass


class InvalidJSONPathException(BaseException):
    pass
