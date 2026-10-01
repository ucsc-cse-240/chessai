import enum

class Color(int, enum.Enum):
    """ An enum representing the side to move or the color of a piece. """
    BLACK = 0
    WHITE = 1

    def symbol(self) -> str:
        """ Returns 'w' for white and 'b' for black. """

        return 'w' if (self == Color.WHITE) else 'b'

    def opposite(self) -> 'Color':
        """ Returns the opposing color. """

        return Color.BLACK if (self == Color.WHITE) else Color.WHITE

    def __str__(self) -> str:
        return self.name.lower()

    def __repr__(self) -> str:
        return f"Color.{self.name}"

    def __bool__(self) -> bool:
        return bool(self.value)

class TerminationReason(str, enum.Enum):
    """ An enum representing the reason for a game to be over. """

    CHECKMATE = 'Checkmate'
    """ See chessai.core.gamestate.GameState.is_checkmate(). """

    STALEMATE = 'Stalemate'
    """ See chessai.core.gamestate.GameState.is_stalemate(). """

    INSUFFICIENT_MATERIAL = 'Insufficient Material'
    """ See chessai.core.gamestate.GameState.is_insufficient_material(). """

    FORFEIT = 'Forfeit'
    """ An agent forfeited the match via chessai.core.action.ForfeitAction(). """

    ACCEPTED_DRAW_PROPOSAL = 'Accepted Draw Proposal.'
    """ Agents agreed to draw via draw proposals. """

    IN_PROGRESS = 'In Progress'
    """ Indicates the game is still in progress (i.e., it has not yet terminated). """

    AGENT_CRASHED = 'Agent Crashed'
    """ Indicates an agent crashed, ending the game. """

    AGENT_TIMEOUT = 'Agent Timeout'
    """ An agent took to long to respond, ending the game. """

    GAME_TIMEOUT = 'Game Timeout'
    """ The maximum number of moves in the game was reached. """

    VARIANT_WIN = 'Variant Win'
    """ See chessai.core.gamestate.GameState.is_variant_win(). """

    VARIANT_LOSS = 'Variant Loss'
    """ See chessai.core.gamestate.GameState.is_variant_loss(). """

    UNKNOWN = 'Unknown'
    """ The termination reason is unknown. """
