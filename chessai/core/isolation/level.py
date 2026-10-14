import enum
import typing

import chessai.core.isolation.isolator
import chessai.core.isolation.none
import chessai.core.isolation.process

class Level(enum.Enum):
    """ An enum representing the different isolation levels supported by the engine. """

    NONE = 'none'
    PROCESS = 'process'

    def get_isolator(self, **kwargs: typing.Any) -> chessai.core.isolation.isolator.AgentIsolator:
        """ Get an isolator matching the given level. """

        isolator: chessai.core.isolation.isolator.AgentIsolator | None = None

        if (self == Level.NONE):
            isolator = chessai.core.isolation.none.NoneIsolator(**kwargs)
        elif (self == Level.PROCESS):
            isolator = chessai.core.isolation.process.ProcessIsolator(**kwargs)

        if (isolator is None):
            raise ValueError(f"Unknown isolation level '{self}'.")

        return isolator

LEVELS: list[str] = [item.value for item in Level]
