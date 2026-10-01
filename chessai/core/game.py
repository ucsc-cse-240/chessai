import abc
import argparse
import datetime
import copy
import logging
import math
import os
import random
import typing

import edq.util.serial

import chessai.core.action
import chessai.core.agentinfo
import chessai.core.board
import chessai.core.gameparser
import chessai.core.isolation.level
import chessai.core.ui
import chessai.util.alias

DEFAULT_MAX_MOVES: int = -1
DEFAULT_AGENT_START_TIMEOUT: float = 0.0
DEFAULT_AGENT_END_TIMEOUT: float = 0.0
DEFAULT_AGENT_ACTION_TIMEOUT: float = 0.0

DEFAULT_AGENT: str = chessai.util.alias.AGENT_RANDOM.short

class GameInfo(edq.util.serial.DictConverter):
    """
    A simple container that holds common information about a game.
    """

    def __init__(self,
            agent_infos: dict[chessai.core.types.Color, chessai.core.agentinfo.AgentInfo],
            start_fen: str | None = None,
            isolation_level: chessai.core.isolation.level.Level = chessai.core.isolation.level.Level.NONE,
            max_moves: int = DEFAULT_MAX_MOVES,
            agent_start_timeout: float = DEFAULT_AGENT_START_TIMEOUT,
            agent_end_timeout: float = DEFAULT_AGENT_END_TIMEOUT,
            agent_action_timeout: float = DEFAULT_AGENT_ACTION_TIMEOUT,
            seed: int | None = None,
            event: str | None = None,
            site: str | None = None,
            date: str | None = None,
            game_round: str | None = None,
            white_player: str | None = None,
            black_player: str | None = None,
            extra_info: dict[str, typing.Any] | None = None,
            wait_for_user: bool = False,
            ) -> None:
        if (seed is None):
            seed = random.randint(0, 2**64)

        self.seed: int = seed
        """ The random seed for this game's RNG. """

        self.agent_infos: dict[chessai.core.types.Color, chessai.core.agentinfo.AgentInfo] = agent_infos
        """ The required information for creating the agents for this game. """

        if (len(self.agent_infos) == 0):
            raise ValueError("No agents provided.")

        if (start_fen is None):
            start_fen = chessai.core.gamestate.DEFAULT_FEN

        self.start_fen: str = start_fen
        """ The starting fen for this game. """

        self.isolation_level: chessai.core.isolation.level.Level = isolation_level
        """ The isolation level to use for this game. """

        self.max_moves: int = max_moves
        """
        The total number of moves (between all agents) allowed for this game.
        If -1, unlimited moves are allowed.
        """

        self.agent_start_timeout: float = agent_start_timeout
        """
        The maximum number of seconds an agent is allowed when starting a game.
        If <= 0, unlimited time is allowed.
        """

        self.agent_end_timeout: float = agent_end_timeout
        """
        The maximum number of seconds an agent is allowed when ending a game.
        If <= 0, unlimited time is allowed.
        """

        self.agent_action_timeout: float = agent_action_timeout
        """
        The maximum number of seconds an agent is allowed when getting an action.
        If <= 0, unlimited time is allowed.
        """

        if (event is None):
            event = '?'

        self.event: str = event
        """ The tournament or match event name. """

        if (site is None):
            site = '?'

        self.site: str = site
        """ The location of the event. """

        if (date is None):
            date = '????.??.??'

        self.date: str = date
        """ The starting date of the game. """

        if (game_round is None):
            game_round = '?'

        self.game_round: str = game_round
        """ The playing round ordinal. """

        if (white_player is None):
            white_player = '?'

        self.white_player: str = white_player
        """ The name of the white player. """

        if (black_player is None):
            black_player = '?'

        self.black_player: str = black_player
        """ The name of the black player. """

        if (extra_info is None):
            extra_info = {}

        self.extra_info: dict[str, typing.Any] = extra_info
        """ Any additional arguments passed to the game. """

        self.wait_for_user: bool = wait_for_user
        """ Pause the game between each move until the user is ready. """

