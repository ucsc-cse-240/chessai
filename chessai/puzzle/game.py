import argparse
import logging
import random
import typing

import chessai.agents.multiscripted
import chessai.chess.game
import chessai.core.agentinfo
import chessai.core.board
import chessai.core.game
import chessai.core.gamestate
import chessai.puzzle.gamestate

class Game(chessai.chess.game.Game):
    """
    A game following the rules of a chess puzzle.

    The agent wins by completing any one of the board's valid move lines.
    The opposing side is played by a multi scripted agent that follows a scripted continuation.

    The game ends as soon as:
      - The agent plays a move that satisfies the final step of a move line (puzzle solved).
      - The agent plays a move that is not consistent with ANY remaining move line (puzzle failed).
    """

    def __init__(self,
            game_info: chessai.core.game.GameInfo,
            save_path: str | None = None,
            is_replay: bool = False,
            move_lines: list[list[chessai.core.action.Action]] | str | dict[str, typing.Any] | None = None) -> None:
        super().__init__(game_info, save_path, is_replay)

        if (move_lines is None):
            move_lines = []

        if (isinstance(move_lines, dict)):
            move_lines = str(move_lines.get(chessai.puzzle.parser.MOVE_LINES_KEY, ""))

        if (isinstance(move_lines, str)):
            move_lines = chessai.core.action.process_raw_action_list(move_lines)

        self.move_lines: list[list[chessai.core.action.Action]] = move_lines
        """ The move lines of this puzzle. """

        self.start_move_lines: list[list[chessai.core.action.Action]] = move_lines.copy()
        """ The starting move lines of the puzzle, which will remain static throughout the game. """

    def process_args(self, args: argparse.Namespace) -> None:
        # Let the gamestate parse the FEN and determine the puzzle agent.
        initial_state = chessai.puzzle.gamestate.GameState.from_fen(fen = args.board, _capture_move_lines = True)

        move_lines: list[list[chessai.core.action.Action]] = []
        if (args.move_lines is not None):
            # Override the move lines from the file if there are move lines from the CLI.
            move_lines = chessai.core.action.process_raw_action_list(args.move_lines)
        elif (initial_state._move_lines is not None):
            # If the game does not have move lines, use the move lines found in the file.
            move_lines = initial_state._move_lines

        self.move_lines = move_lines
        self.start_move_lines = self.move_lines.copy()

        # Override the dummy player with a scripted agent that follows the move lines.
        self.game_info.agent_infos[initial_state.dummy_player].extra_arguments['move_lines'] = self.start_move_lines.copy()

    def get_initial_state(self,
            rng: random.Random,
            fen: str | None = None) -> chessai.core.gamestate.GameState:
        return chessai.puzzle.gamestate.GameState.from_fen(fen = fen)

    def process_turn(self,
            state: chessai.core.gamestate.GameState,
            action_record: chessai.core.agentaction.AgentActionRecord,
            result: chessai.core.game.GameResult,
            rng: random.Random,
            ) -> chessai.core.gamestate.GameState:
        """
        Process the given agent action and return an updated game state.
        The returned game state may be a copy or modified version of the passed-in game state.
        """

        state = typing.cast(chessai.puzzle.gamestate.GameState, state)

        # The agent has timed out.
        if (action_record.timeout):
            result.timeout_agent_teams.append(action_record.player)
            state.process_agent_timeout(action_record.player)
            return state

        # The agent has crashed.
        if (action_record.crashed):
            result.crash_agent_teams.append(action_record.player)
            state.process_agent_crash(action_record.player)
            return state

        action = action_record.get_action()
        if (action not in state.get_legal_actions()):
            raise ValueError(f"Illegal action for agent {action_record.player}: '{action}' of type '{type(action)}'.")

        # Check whether the move follows any of the remaining move lines.
        if (action not in self._next_puzzle_moves()):
            logging.info(
                "Incorrect action for agent '%s': '%s' of type '%s'.",
                action_record.player, action, type(action),
            )

            # The agent failed to solve the puzzle, so the game is over.
            state.game_over = True
            return state

        self._call_state_process_turn_full(state, action, rng)

        # Progress the move lines of the puzzle.
        self._update_move_lines(state, action)

        return state

    def check_end(self, state: chessai.core.gamestate.GameState) -> bool:
        if state.game_over:
            return True

        return (len(self.move_lines) == 0)

    def _next_puzzle_moves(self) -> list[chessai.core.action.Action]:
        """ Get the list of possible next moves from the puzzle's move lines. """

        move_options = []

        for move_line in self.move_lines:
            if (len(move_line) > 0):
                move_options.append(move_line[0])

        return move_options

    def _update_move_lines(self, state: chessai.puzzle.gamestate.GameState, action: chessai.core.action.Action) -> bool:
        """
        Update the possible puzzle lines based on the action taken.

        Returns whether the action matched at least one move line.
        """

        new_move_lines = []
        matched_move_line = False

        for move_line in self.move_lines:
            if (len(move_line) == 0):
                continue

            # Skip if the action is not consistent with the move line.
            if (move_line[0] != action):
                continue

            matched_move_line = True

            new_move_line = move_line[1:]

            # If there is nothing left in the move line, skip it.
            if (len(new_move_line) == 0):
                continue

            new_move_lines.append(new_move_line)

        self.move_lines = new_move_lines

        # If the action matched a move line and there are no remaining move lines, the puzzle is solved.
        if (matched_move_line and (len(self.move_lines) == 0)):
            state.puzzle_solved = True

        return matched_move_line
