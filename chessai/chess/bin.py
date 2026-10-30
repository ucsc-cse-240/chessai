"""
The main executable for running a game of Chess.
"""

import argparse
import typing

import chessai.chess.game
import chessai.util.alias
import chessai.util.bin

def set_cli_args(parser: argparse.ArgumentParser, **kwargs: typing.Any) -> argparse.ArgumentParser:
    """
    Set Chess-specific CLI arguments.
    This is a sibling to init_from_args(), as the arguments set here can be interpreted there.
    """

    parser.add_argument('--white-team', dest = 'white_team',
            action = 'store', type = str, default = chessai.util.alias.AGENT_USER_INPUT.short,
            help = ('Select the chess team that will play on the white team (default: %(default)s).'
                    + f' Builtin teams: {chessai.util.alias.AGENT_SHORT_NAMES}.'))

    parser.add_argument('--black-team', dest = 'black_team',
            action = 'store', type = str, default = chessai.util.alias.AGENT_RANDOM.short,
            help = ('Select the chess team that will play on the black team (default: %(default)s).'
                    + f' Builtin teams: {chessai.util.alias.AGENT_SHORT_NAMES}.'))

    return parser

def init_from_args(args: argparse.Namespace) -> tuple[dict[chessai.core.types.Color, chessai.core.agentinfo.AgentInfo],
        list[chessai.core.types.Color], dict[str, typing.Any]]:
    """
    Setup agents based on Chess rules.

    Agent infos are supplied via the `--white-team` and `--black-team` arguments.
    Missing agents will be filled in with random agents.
    """

    base_agent_infos: dict[chessai.core.types.Color, chessai.core.agentinfo.AgentInfo] = {
        chessai.core.types.Color.WHITE: chessai.core.agentinfo.AgentInfo(name = args.white_team),
        chessai.core.types.Color.BLACK: chessai.core.agentinfo.AgentInfo(name = args.black_team),
    }

    return base_agent_infos, [], {}

def main(argv: list[str] | None = None) -> list[chessai.core.game.GameResult]:
    """
    Invoke a game of chess.

    Will return the results of the games.
    """

    return chessai.util.bin.run_main(
        description = "Play a game of chess.",
        game_class = chessai.chess.game.Game,
        state_class = chessai.chess.gamestate.GameState,
        default_board = None,
        custom_set_cli_args = set_cli_args,
        custom_init_from_args = init_from_args,
        argv = argv,
    )

if (__name__ == '__main__'):
    main()