class GameResult(edq.util.serial.DictConverter):
    """ The result of running a game. """

    def __init__(self,
            game_id: int,
            game_info: GameInfo,
            termination_reason: chessai.core.types.TerminationReason | None = None,
            score: float = 0,
            end_fen: str | None = None,
            game_timeout: bool = False,
            timeout_agent_teams: list[chessai.core.types.Color] | None = None,
            crash_agent_teams: list[chessai.core.types.Color] | None = None,
            winning_agent_teams: list[chessai.core.types.Color] | None = None,
            start_time: edq.util.time.Timestamp | None = None,
            end_time: edq.util.time.Timestamp | None = None,
            history: list[chessai.core.agentaction.AgentActionRecord] | None = None,
            agent_complete_records: dict[chessai.core.types.Color, chessai.core.agentaction.AgentActionRecord] | None = None,
            **kwargs: typing.Any,
            ) -> None:
        self.game_id: int = game_id
        """ The ID of the game result. """

        self.game_info: GameInfo = game_info
        """ The core information about this game. """

        self.termination_reason: chessai.core.types.TerminationReason | None = termination_reason
        """ The reason the game ended. """

        self.score: float = score
        """ The score of the game from white's perspective. """

        self.end_fen = end_fen
        """ The fen the board is in at the end of the game. """

        if (start_time is None):
            start_time = edq.util.time.Timestamp.now()

        self.start_time: edq.util.time.Timestamp = start_time
        """ The time the game started at. """

        self.end_time: edq.util.time.Timestamp | None = end_time
        """ The time the game ended at. """

        if (history is None):
            history = []

        self.history: list[chessai.core.agentaction.AgentActionRecord] = history
        """ The history of actions taken by each agent in this game. """

        if (agent_complete_records is None):
            agent_complete_records = {}

        self.agent_complete_records: dict[chessai.core.types.Color, chessai.core.agentaction.AgentActionRecord] = agent_complete_records
        """
        The record recieved from an agent when the game finishes.
        For agents that learn, this may include information that the agent learned this game.
        """

        self.game_timeout: bool = game_timeout
        """ Indicates that the game has timed out (reached the maximum number of moves). """

        if (timeout_agent_teams is None):
            timeout_agent_teams = []

        self.timeout_agent_teams: list[chessai.core.types.Color] = timeout_agent_teams
        """ The list of agents that timed out in this game. """

        if (crash_agent_teams is None):
            crash_agent_teams = []

        self.crash_agent_teams: list[chessai.core.types.Color] = crash_agent_teams
        """ The list of agents that crashed in this game. """

        if (winning_agent_teams is None):
            winning_agent_teams = []

        self.winning_agent_teams: list[chessai.core.types.Color] = winning_agent_teams
        """
        The list of agents that won this game.
        An empty list indicates a tie.

        Games may interpret this value in different ways.
        """

    def get_duration_secs(self) -> float:
        """
        Get the game's duration in seconds.
        Will return positive infinity if the game has no end time
        (it is still going or crashed (in very rare cases)).
        """

        if (self.end_time is None):
            return math.inf

        return self.end_time.sub(self.start_time).to_secs()

