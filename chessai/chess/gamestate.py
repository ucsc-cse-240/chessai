import typing

import edq.util.serial

import chessai.chess.piece
import chessai.core.action
import chessai.core.agent
import chessai.core.gamestate

class GameState(chessai.core.gamestate.GameState):
    """ A game state specific to a standard Pacman game. """

    def game_complete(self) -> tuple[list[chessai.core.types.Color], float]:
        winners = self.get_winners()

        # Score is based on white's perspective using standard chess scoring.
        if (chessai.core.types.Color.WHITE in winners):
            score = 1.0
        elif (chessai.core.types.Color.BLACK in winners):
            score = 0.0
        else:
            score = 0.5

        return (winners, score)

    def is_check(self, color: chessai.core.types.Color, started_in_check: bool = True) -> bool:
        # Find the king of the given color.
        king_coordinate = self.get_king_coordinate(color)

        # If there is no King, they cannot be in check.
        # This should never happen in standard chess games with valid positions.
        if (king_coordinate is None):
            return False

        # Get the most recent action to try to avoid work when not doing a full check.
        previous_action = self.get_previous_action()

        if ((not started_in_check) and isinstance(previous_action, chessai.core.action.MoveAction)):
            check_potential = self._has_check_potential(king_coordinate, previous_action)
        else:
            check_potential = True

        # Skip checking moves that could not have opened us to check.
        if (not check_potential):
            return False

        # Check if any opponent piece can attack the king's coordinate.
        old_turn = self.turn
        self.turn = color.opposite()

        try:
            opponent_actions = self._get_pseudo_legal_moves()
            for action in opponent_actions:
                if (action.end_coordinate == king_coordinate):
                    return True

            return False
        finally:
            self.turn = old_turn

    def get_king_coordinate(self, color: chessai.core.types.Color) -> chessai.core.coordinate.Coordinate | None:
        """ Get the coordinate of the king for the given color. """

        for (file, rank_dict) in self.board.pieces.items():
            for (rank, piece) in rank_dict.items():
                if ((piece.color == color) and (isinstance(piece, chessai.chess.piece.King))):
                    return chessai.core.coordinate.Coordinate(file, rank)

        # If there's no king, the position is invalid, which should never happen.
        return None

    def _has_check_potential(self, king_coordinate: chessai.core.coordinate.Coordinate, previous_action: chessai.core.action.MoveAction) -> bool:
        """
        Returns whether the player who played the most recent move could be in check.

        Assumes the player was not in check before playing their most recent move.
        """

        # Check if the king just moved, which means it could have moved into check.
        if (previous_action.end_coordinate == king_coordinate):
            return True

        # Check if a piece moved on the king's file, rank, or diagonal.
        # This move would allow for discovery checks.
        if ((previous_action.start_coordinate.file == king_coordinate.file) or (previous_action.start_coordinate.rank == king_coordinate.rank)):
            # A piece moved on the king's rank or file, so the king could be under attack from a rook or queen.
            return True

        # Check the diagonal.
        file_delta = abs(king_coordinate.file - previous_action.start_coordinate.file)
        rank_delta = abs(king_coordinate.rank - previous_action.start_coordinate.rank)

        # If a piece moved away from the king's diagonal, the king could be under attack from a bishop or queen.
        return file_delta == rank_delta

    def _should_reset_halfmove_clock(self, action: chessai.core.action.Action, piece: chessai.core.piece.Piece) -> bool:
        return (isinstance(piece, chessai.chess.piece.Pawn))

    def _get_pseudo_legal_moves(self) -> list[chessai.core.action.MoveAction]:
        # Get the base movement from all pieces.
        actions = self._get_base_move_actions()

        # Add any castling moves.
        actions.extend(self._get_castling_moves())

        # Add any pawn double pushes.
        actions.extend(self._get_pawn_double_pushes())

        # Add any en-passant captures.
        actions.extend(self._get_en_passant_captures())

        return actions

    def _get_base_move_actions(self) -> list[chessai.core.action.MoveAction]:
        """
        Expands all movement vectors from the pieces on the board.
        Pieces will move until they can capture or reach the end of the board.

        Detects when pawns reach the end of the board and can be promoted.
        """

        actions: list[chessai.core.action.MoveAction] = []

        # Determine the rank for pawn promotions.
        if (self.turn == chessai.core.types.Color.WHITE):
            promotion_rank = self.board.num_ranks - 1
        else:
            promotion_rank = 0

        for (file, rank_dict) in self.board.pieces.items():
            for (rank, piece) in rank_dict.items():
                if (piece.color != self.turn):
                    continue

                for movement_vector in piece.move_vectors():
                    current_rank = rank
                    current_file = file

                    coordinate = chessai.core.coordinate.Coordinate(file, rank)

                    num_repetitions = movement_vector.num_repetitions
                    while (num_repetitions != 0):
                        current_file += movement_vector.file_delta
                        current_rank += movement_vector.rank_delta
                        if (not self.board.is_within_bounds(current_file, current_rank)):
                            break

                        occupant = self.board.get(current_file, current_rank)

                        is_occupied = occupant is not None
                        is_enemy    = (occupant is not None) and (occupant.color != piece.color)
                        is_ally     = (occupant is not None) and (occupant.color == piece.color)

                        # No movement type can move on top of an ally.
                        if (is_ally):
                            break

                        # Push movement types cannot capture.
                        if ((movement_vector.kind == chessai.core.piece.MoveKind.PUSH) and is_occupied):
                            break

                        # Capture movement types must target an enemy.
                        if ((movement_vector.kind == chessai.core.piece.MoveKind.CAPTURE) and (not is_enemy)):
                            break

                        current_coordinate = chessai.core.coordinate.Coordinate(current_file, current_rank)

                        # Check if this action would lead to a pawn promotion.
                        if ((isinstance(piece, chessai.chess.piece.Pawn)) and (current_coordinate.rank == promotion_rank)):
                            actions.extend(self._get_promotion_actions(coordinate, current_coordinate))
                        else:
                            actions.append(chessai.core.action.MoveAction(coordinate, current_coordinate))

                        if (is_occupied):
                            break

                        num_repetitions -= 1

        return actions

    def _process_special_move(self,
                              action: chessai.core.action.Action,
                              piece: chessai.core.piece.Piece) -> tuple[bool, chessai.core.coordinate.Coordinate | None]:
        if (not isinstance(action, chessai.core.action.MoveAction)):
            return False, None

        # Update castling rights.
        self._update_castling_rights(action, piece)

        # Handle promoting pieces.
        if isinstance(action, chessai.core.action.PromotionAction):
            self._handle_promotion(action, piece)

        # Detect castling by seeing if the king moved more than two files.
        if ((isinstance(piece, chessai.chess.piece.King))
                and (action.start_coordinate.file_distance(action.end_coordinate) > 1)):
            self._handle_castling(action, piece)
            return False, None

        # Detect en-passant by checking if a pawn moves diagonally to an empty coordinate.
        if ((isinstance(piece, chessai.chess.piece.Pawn))
                and (action.start_coordinate.file_distance(action.end_coordinate) == 1)
                and (self.get(action.end_coordinate) is None)):
            en_passant_coordinate = self._handle_en_passant(action, piece)
            return True, en_passant_coordinate

        return False, None

    def is_insufficient_material(self) -> bool:
        # Meta actions cannot cause a game to become in an insufficient material state.
        if (not isinstance(self.get_previous_action(), chessai.core.action.MoveAction)):
            return False

        for color in chessai.core.types.Color:
            if (not self._is_insufficient_material(color)):
                return False

        return True

    def _is_insufficient_material(self, color: chessai.core.types.Color) -> bool:
        """
        Checks if the given color has insufficient winning material.

        This is guaranteed to return False if the color can still win the game.

        The converse does not necessarily hold: only material is considered (including bishop square colors), not piece positions.
        Fortress positions or forced lines may still return False even with no winning continuation.
        """

        own_pieces = {}
        opponent_pieces = {}

        own_knights = False
        own_bishops: dict[chessai.core.coordinate.Coordinate, chessai.core.piece.Piece] = {}

        for (file, rank_dict) in self.board.pieces.items():
            for (rank, piece) in rank_dict.items():
                coordinate = chessai.core.coordinate.Coordinate(file, rank)

                if (piece.color == color):
                    own_pieces[coordinate] = piece

                    # Pawns, rooks, or queens are always sufficient material.
                    if (isinstance(piece, (chessai.chess.piece.Pawn, chessai.chess.piece.Rook, chessai.chess.piece.Queen))):
                        return False

                    if (isinstance(piece, chessai.chess.piece.Knight)):
                        own_knights = True
                    elif (isinstance(piece, chessai.chess.piece.Bishop)):
                        own_bishops[coordinate] = piece
                else:
                    opponent_pieces[coordinate] = piece

        # Knights are only insufficient material if:
        # (1) We do not have any other pieces, including more than one knight.
        # (2) The opponent does not have pawns, knights, bishops or rooks.
        #     These would allow selfmate.
        if (own_knights):
            # Sufficient material via case 1.
            if (len(own_pieces) > 2):
                return False

            for piece in opponent_pieces.values():
                if isinstance(piece, (chessai.chess.piece.Knight, chessai.chess.piece.Bishop, chessai.chess.piece.Rook, chessai.chess.piece.Pawn)):
                    # Sufficient material via case 2.
                    return False

            return True

        # Bishops are only insufficient material if:
        # (1) We do not have any other pieces, including bishops of the opposite color.
        # (2) The opponent does not have bishops of the opposite color, pawns or knights.
        #     These would allow selfmate.
        if (len(own_bishops) > 0):
            square_parities = set()
            for (coordinate, _) in own_bishops.items():
                square_parity = (coordinate.file + coordinate.rank) % 2
                square_parities.add(square_parity)

            # Sufficient material via case 1.
            if (len(square_parities) > 1):
                return False

            for piece in opponent_pieces.values():
                # Sufficient material via case 2 (using pawns or knights).
                if (isinstance(piece, (chessai.chess.piece.Pawn, chessai.chess.piece.Knight))):
                    return False

            opponent_bishop_parities = set()
            for (coordinate, piece) in opponent_pieces.items():
                if (isinstance(piece, chessai.chess.piece.Bishop)):
                    opponent_parity = (coordinate.file + coordinate.rank) % 2
                    opponent_bishop_parities.add(opponent_parity)

            opponent_has_opposite_bishops = bool(opponent_bishop_parities - square_parities)

            # Determine sufficient material via case 2 when the opponent has bishops of the opposite color.
            return (not opponent_has_opposite_bishops)

        # King alone.
        return True

    def _handle_castling(self, action: chessai.core.action.MoveAction, piece: chessai.core.piece.Piece) -> None:
        # Build the rook action for castling.
        rook_action: chessai.core.action.Action | None = None
        back_rank = action.start_coordinate.rank

        if (action.end_coordinate.file > action.start_coordinate.file):
            # Kingside: rook moves from the h-file to just right of the king's destination.
            rook_start = chessai.core.coordinate.Coordinate(self.board.num_files - 1, back_rank)
            rook_end   = chessai.core.coordinate.Coordinate(action.end_coordinate.file - 1, back_rank)
        else:
            # Queenside: rook moves from the a-file to just left of the king's destination.
            rook_start = chessai.core.coordinate.Coordinate(0, back_rank)
            rook_end   = chessai.core.coordinate.Coordinate(action.end_coordinate.file + 1, back_rank)

        rook_action = chessai.core.action.MoveAction(rook_start, rook_end)

        # Move the rook for castling.
        self.board.push(rook_action)

    def _handle_en_passant(self,
                           action: chessai.core.action.MoveAction,
                           piece: chessai.core.piece.Piece,
                           ) -> chessai.core.coordinate.Coordinate | None:
        # The captured pawn is on the same rank as the moving pawn, on the destination file.
        captured_piece_coordinate = chessai.core.coordinate.Coordinate(
            action.end_coordinate.file,
            action.start_coordinate.rank,
        )

        # Remove the en-passant captured pawn from its actual coordinate.
        self.board.remove(captured_piece_coordinate)

        # Return the en-passant target coordinate, based on the action.
        return self._compute_en_passant(action, piece)

    def _handle_promotion(self, action: chessai.core.action.PromotionAction, piece: chessai.core.piece.Piece) -> None:
        # Handle promotion by replacing the pawn with the promoted piece.
        self.board.set(action.promotion, action.end_coordinate)

    def _get_castling_moves(self) -> list[chessai.core.action.MoveAction]:
        """ Get all pseudo-legal castling moves for the current player. """

        # Determine the back rank and castling rights for the current player.
        if (self.turn == chessai.core.types.Color.WHITE):
            back_rank           = 0
            kingside_rights     = self.castling_rights.white_kingside
            queenside_rights    = self.castling_rights.white_queenside
        else:
            back_rank           = self.board.num_ranks - 1
            kingside_rights     = self.castling_rights.black_kingside
            queenside_rights    = self.castling_rights.black_queenside

        if ((not kingside_rights) and (not queenside_rights)):
            return []

        # Find the king.
        king_coordinate = self.get_king_coordinate(self.turn)

        # The king must be on the back rank to castle.
        if ((king_coordinate is None) or (king_coordinate.rank != back_rank)):
            return []

        # Get the coordinates that the opponent can attack,
        # as a castling move cannot pass through a square that is attacked.
        attacked_coordinates = self.get_attacked_coordinates(self.turn.opposite())

        # The king cannot castle if it is being attacked.
        if (king_coordinate in attacked_coordinates):
            return []

        actions: list[chessai.core.action.MoveAction] = []

        # Add Kingside castling.
        if (kingside_rights):
            rook_cordinate = chessai.core.coordinate.Coordinate((self.board.num_files - 1), back_rank)
            rook_piece = self.get(rook_cordinate)

            # Check that the files to the right of the king and left of the rook are empty.
            all_safe = True
            file = king_coordinate.file + 1
            while (file < rook_cordinate.file):
                empty_coord = chessai.core.coordinate.Coordinate(file, back_rank)

                if (empty_coord in attacked_coordinates):
                    all_safe = False
                    break

                if (self.board.has_piece(empty_coord)):
                    all_safe = False
                    break

                file = file + 1

            if ((rook_piece is not None)
                    and (isinstance(rook_piece, chessai.chess.piece.Rook))
                    and (rook_piece.color == self.turn)
                    and (all_safe)):
                king_dest = chessai.core.coordinate.Coordinate((self.board.num_files - 2), back_rank)
                actions.append(chessai.core.action.MoveAction(king_coordinate, king_dest))

        # Add Queenside castling.
        if (queenside_rights):
            rook_cordinate = chessai.core.coordinate.Coordinate(0, back_rank)
            rook_piece = self.get(rook_cordinate)

            # Check that the files to the right of the king and left of the rook are empty.
            all_safe = True
            file = king_coordinate.file - 1
            while (file > 0):
                empty_coord = chessai.core.coordinate.Coordinate(file, back_rank)

                if (empty_coord in attacked_coordinates):
                    all_safe = False
                    break

                if (self.board.has_piece(empty_coord)):
                    all_safe = False
                    break

                file = file - 1

            if ((rook_piece is not None)
                    and (isinstance(rook_piece, chessai.chess.piece.Rook))
                    and (rook_piece.color == self.turn)
                    and (all_safe)):
                king_dest = chessai.core.coordinate.Coordinate(2, back_rank)
                actions.append(chessai.core.action.MoveAction(king_coordinate, king_dest))

        return actions

    def _get_pawn_double_pushes(self) -> list[chessai.core.action.MoveAction]:
        """ Get all pseudo-legal pawn double push moves for the current player. """

        if (self.turn == chessai.core.types.Color.WHITE):
            start_rank = 1
            direction  = 1
        else:
            start_rank = self.board.num_ranks - 2
            direction  = -1

        actions: list[chessai.core.action.MoveAction] = []

        for (file, rank_dict) in self.board.pieces.items():
            if (start_rank not in rank_dict):
                continue

            piece = rank_dict[start_rank]
            if (piece.color != self.turn):
                continue

            if (not isinstance(piece, chessai.chess.piece.Pawn)):
                continue

            coordinate = chessai.core.coordinate.Coordinate(file, start_rank)

            # Both the single and double push coordinates must be empty.
            single_push_coord = coordinate.offset(0, direction)
            if (self.board.has_piece(single_push_coord)):
                continue

            double_push_coord = coordinate.offset(0, direction * 2)
            if (self.board.has_piece(double_push_coord)):
                continue

            actions.append(chessai.core.action.MoveAction(coordinate, double_push_coord))

        return actions

    def _get_en_passant_captures(self) -> list[chessai.core.action.MoveAction]:
        """ Get all pseudo-legal en-passant captures for the current player. """

        actions: list[chessai.core.action.MoveAction] = []

        if (self.en_passant_coordinate is None):
            return actions

        if (self.turn == chessai.core.types.Color.WHITE):
            # The en-passant coordinate encodes the coordinate that must be taken.
            # So, the pawn that can attack it will be one rank below for white.
            capturing_rank = self.en_passant_coordinate.rank - 1
        else:
            capturing_rank = self.en_passant_coordinate.rank + 1

        # The pawn will have to be on an adjacent file.
        for file_delta in [-1, 1]:
            candidate_capture_coord = chessai.core.coordinate.Coordinate(
                self.en_passant_coordinate.file + file_delta,
                capturing_rank,
            )

            if (not self.board.is_within_bounds(candidate_capture_coord.file, candidate_capture_coord.rank)):
                continue

            piece = self.get(candidate_capture_coord)
            if (piece is None):
                continue

            if (not isinstance(piece, chessai.chess.piece.Pawn)):
                continue

            if (piece.color != self.turn):
                continue

            actions.append(chessai.core.action.MoveAction(candidate_capture_coord, self.en_passant_coordinate))

        return actions

    def _get_promotion_actions(self,
            start_coordinate: chessai.core.coordinate.Coordinate,
            end_coordinate: chessai.core.coordinate.Coordinate) -> list[chessai.core.action.MoveAction]:
        """
        Expand a pawn move that reaches the back rank into one action per promotable piece type.

        Called when a pawn reaches the back rank of the opposing side.
        Always returns exactly four actions (queen, rook, bishop, knight).
        """

        return [
            chessai.core.action.PromotionAction(start_coordinate, end_coordinate, chessai.chess.piece.Queen(self.turn)),
            chessai.core.action.PromotionAction(start_coordinate, end_coordinate, chessai.chess.piece.Rook(self.turn)),
            chessai.core.action.PromotionAction(start_coordinate, end_coordinate, chessai.chess.piece.Bishop(self.turn)),
            chessai.core.action.PromotionAction(start_coordinate, end_coordinate, chessai.chess.piece.Knight(self.turn)),
        ]

    def _update_castling_rights(self,
            action: chessai.core.action.MoveAction,
            piece: chessai.core.piece.Piece) -> None:
        """ Revoke castling rights that are no longer valid after the given move. """

        white_kingside_rook  = chessai.core.coordinate.Coordinate(self.board.num_files - 1, 0)
        white_queenside_rook = chessai.core.coordinate.Coordinate(0, 0)
        black_kingside_rook  = chessai.core.coordinate.Coordinate(self.board.num_files - 1, self.board.num_ranks - 1)
        black_queenside_rook = chessai.core.coordinate.Coordinate(0, self.board.num_ranks - 1)

        # King moves, which forfeits both rights for that color.
        if (isinstance(piece, chessai.chess.piece.King)):
            if (piece.color == chessai.core.types.Color.WHITE):
                self.castling_rights = self.castling_rights.revoke_rights(chessai.core.castling.ALL_WHITE_RIGHTS)
            else:
                self.castling_rights = self.castling_rights.revoke_rights(chessai.core.castling.ALL_BLACK_RIGHTS)

        # Rook moves from its starting coordinate.
        if (action.start_coordinate == white_kingside_rook):
            self.castling_rights = self.castling_rights.revoke_rights(chessai.core.castling.WHITE_KINGSIDE_RIGHTS)

        if (action.start_coordinate == white_queenside_rook):
            self.castling_rights = self.castling_rights.revoke_rights(chessai.core.castling.WHITE_QUEENSIDE_RIGHTS)

        if (action.start_coordinate == black_kingside_rook):
            self.castling_rights = self.castling_rights.revoke_rights(chessai.core.castling.BLACK_KINGSIDE_RIGHTS)

        if (action.start_coordinate == black_queenside_rook):
            self.castling_rights = self.castling_rights.revoke_rights(chessai.core.castling.BLACK_QUEENSIDE_RIGHTS)

        # Rook captured on its starting coordinate.
        if (action.end_coordinate == white_kingside_rook):
            self.castling_rights = self.castling_rights.revoke_rights(chessai.core.castling.WHITE_KINGSIDE_RIGHTS)

        if (action.end_coordinate == white_queenside_rook):
            self.castling_rights = self.castling_rights.revoke_rights(chessai.core.castling.WHITE_QUEENSIDE_RIGHTS)

        if (action.end_coordinate == black_kingside_rook):
            self.castling_rights = self.castling_rights.revoke_rights(chessai.core.castling.BLACK_KINGSIDE_RIGHTS)

        if (action.end_coordinate == black_queenside_rook):
            self.castling_rights = self.castling_rights.revoke_rights(chessai.core.castling.BLACK_QUEENSIDE_RIGHTS)

    def _compute_en_passant(self,
            action: chessai.core.action.MoveAction,
            piece: chessai.core.piece.Piece) -> chessai.core.coordinate.Coordinate | None:
        """
        Return the new en-passant target coordinate after this move, or None.

        A target coordinate is set only when a pawn advances two ranks.
        The target is the coordinate the pawn passed through (i.e. one rank behind the destination), which is standard FEN notation.
        """

        if (not isinstance(piece, chessai.chess.piece.Pawn)):
            return None

        if (action.start_coordinate.rank_distance(action.end_coordinate) != 2):
            return None

        # The en-passant target is the coordinate the pawn skipped over.
        passed_rank = (action.start_coordinate.rank + action.end_coordinate.rank) // 2
        return chessai.core.coordinate.Coordinate(action.start_coordinate.file, passed_rank)

    def copy(self,
            context: typing.Union[edq.util.serial.SerializationContext, None] = None,
            ) -> 'GameState':
        new_state = super().copy()
        new_state = typing.cast(GameState, new_state)

        return new_state

