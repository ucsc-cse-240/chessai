import argparse
import logging
import typing

import chessai.core.agentinfo
import chessai.core.game
import chessai.core.types
import chessai.escort.game
import chessai.escort.gamestate
import chessai.util.alias
import chessai.util.bin

DEFAULT_BOARD: str = 'alcove-demo'

def set_cli_args(parser: argparse.ArgumentParser, **kwargs: typing.Any) -> argparse.ArgumentParser:
    """
    Set Escort-specific command-line arguments.
    """

    parser.add_argument('--agent', dest = 'agent', action = 'store', type = str,
            default = chessai.util.alias.AGENT_RANDOM.short,
            help = ('Select the Escort agent (default: %(default)s).'
                    + f' Builtin agents: {chessai.util.alias.AGENT_SHORT_NAMES}.'))

    parser.add_argument('--search-targets', dest = 'search_targets',
            action = 'store', type = str, default = None,
            help = ('The target squares for the search problem (default: %(default)s).'
                    + ' Separate multiple targets with commas (e.g., \'0,42,63\').'))

    return parser

def init_from_args(args: argparse.Namespace) -> tuple[dict[chessai.core.types.Color, chessai.core.agentinfo.AgentInfo],
        list[chessai.core.types.Color], dict[str, typing.Any]]:
    """
    Setup agents based on King Escort rules.

    The solver agent is whichever color has the first move according to the board's FEN (i.e., the side-to-move).
    The guard agent is assigned the opposite color so it can attack the king.

    If the board hasn't been loaded yet (args.board is still a string or None),
    we parse the side-to-move directly from the FEN/board argument so we can
    assign colors before the full board object is constructed.
    """

    solver_color = _detect_solver_color(args)

    base_agent_infos: dict[chessai.core.types.Color, chessai.core.agentinfo.AgentInfo] = {
        solver_color:            chessai.core.agentinfo.AgentInfo(name = args.agent),
        solver_color.opposite(): chessai.core.agentinfo.AgentInfo(name = chessai.util.alias.AGENT_GUARD.short),
    }

    return base_agent_infos, [], {}

def _detect_solver_color(args: argparse.Namespace) -> chessai.core.types.Color:
    """
    Determine which color is the escort solver (i.e., the side that moves first).
    """

    board_arg = args.board
    if (board_arg is None):
        board_arg = DEFAULT_BOARD

    board_arg = typing.cast(str, board_arg)

    parsed_fen = chessai.escort.parser.parse_escort(board_arg)
    return parsed_fen.turn

def log_escort_results(results: list[chessai.core.game.GameResult],
                       winning_agent_teams: set[chessai.core.types.Color],
                       prefix: str = '') -> None:
    """
    Log the result of running several King Escort games.
    """

    move_counts: list[int] = [len(result.history) for result in results]
    scores: list[float] = [result.score for result in results]

    record: list[str] = []
    for result in results:
        if (result.score > 0):
            record.append('Win')
        elif (result.score < 0):
            record.append('Loss')
        else:
            record.append('Tie')

    average_score: float = (sum(scores)) / len(scores)
    logging.info('Average Score: %0.2f', average_score)

    # Avoid logging long lists (which can be a bit slow in Python's logging module).
    log_lists_to_info: bool = (len(results) < chessai.util.bin.SCORE_LIST_MAX_INFO_LENGTH)
    log_lists_to_debug: bool = (logging.getLogger().getEffectiveLevel() <= logging.DEBUG)

    joined_scores: str = ''
    joined_record: str = ''
    joined_move_counts: str = ''

    if (log_lists_to_info or log_lists_to_debug):
        joined_scores = ', '.join([str(score) for score in scores])
        joined_record = ', '.join(record)
        joined_move_counts = ', '.join([str(move_count) for move_count in move_counts])

    if (log_lists_to_info):
        logging.info('%sScores:        %s', prefix, joined_scores)
    elif (log_lists_to_debug):
        logging.debug('%sScores:        %s', prefix, joined_scores)

    if (log_lists_to_info):
        logging.info('%sRecord:        %s', prefix, joined_record)
    elif (log_lists_to_debug):
        logging.debug('%sRecord:        %s', prefix, joined_record)

    logging.info('%sAverage Moves: %s', prefix, sum(move_counts) / float(len(results)))

    if (log_lists_to_info):
        logging.info('%sMove Counts:   %s', prefix, joined_move_counts)
    elif (log_lists_to_debug):
        logging.debug('%sMove Counts:   %s', prefix, joined_move_counts)

def main(argv: list[str] | None = None,
         ) -> list[chessai.core.game.GameResult]:
    """
    Invoke a game of King Escort.

    Will return the results of all of the games.
    """

    return chessai.util.bin.run_main(
        description = 'Play a King Escort game.',
        default_board = DEFAULT_BOARD,
        game_class = chessai.escort.game.Game,
        state_class = chessai.escort.gamestate.GameState,
        custom_set_cli_args = set_cli_args,
        custom_init_from_args = init_from_args,
        log_results = log_escort_results,
        argv = argv,
    )

if (__name__ == '__main__'):
    main()
