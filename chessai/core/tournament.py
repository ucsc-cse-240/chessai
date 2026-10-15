import typing

import edq.util.serial

class Game(edq.util.serial.DictConverter):
    """
    A scheduled tournament match between two players.

    The input form needs only ``player_one`` and ``player_two``.
    The tournament runner fills in the remaining fields after the match has completed.
    """

    def __init__(self,
            player_one: str,
            player_two: str,
            id: str | None = None,
            seed: int | None = None,
            results: list[dict[str, typing.Any]] | None = None,
            status: str = 'pending',
            error: str | None = None,
            log_path: str | None = None,
            replay_path: str | None = None,
            **kwargs: typing.Any,
            ) -> None:
        if (not isinstance(player_one, str)) or (len(player_one.strip()) == 0):
            raise ValueError("Tournament game 'player_one' must be a non-empty string.")

        if (not isinstance(player_two, str)) or (len(player_two.strip()) == 0):
            raise ValueError("Tournament game 'player_two' must be a non-empty string.")

        if (id is not None) and ((not isinstance(id, str)) or (len(id.strip()) == 0)):
            raise ValueError("Tournament game 'id' must be a non-empty string when provided.")

        self.player_one: str = player_one
        """ The player whose score is reported by the tournament summary. """

        self.player_two: str = player_two
        """ The opposing player. """

        self.id: str | None = id
        """ An optional identifier supplied by the tournament schedule. """

        self.seed: int | None = seed
        """ The seed assigned to this match by the tournament runner. """

        self.results: list[dict[str, typing.Any]] = results if (results is not None) else []
        """ The serialized result of every game played in this match. """

        self.status: str = status
        """ The execution status: pending, succeeded, or failed. """

        self.error: str | None = error
        """ The child-process error, if the match failed. """

        self.log_path: str | None = log_path
        """ The optional relative path to the captured match log. """

        self.replay_path: str | None = replay_path
        """ The optional relative base path used for saved PGN replays. """