class Game(abc.ABC):
    """
    A game that can be run in chessai.
    Games combine the rules, layouts, and agents to run.
    """

    def __init__(self,
                 game_info: GameInfo,
                 save_path: str | None = None,
                 is_replay: bool = False,
                 initial_actions: list[chessai.core.action.Action] | None = None,
                 action_history: list[chessai.core.action.Action] | None = None,
                 expected_result: chessai.core.gameparser.PGNResult = chessai.core.gameparser.PGNResult.UNKNOWN,
                 ) -> None:
        self.game_info: GameInfo = game_info
        """ The core information about this game. """

        self._save_path: str | None = save_path
        """ Where to save the results of this game. """

        self._is_replay: bool = is_replay
        """
        Indicates that this game is being loaded from a replay.
        Some behavior, like saving the result, will be modified.
        """

        if (initial_actions is None):
            initial_actions = []

        self.initial_actions: list[chessai.core.action.Action] = initial_actions
        """ The moves to be played at the beginning of the game. """

        if (action_history is None):
            action_history = []

        self.action_history: list[chessai.core.action.Action] = action_history
        """ The actions taken throughout the game. """

        self.expected_result: chessai.core.gameparser.PGNResult = expected_result
        """ The expected result from the PGN: '1-0', '0-1', '1/2-1/2', or '*'. """

    @classmethod
    def from_pgn(cls,
                 pgn: str,
                 state_class: typing.Type[chessai.core.gamestate.GameState],
                 game_info: GameInfo,
                 save_path: str | None = None,
                 **kwargs: typing.Any) -> typing.Optional['Game']:
        """
        Create a Game from a PGN.

        The game will be initialized with metadata from the PGN headers and will store the moves for replay.

        Returns the game and whether the PGN parsing was successful.
        """

        parsed_pgn = chessai.core.gameparser.parse_pgn(pgn, state_class)
        if (parsed_pgn is None):
            return None

        # Extract starting FEN from optional headers or use default.
        start_fen = parsed_pgn.get_starting_fen()
        if (start_fen is not None):
            game_info.start_fen = start_fen

        # Extract header information into the game info.
        game_info.event = parsed_pgn.headers.event
        game_info.site = parsed_pgn.headers.site
        game_info.date = parsed_pgn.headers.date
        game_info.game_round = parsed_pgn.headers.round
        game_info.white_player = parsed_pgn.headers.white
        game_info.black_player = parsed_pgn.headers.black
        game_info.extra_info.update(parsed_pgn.optional_headers)

        return cls(
            game_info = game_info,
            save_path = save_path,
            is_replay = True,
            initial_actions = parsed_pgn.initial_actions,
            expected_result = parsed_pgn.result,
            **kwargs
        )

    def to_pgn(self,
            final_state: chessai.core.gamestate.GameState,
            termination_reason: chessai.core.types.TerminationReason,
            ) -> str:
        """ Returns the PGN representation of the Game. """

        if (termination_reason in [chessai.core.types.TerminationReason.CHECKMATE,
                                   chessai.core.types.TerminationReason.FORFEIT]):
            winners = final_state.get_winners()
            if (chessai.core.types.Color.WHITE in winners):
                result = chessai.core.gameparser.PGNResult.WHITE_WIN
            elif (chessai.core.types.Color.BLACK in winners):
                result = chessai.core.gameparser.PGNResult.BLACK_WIN
            else:
                result = chessai.core.gameparser.PGNResult.TIE
        elif (termination_reason in [chessai.core.types.TerminationReason.STALEMATE,
                                     chessai.core.types.TerminationReason.INSUFFICIENT_MATERIAL,
                                     chessai.core.types.TerminationReason.ACCEPTED_DRAW_PROPOSAL]):
            result = chessai.core.gameparser.PGNResult.TIE
        elif (termination_reason == chessai.core.types.TerminationReason.IN_PROGRESS):
            result = chessai.core.gameparser.PGNResult.IN_PROGRESS
        else:
            result = chessai.core.gameparser.PGNResult.UNKNOWN

        headers = chessai.core.gameparser.StandardHeaders(
                event = self.game_info.event,
                site = self.game_info.site,
                date = self.game_info.date,
                game_round = self.game_info.game_round,
                white = self.game_info.white_player,
                black = self.game_info.black_player,
                result = result)

        return chessai.core.gameparser.to_pgn(headers, self.game_info.extra_info, type(final_state),
                                              self.game_info.start_fen, self.action_history)

    def process_args(self, args: argparse.Namespace) -> None:
        """ Process any special arguments from the command-line. """

    @abc.abstractmethod
    def get_initial_state(self,
            rng: random.Random,
            fen: str | None = None) -> chessai.core.gamestate.GameState:
        """ Create the initial state for this game. """

    def process_turn(self,
                     state: chessai.core.gamestate.GameState,
                     action_record: chessai.core.agentaction.AgentActionRecord,
                     result: GameResult,
                     rng: random.Random) -> chessai.core.gamestate.GameState:
        """
        Process the given agent action and return an updated game state.
        The returned game state may be a copy or modified version of the passed in game state.
        """

        # The agent has timed out.
        if (action_record.timeout):
            result.timeout_agent_teams.append(action_record.player)
            result.termination_reason = chessai.core.types.TerminationReason.AGENT_TIMEOUT
            state.process_agent_timeout(action_record.player)
            return state

        # The agent has crashed.
        if (action_record.crashed):
            result.crash_agent_teams.append(action_record.player)
            result.termination_reason = chessai.core.types.TerminationReason.AGENT_CRASHED
            state.process_agent_crash(action_record.player)
            return state

        action = action_record.get_action()
        if (action not in state.get_legal_actions()):
            raise ValueError(f"Illegal action for agent {action_record.player}: '{action.uci()}' of type '{type(action)}'.")

        # Add the action to the action history.
        self.action_history.append(action)

        self._call_state_process_turn_full(state, action, rng)

        return state

    def _call_state_process_turn_full(self,
            state: chessai.core.gamestate.GameState,
            action: chessai.core.action.Action,
            rng: random.Random,
            **kwargs: typing.Any) -> None:
        """ Call on the game state to process a full turn. """

        state.process_turn_full(action, rng, **kwargs)

    def check_end(self, state: chessai.core.gamestate.GameState) -> bool:
        """
        Check to see if the game is over.
        Return True if the game is now over, False otherwise.

        By default, this will check chessai.core.gamestate.GameState.game_over
        and chessai.core.gamestate.GameState.is_game_over(),
        but child games can override for more complex functionality.
        """

        return (state.game_over or state.is_game_over())

    def game_complete(self, state: chessai.core.gamestate.GameState, result: GameResult) -> None:
        """
        Make any last adjustments to the game result after the game is over.
        """

    def _wait_for_user(self) -> None:
        input("Press Enter to resume the game...")

    def run(self, ui: chessai.core.ui.UI) -> GameResult:
        """
        The main "game loop" for all games.
        """

        logging.debug("Starting a game with seed: %d.", self.game_info.seed)

        # Create a new random number generator just for this game.
        rng = random.Random(self.game_info.seed)

        # Keep track of what happens during this game.
        game_id = rng.randint(0, 2**64)
        result = GameResult(game_id, self.game_info)

        # Initialize the agent isolator.
        isolator = self.game_info.isolation_level.get_isolator()
        isolator.init_agents(self.game_info.agent_infos)

        # Create the initial game state (and force it's seed).
        state = self.get_initial_state(rng, self.game_info.start_fen)
        state.seed = game_id
        state.game_start()

        # Notify agents about the start of the game.
        records = isolator.game_start(rng, state, self.game_info.agent_start_timeout)
        for record in records.values():
            if (record.timeout):
                result.timeout_agent_teams.append(record.player)
                state.process_agent_timeout(record.player)
                result.termination_reason = chessai.core.types.TerminationReason.AGENT_TIMEOUT
            elif (record.crashed):
                result.crash_agent_teams.append(record.player)
                state.process_agent_crash(record.player)
                result.termination_reason = chessai.core.types.TerminationReason.AGENT_CRASHED

        state.agents_game_start(records)

        # Start the UI.
        ui.game_start(state)

        while (not self.check_end(state)):
            logging.trace("Turn %d, agent %s.", state.fullmove_number, state.turn) # type: ignore[attr-defined]  # pylint: disable=no-member

            if (self.game_info.wait_for_user):
                self._wait_for_user()

            if (len(self.initial_actions) > 0):
                # Get the action from the pre-loaded actions.
                action = self.initial_actions.pop(0)
                agent_action = chessai.core.agentaction.AgentAction(action = action)
                duration = edq.util.time.Duration(0)

                action_record = chessai.core.agentaction.AgentActionRecord(state.turn, agent_action, duration)
            else:
                # Get the next action from the agent.
                action_record = isolator.get_action(state, self.game_info.agent_action_timeout)

            # Execute the next action and update the state.
            state = self.process_turn(state, action_record, result, rng)

            # Update the UI.
            ui.update(state)

            # Update the game result and move history.
            result.history.append(action_record)

            # Check for game ending conditions.
            if (self.check_end(state)):
                break

            # Check if this game has ran for the maximum number of moves.
            if (0 < self.game_info.max_moves <= len(result.history)):
                state.process_game_timeout()
                result.game_timeout = True
                result.termination_reason = chessai.core.types.TerminationReason.GAME_TIMEOUT
                break

        # Mark the end time of the game.
        result.end_time = edq.util.time.Timestamp.now()

        # Notify the state about the end of the game.
        (winners, score) = state.game_complete()
        result.winning_agent_teams += winners
        result.score = score

        if (result.termination_reason is None):
            result.termination_reason = state.get_termination_reason()

        result.end_fen = state.get_fen()

        # Notify agents about the end of this game.
        result.agent_complete_records = isolator.game_complete(state, self.game_info.agent_end_timeout)

        # All the game to make final updates to the result.
        self.game_complete(state, result)

        # Update the UI.
        ui.game_complete(state, result.termination_reason)

        # Cleanup
        isolator.close()
        ui.close()

        if ((not self._is_replay) and (self._save_path is not None)):
            logging.info("Saving results to '%s'.", self._save_path)

            pgn = self.to_pgn(state, result.termination_reason)
            edq.util.dirent.write_file(self._save_path, pgn)

        return result

