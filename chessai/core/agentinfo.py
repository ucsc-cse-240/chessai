import typing

import edq.util.serial

import chessai.util.alias
import chessai.util.reflection

DEFAULT_STATE_EVAL: str = chessai.util.alias.STATE_EVAL_BASE.long

class AgentInfo(edq.util.serial.DictConverter):
    """
    Argument used to construct an agent.
    Common arguments used by the engine are stored as top-level fields,
    while arguments that specific child agents may use are stored in a general dict.

    Then additional arguments should be kept to simple types
    that can be serialized/deserialized via the standard Python JSON library.
    """

    def __init__(self,
            name: str | chessai.util.reflection.Reference = '',
            state_eval_func: chessai.util.reflection.Reference | str = DEFAULT_STATE_EVAL,
            display_name: str = '',
            extra_arguments: dict[str, typing.Any] | None = None,
            **kwargs: typing.Any) -> None:
        if (isinstance(name, str)):
            name = chessai.util.reflection.Reference(name)

        self.name: chessai.util.reflection.Reference = name
        """ The name of the agent's class. """

        self.state_eval_func: chessai.util.reflection.Reference = chessai.util.reflection.Reference(state_eval_func)
        """ The state evaluation function this agent will use. """

        if (display_name == ''):
            display_name = str(self.name)

        self.display_name = display_name
        """ The display name of the agent. """

        self.extra_arguments: dict[str, typing.Any] = {}
        """
        Additional arguments to the agent.
        These are typically used by agent subclasses.
        """

        self.extra_arguments.update(kwargs)
        if (extra_arguments is not None):
            self.extra_arguments.update(extra_arguments)

    def set_from_string(self, name: str, value: str) -> None:
        """ Set an attribute by name. """

        if (name == 'name'):
            self.name = chessai.util.reflection.Reference(value)
        elif (name == 'state_eval_func'):
            self.state_eval_func = chessai.util.reflection.Reference(value)
        else:
            self.extra_arguments[name] = value

    def update(self, other: 'AgentInfo') -> None:
        """ Update this agent info data from the given agent info. """

        self.name = other.name
        self.state_eval_func = other.state_eval_func
        self.extra_arguments.update(other.extra_arguments)

    def to_flat_dict(self) -> dict[str, typing.Any]:
        """
        Convert this information to a flat dictionary,
        where the extra arguments are on the same level as name and move_delay.
        """

        result = self.extra_arguments.copy()

        result['name'] = self.name
        result['state_eval_func'] = str(self.state_eval_func)

        return result