def base_eval(
        state: chessai.core.gamestate.GameState,
        action: chessai.core.action.Action | None = None,
        agent: typing.Any | None = None,
        **kwargs: typing.Any) -> float:
    """
    The most basic evaluation function, which just uses the difference in piece value on the board.

    Scores are from the requesting agent's perspective.
    Positive values favor that agent and negative values favor its opponent.
    When no agent is supplied, scores are from the side-to-move's perspective.
    """

    piece_values: dict[type[chessai.core.piece.Piece], int] = {
        chessai.chess.piece.Pawn: 1,
        chessai.chess.piece.Knight: 3,
        chessai.chess.piece.Bishop: 3,
        chessai.chess.piece.Rook: 5,
        chessai.chess.piece.Queen: 9,
        chessai.chess.piece.King: 9999,
    }

    # The difference in pieces from White's perspective.
    board_value = 0
    for piece in state.board.all_pieces():
        piece_value = piece_values.get(type(piece), 0)
        if (piece.color == chessai.core.types.Color.WHITE):
            board_value += piece_value
        else:
            board_value -= piece_value

    player = state.turn
    if isinstance(agent, chessai.core.agent.Agent) and (agent.player is not None):
        player = agent.player

    if (player == chessai.core.types.Color.WHITE):
        return board_value

    # Black's perspective is the inverse of White's.
    return -1 * board_value