def set_cli_args(parser: argparse.ArgumentParser, default_board: str | None = None) -> argparse.ArgumentParser:
    """
    Set common CLI arguments.
    This is a sibling to init_from_args(), as the arguments set here can be interpreted there.
    """

    parser.add_argument('--board', dest = 'board',
            action = 'store', type = str, default = default_board,
            help = ('Play on this board (default: %(default)s).'
                    + ' This may be a FEN of the board.'
                    + ' It may also be the full path to a board, or just a filename.'
                    + ' If just a filename, than the `chessai/resources/boards` directory will be checked (using a ".fen" extension.'))

    parser.add_argument('--num-games', dest = 'num_games',
            action = 'store', type = int, default = 1,
            help = 'The number of games to play (default: %(default)s).')

    parser.add_argument('--seed', dest = 'seed',
            action = 'store', type = int, default = None,
            help = 'The random seed for the game (will be randomly generated if not set).')

    parser.add_argument('--max-moves', dest = 'max_moves',
            action = 'store', type = int, default = DEFAULT_MAX_MOVES,
            help = 'The maximum number of moves (total for all agents) allowed in this game (-1 for unlimited) (default: %(default)s).')

    parser.add_argument('--agent-start-timeout', dest = 'agent_start_timeout',
            action = 'store', type = float, default = DEFAULT_AGENT_START_TIMEOUT,
            help = ('The maximum number of seconds each agent is allowed when starting a game (<= 0 for unlimited time) (default: %(default)s).'
                    + ' Note that the "none" isolation level cannot enforce timeouts.'))

    parser.add_argument('--agent-end-timeout', dest = 'agent_end_timeout',
            action = 'store', type = float, default = DEFAULT_AGENT_END_TIMEOUT,
            help = ('The maximum number of seconds each agent is allowed when ending a game (<= 0 for unlimited time) (default: %(default)s).'
                    + ' Note that the "none" isolation level cannot enforce timeouts.'))

    parser.add_argument('--agent-action-timeout', dest = 'agent_action_timeout',
            action = 'store', type = float, default = DEFAULT_AGENT_ACTION_TIMEOUT,
            help = ('The maximum number of seconds each agent is allowed when getting an action (<= 0 for unlimited time) (default: %(default)s).'
                    + ' Note that the "none" isolation level cannot enforce timeouts.'))

    parser.add_argument('--isolation', dest = 'isolation_level', metavar = 'LEVEL',
            action = 'store', type = str, default = chessai.core.isolation.level.Level.NONE.value,
            choices = chessai.core.isolation.level.LEVELS,
            help = ('Set the agent isolation level for this game (default: %(default)s).'
                    + ' Choose one of:'
                    + ' `none` -- Do not make any attempt to isolate the agent code from the game (fastest and least secure),'
                    + ' `process` -- Run the agent code in a separate process'
                    + ' (offers some protection, but still vulnerable to disk or execution exploits),'
                    + ' `tcp` -- Open TCP listeners to communicate with agents (most secure, requires additional work to set up agents).'))

    parser.add_argument('--agent-arg', dest = 'raw_agent_args', metavar = 'ARG',
            action = 'append', type = str, default = [],
            help = ('Specify arguments directly to agents (may be used multiple times).'
                    + ' The value for this argument must be formatted as "player::key=value",'
                    + ' for example to set `foo = 9` for white and `bar = a` for black, we can use:'
                    + ' `--agent-arg white::foo=9 --agent-arg black::bar=a`.'))

    parser.add_argument('--save-path', dest = 'save_path',
            action = 'store', type = str, default = None,
            help = ('If specified, write the result of this game to the specified location.'
                    + ' This file can be replayed with `--replay-path`.'))

    parser.add_argument('--replay-path', dest = 'replay_path',
            action = 'store', type = str, default = None,
            help = ('If specified, replay the game whose result was saved at the specified path with `--save-path`.'
                    + ' This may be a PGN of the game.'
                    + ' It may also be the full path to a game, or just a filename.'
                    + ' If just a filename, than the `chessai/resources/games` directory will be checked (using a ".pgn" extension.'))

    parser.add_argument('--wait-for-input', dest = 'wait_for_user',
            action = 'store_true',
            help = ('Pause the game between each move until the user resumes the game.'))

    return parser

