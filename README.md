# Chessai

An AI educational project disguised as [Chess](https://en.wikipedia.org/wiki/Chess)!

## Documentation

API documentation for all releases is available at [ucsc-cse-240.github.io/chessai](https://ucsc-cse-240.github.io/chessai).

## Installation / Requirements

This project requires [Python](https://www.python.org/) >= 3.10.

Standard Python requirements are listed in `pyproject.toml`.
The project and Python dependencies can be installed from source with:
```sh
pip3 install .
```

## Using Chessai

Once installed, you can play a game of Chess with:
```sh
python3 -m chessai.chess
```

To see all the available options, use the `--help` flag:
```sh
python3 -m chessai.chess --help
```

### Boards

You can change the board that you are playing on with the `--board` option.
Any [chess FEN](https://en.wikipedia.org/wiki/Forsyth%E2%80%93Edwards_Notation) can be used to set the board.

Chessai comes with several different boards in the [chessai/resources/boards directory](chessai/resources/boards).
For example:
```sh
python3 -m chessai.chess --board "rnbqkbnr/pp1ppppp/8/2p5/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq - 1 2"
```

You can also specify a path to a board file if you want to use a custom board:
```sh
python3 -m chessai.chess --board chessai/resources/boards/standard.board
```

### Puzzles

Puzzles test a single agent's ability to find one of the best moves available, given the current board position.

You can play a puzzle game with:
```sh
python3 -m chessai.puzzle
```

The default agent chooses a random legal move, so they will rarely solve puzzles.

By default, the puzzle is a mate-in-1, but there are more puzzles available in the [chessai/resources/boards directory](chessai/resources/boards).
All puzzle boards are prefixed with `puzzle-`, to differentiate from standard chess boards.

For example, you can specify a mate-in-3 puzzle with:
```sh
python3 -m chessai.puzzle --board chessai/resources/puzzles/puzzle-mate-3.json
```

You can also specify the possible "move lines" (the potential solutions to the puzzle) directly with the `--move-lines` option.
Move lines must be specified as list of move lines, where each move line consists of the steps to solve the puzzle, using UCI notation:
```sh
python3 -m chessai.puzzle --move-lines "[[\"c6d5\"]]"
```

This provides the move that finds the mate in 1!

#### Adding Known Puzzles

Chessai accepts any puzzle, as long as you provide the starting position, in the form of a FEN, and the move lines that solve the puzzle.
Note that puzzles do not have to end in a mate, they will end once the agent finishes one of the solution move lines.

A great place to find puzzles is through [Lichess' Puzzles](https://lichess.org/training/themes),
which are sorted by theme.
You can also download a large number of puzzles from [Lichess' download link](https://database.lichess.org/#puzzles).

#### Creating a Custom Puzzle

One of the easiest ways to create a new puzzle is to use the [Lichess board editor](https://lichess.org/editor).

There, you can adjust the board manually to create a unique puzzle!
After you finish adjusting the board, copy the FEN that is provided at the bottom of the screen.

Lichess's board editor allows you to analyze the board position with their built-in chess engine.
Once you find the recommended moves, which should be clearly better than the alternative moves,
write the moves down in the puzzle's move line.

Once you are done, run the following command with your starting FEN and the moves to solve the puzzle:
```sh
python3 -m chessai.puzzle --board <puzzle FEN> --move-lines <possible solution moves>
```

#### Evaluating an Agent Using Puzzles

A great baseline way to test your agent is to have it try to solve chess puzzles.
Each puzzle tries to teach a specific skill that your agent should be able to solve.

To test your agent against many puzzles, run the following script:
TODO: Add puzzle documentation and explain how to have an agent play a suite of puzzles.

### Choosing an Agent

In Chess, you can choose which agent you use with the `--white-team` and `--black-team` options.
The `--help` flag will list all the agent's available by default.
Agents may be specialized and not work on every board.

For example, you can use a random agent with:
```sh
python3 -m chessai.chess --white-team agent-random --black-team agent-random
```

You can also use `--white-team` and `--black-team` to point to any importable module or file/class.
```sh
# Use an importable module name.
python3 -m chessai.chess --white-team chessai.agents.random.RandomAgent

# Point to an agent class inside of a file.
python3 -m chessai.chess --black-team chessai/agents/random.py:RandomAgent
```

#### Agent Arguments

Many agents will accept arguments that can be used to tweak that agent's behavior.
These arguments can be passed using the `--agent-arg` options
(which can be specified as many times as you wish).
The argument to `--agent-arg` is formatted as: `<agent color>::<option name>=<option value>`.

Note that the agent now finds the optimal path much faster.

## For Students

Students who are working on this project as part of a class should note a few things:
 1. Never share your solutions or implemented code.
    In many courses, this would be considered cheating.
 2. Make sure that your version of this repo is private.
    Having a public repo may be indirectly sharing code.
    You can follow GitHub's directions on
    [creating a repo from a template](https://docs.github.com/en/repositories/creating-and-managing-repositories/creating-a-repository-from-a-template).
    Pay close attention to make the repository private.
 3. All or most of the code you will implement will be in the [chessai/student directory](chessai/student).

## Acknowledgements

This project has been built up from the work of many people.
Here are just a few that we know about:
 - TODO(List Acknowledgements)
 - TAs, grader, and graduates of UCSC's CMPS/CSE 240 class who have helped pave the way for future classes
   (their identities are immortalized in the git history).

## Licensing

See [LICENSE](LICENSE).

The majority of this project is licensed under an [MIT license](LICENSE-code).
Non-code portions of the code (e.g., images) under the [chessai/resources directory](/chessai/resources)
are license under a [CC BY-SA 4.0 license](LICENSE-noncode).

Additionally, solutions (implementations (full or partial) of the code in the [chessai/student directory](/chessai/student))
should never be published or distributed.

[This notice](LICENSE) should always be retained.
