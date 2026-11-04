""" Typed annotations that can be stored in a PGN game header. """

import enum
import typing

import edq.util.json
import edq.util.serial

import chessai

GAME_RATING_ANNOTATION_HEADER: str = 'ChessAIStockfishAnalysis'
""" The PGN header used for a serialized :class:`GameRatingAnnotation`. """

class RatingPerspective(str, enum.Enum):
    """ The player for whom a positive rating is favorable. """

    WHITE = 'white'
    """ Positive values favor White. """

    BLACK = 'black'
    """ Positive values favor Black. """

Rating: typing.TypeAlias = float | str
""" A pawn evaluation or a forced-mate value such as ``"M3"``. """

class RatingEngine(edq.util.serial.DictConverter):
    """ Identify the chess engine that produced a game rating. """

    def __init__(self, name: str, commit: str) -> None:
        self.name: str = name
        """ The engine's display name. """

        self.commit: str = commit
        """ The source revision used to build the engine. """

class MoveRatingAnnotation(edq.util.serial.DictConverter):
    """ A rating for the position after one ply of a game. """

    def __init__(self, ply: int, rating: Rating, move: str | None = None) -> None:
        if (ply < 0):
            raise ValueError('The ply for a game rating annotation cannot be negative.')

        self.ply: int = ply
        """ The zero-based ply of the rated position; zero is the starting position. """

        self.rating: Rating = rating
        """ The engine evaluation of this position. """

        self.move: str | None = move
        """ The UCI move that produced this position, or ``None`` for the starting position. """

    @classmethod
    def from_dict(cls,
            data: dict[str, typing.Any],
            context: edq.util.serial.SerializationContext | None = None,
            ) -> 'MoveRatingAnnotation':
        data = dict(data)
        raw_rating = data.pop('rating', 0.0)
        if isinstance(raw_rating, str):
            if ("M" not in raw_rating.upper()):
                try:
                    raw_rating = float(raw_rating)
                except Exception as ex: # pylint disable=broad-exception-caught
                    raise ValueError(f"Failed to parse rating {raw_rating}") from ex

        init_data = super().prep_init_data(data, context)
        init_data['rating'] = raw_rating
        return cls(**init_data)

class GameRatingAnnotation(edq.util.serial.DictConverter):
    """ A versioned collection of engine ratings for every position in a game. """

    def __init__(self,
            engine: RatingEngine,
            depth: int,
            annotations: list[MoveRatingAnnotation] | None = None,
            score_perspective: RatingPerspective = RatingPerspective.WHITE,
            schema_version: str = chessai.__version__,
            ) -> None:
        if (depth < 1):
            raise ValueError('The analysis depth must be at least one.')

        self.schema_version: str = schema_version
        """ The version of this annotation's JSON schema. """

        self.score_perspective: RatingPerspective = score_perspective
        """ The player for whom a positive evaluation is favorable. """

        self.engine: RatingEngine = engine
        """ The engine that evaluated the game. """

        self.depth: int = depth
        """ The engine search depth used for every rating. """

        if (annotations is None):
            annotations = []

        self.annotations: list[MoveRatingAnnotation] = annotations
        """ The initial position and each later position's rating, in ply order. """

    def to_header_value(self) -> str:
        """ Serialize this annotation as compact JSON suitable for a PGN tag value. """

        return edq.util.json.dumps(self.to_dict(), separators = (',', ':'))

    @classmethod
    def from_header_value(cls, value: str) -> 'GameRatingAnnotation':
        """ Deserialize a :data:`GAME_RATING_ANNOTATION_HEADER` tag value. """

        data = edq.util.json.loads(value, strict = True)
        if (not isinstance(data, dict)):
            raise ValueError('A game rating annotation header must contain a JSON object.')

        return cls.from_dict(data)