def init_from_args(
        args: argparse.Namespace,
        game_class: typing.Type[Game],
        state_class: typing.Type[chessai.core.gamestate.GameState],
        base_agent_infos: dict[chessai.core.types.Color, chessai.core.agentinfo.AgentInfo] | None = None,
        **kwargs: typing.Any,
        ) -> argparse.Namespace:
    """
    Take in args from a parser that was passed to set_cli_args(),
    and initialize the proper components.
    This will create a number of games (and related resources)
    based on `--num-games` + `--num-training`.
    Each of these resources will be placed in their respective list at
    `args._fens`, `args._agent_infos`, or `args._games`.
    """

    if (base_agent_infos is None):
        base_agent_infos = {}

    if (args.num_games <= 0):
        raise ValueError(f"At least one game must be played (--num-games), {args.num_games} was specified.")

    # Establish an RNG to generate seeds for each game using the given seed.
    seed = args.seed
    if (seed is None):
        seed = random.randint(0, 2**64)

    logging.debug("Using source seed for games: %d.", seed)
    rng = random.Random(seed)

    agents = [chessai.core.types.Color.WHITE, chessai.core.types.Color.BLACK]
    agent_infos = _parse_agent_infos(agents, args.raw_agent_args, base_agent_infos)

    base_save_path = args.save_path

    all_fens: list[str] = []
    all_agent_infos = []
    all_games = []

    for i in range(args.num_games):
        game_seed = rng.randint(0, 2**64)

        all_agent_infos.append(copy.deepcopy(agent_infos))
        all_fens.append(args.board)

        white_agent_info = all_agent_infos[-1].get(chessai.core.types.Color.WHITE, None)
        if (white_agent_info is not None):
            white_reference = white_agent_info.name
            if (isinstance(white_reference, chessai.util.reflection.Reference)):
                white_player = str(white_reference)
            else:
                white_player = white_reference
        else:
            white_player = '?'

        black_agent_info = all_agent_infos[-1].get(chessai.core.types.Color.BLACK, None)
        if (black_agent_info is not None):
            black_reference = black_agent_info.name
            if (isinstance(black_reference, chessai.util.reflection.Reference)):
                black_player = str(black_reference)
            else:
                black_player = black_reference
        else:
            black_player = '?'

        game_info = GameInfo(
            all_agent_infos[-1],
            start_fen = all_fens[-1],
            isolation_level = chessai.core.isolation.level.Level(args.isolation_level),
            max_moves = args.max_moves,
            agent_start_timeout = args.agent_start_timeout,
            agent_end_timeout = args.agent_end_timeout,
            agent_action_timeout = args.agent_action_timeout,
            seed = game_seed,
            event = 'Casual Chessai Game',
            site = 'https://github.com/ucsc-cse-240/chessai',
            date = datetime.date.today().isoformat(),
            game_round = str(i),
            white_player = white_player,
            black_player = black_player,
            wait_for_user = args.wait_for_user,
        )

        # Suffix the save path if there is more than one game.
        save_path = base_save_path
        if ((save_path is not None) and (args.num_games > 1)):
            parts = os.path.splitext(save_path)
            save_path = f"{parts[0]}_{i:03d}{parts[1]}"

        if (args.replay_path is None):
            game_args = {
                'game_info': game_info,
                'save_path': save_path,
            }

            game = game_class(**game_args)
        else:
            raw_game = game_class.from_pgn(args.replay_path, state_class, game_info, save_path)
            if (raw_game is None):
                raise ValueError(f"Failed to initialize game number {i} from the PGN: '{args.replay_path}'.")

            game = raw_game

        game.process_args(args)

        all_games.append(game)

    setattr(args, '_fens', all_fens)
    setattr(args, '_agent_infos', all_agent_infos)
    setattr(args, '_games', all_games)

    return args

