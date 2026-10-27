import argparse
import logging
import math
import typing

import edq.util.json

import chessai.core.agentaction
import chessai.core.agentinfo
import chessai.core.game
import chessai.core.log
import chessai.core.ui
import chessai.util.alias

SCORE_LIST_MAX_INFO_LENGTH: int = 50
""" If a score list is less than this, log it to info. """

@typing.runtime_checkable
class SetCLIArgs(typing.Protocol):
    """
    A function that can be used to modify a CLI parser before use.
    """

    def __call__(self,
            parser: argparse.ArgumentParser,
            ) -> argparse.ArgumentParser:
        """
        Modify the CLI parser before use.
        Any changes may be made, including adding arguments.
        The modified (or new) parser should be returned.
        """

@typing.runtime_checkable
class GetAdditionalOptions(typing.Protocol):
    """
    A function that can be used to get additional initialization options.
    """

    def __call__(self,
            args: argparse.Namespace,
            ) -> dict[str, typing.Any]:
        """
        Get additional/custom initialization options.
        """

@typing.runtime_checkable
class InitFromArgs(typing.Protocol):
    """
    A function that can be used to initialize components from CLI args.
    """

    def __call__(self,
            args: argparse.Namespace,
            ) -> tuple[dict[chessai.core.types.Color, chessai.core.agentinfo.AgentInfo], list[chessai.core.types.Color], dict[str, typing.Any]]:
        """
        Initialize components from arguments and return
        the base agent infos, a list of agents to remove from the board, as well as any board options.
        See base_init_from_args() for the default implementation.
        """

@typing.runtime_checkable
class LogResults(typing.Protocol):
    """
    A function that can be used to log game results.
    """

    def __call__(self,
            results: list[chessai.core.game.GameResult],
            winning_agent_teams: set[chessai.core.types.Color],
            prefix: str = '',
            ) -> None:
        """
        Log the result of running several games.
        """

def base_init_from_args(args: argparse.Namespace) -> tuple[dict[chessai.core.types.Color, chessai.core.agentinfo.AgentInfo],
        list[chessai.core.types.Color], dict[str, typing.Any]]:
    """
    Take in args from a parser that was passed to set_cli_args(),
    and initialize the proper components.
    """

    # Create base arguments for all possible agents.
    base_agent_infos: dict[chessai.core.types.Color, chessai.core.agentinfo.AgentInfo] = {
        chessai.core.types.Color.WHITE: chessai.core.agentinfo.AgentInfo(name = chessai.util.alias.AGENT_RANDOM.long),
        chessai.core.types.Color.BLACK: chessai.core.agentinfo.AgentInfo(name = chessai.util.alias.AGENT_RANDOM.long),
    }

    return base_agent_infos, [], {}

def base_log_results(results: list[chessai.core.game.GameResult], winning_agent_teams: set[chessai.core.types.Color], prefix: str = '') -> None:
    """
    Log the result of running several games.
    """

    move_counts: list[int] = [len(result.history) for result in results]
    scores: list[float] = [result.score for result in results]

    record: list[str] = []
    for result in results:
        if (math.isclose(result.score, 0.5)):
            record.append('Tie')
        elif (math.isclose(result.score, 1.0)):
            record.append('Win')
        else:
            record.append('Loss')

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

def run_main(
        description: str,
        game_class: typing.Type[chessai.core.game.Game],
        state_class: typing.Type[chessai.core.gamestate.GameState],
        default_board: str | None = None,
        custom_set_cli_args: SetCLIArgs | None = None,
        custom_init_from_args: InitFromArgs = base_init_from_args,
        winning_agent_teams: set[chessai.core.types.Color] | None = None,
        log_results: LogResults | None = base_log_results,
        argv: list[str] | None = None,
        ) -> list[chessai.core.game.GameResult]:
    """
    A full main function to prep and run games.

    Returns the results of the games.
    """

    # Create a CLI parser.
    parser = get_parser(description, default_board, custom_set_cli_args = custom_set_cli_args)

    # Parse the CLI args.
    args = parse_args(parser, game_class, state_class,
            custom_init_from_args = custom_init_from_args,
            argv = argv)

    return run_games(args, winning_agent_teams = winning_agent_teams, log_results = log_results)

def get_parser(
        description: str,
        default_board: str | None = None,
        custom_set_cli_args: SetCLIArgs | None = None,
        ) -> argparse.ArgumentParser:
    """ Get a parser with all the options. """

    parser = argparse.ArgumentParser(description = description)

    # Add logging arguments.
    parser = chessai.core.log.set_cli_args(parser)

    # Add UI arguments.
    parser = chessai.core.ui.set_cli_args(parser)

    # Add game arguments.
    parser = chessai.core.game.set_cli_args(parser, default_board = default_board)

    # Add custom options.
    if (custom_set_cli_args is not None):
        parser = custom_set_cli_args(parser)

    return parser

def parse_args(
        parser: argparse.ArgumentParser,
        game_class: typing.Type[chessai.core.game.Game],
        state_class: typing.Type[chessai.core.gamestate.GameState],
        custom_init_from_args: InitFromArgs = base_init_from_args,
        argv: list[str] | None = None,
        ) -> argparse.Namespace:
    """ Parse the args from the parser returned by get_parser(). """

    args = parser.parse_args(args = argv)

    # Parse logging arguments.
    args = chessai.core.log.init_from_args(parser, args)

    # Parse custom options.
    base_agent_infos, _, kwargs = custom_init_from_args(args)

    # Parse UI options.

    additional_ui_args: dict[str, str] = {}
    null_out_uis = 0

    args = chessai.core.ui.init_from_args(args, null_out_uis = null_out_uis, additional_args = additional_ui_args)

    # Parse game arguments.
    args = chessai.core.game.init_from_args(args, game_class, state_class,
            base_agent_infos = base_agent_infos, **kwargs)

    return args

def run_games(
        args: argparse.Namespace,
        winning_agent_teams: set[chessai.core.types.Color] | None = None,
        log_results: LogResults | None = base_log_results,
        ) -> list[chessai.core.game.GameResult]:
    """
    Run one or more standard games using pre-parsed arguments.
    The arguments are expected to have `_games`,
    as if `chessai.core.game.init_from_args()` `chessai.core.ui.init_from_args` have been called.

    Returns the results of the games.
    """

    if (winning_agent_teams is None):
        winning_agent_teams = set()

    results = []

    for i in range(args.num_games):
        game = args._games[i]
        ui = args._uis[i]

        result = game.run(ui)
        results.append(result)

    if (len(results) > 0):
        if (log_results is not None):
            log_results(results, winning_agent_teams)

    if (args.results_path is not None):
        dict_results = [result.to_dict() for result in results]
        edq.util.json.dump_path(dict_results, args.results_path)

    return results