def _parse_agent_infos(
        agent_teams: list[chessai.core.types.Color],
        raw_args: list[str],
        base_agent_infos: dict[chessai.core.types.Color, chessai.core.agentinfo.AgentInfo],
        ) -> dict[chessai.core.types.Color, chessai.core.agentinfo.AgentInfo]:
    # Initialize with random agents.
    agent_info = {agent_team: chessai.core.agentinfo.AgentInfo(name = DEFAULT_AGENT) for agent_team in sorted(agent_teams)}

    # Take any args from the base args.
    for (team, base_agent_info) in base_agent_infos.items():
        if (team in agent_info):
            agent_info[team].update(base_agent_info)

    # Update with CLI args.
    for raw_arg in raw_args:
        raw_arg = raw_arg.strip()
        if (len(raw_arg) == 0):
            continue

        parts = raw_arg.split('::', 1)
        if (len(parts) != 2):
            raise ValueError(f"Improperly formatted CLI agent argument: '{raw_arg}'.")

        raw_team = parts[0].strip().lower()
        team_color: chessai.core.types.Color | None = None
        if (raw_team in ('white', 'w')):
            team_color = chessai.core.types.Color.WHITE
        elif (raw_team in ('black', 'b')):
            team_color = chessai.core.types.Color.BLACK
        else:
            raise ValueError(f"CLI agent argument has an unknown agent team: {parts[0]}.")

        raw_pair = parts[1]

        parts = raw_pair.split('=', 1)
        if (len(parts) != 2):
            raise ValueError(f"Improperly formatted CLI agent argument key/value pair: '{raw_pair}'.")

        key = parts[0].strip()
        value = parts[1].strip()

        agent_info[team_color].set_from_string(key, value)

    return agent_info
