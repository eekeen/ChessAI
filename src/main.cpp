#include "game/GameController.h"

#include <cctype>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

// ============================================================
// STRING -> SQUARE
// ============================================================

int squareFromString(const std::string& square)
{
    if (square.length() != 2)
    {
        return -1;
    }

    const char file = square[0];
    const char rank = square[1];

    if (
        file < 'a' || file > 'h' ||
        rank < '1' || rank > '8'
    )
    {
        return -1;
    }

    return
        (rank - '1') * 8 +
        (file - 'a');
}


// ============================================================
// SQUARE -> STRING
// ============================================================

std::string squareToString(int square)
{
    if (!isValidSquare(square))
    {
        return "-";
    }

    std::string result;

    result += static_cast<char>(
        'a' + fileOf(square)
    );

    result += static_cast<char>(
        '1' + rankOf(square)
    );

    return result;
}


// ============================================================
// PROMOTION CHARACTER
// ============================================================

PieceType promotionPieceFromChar(char c)
{
    switch (c)
    {
        case 'q':
        case 'Q':
            return PieceType::Queen;

        case 'r':
        case 'R':
            return PieceType::Rook;

        case 'b':
        case 'B':
            return PieceType::Bishop;

        case 'n':
        case 'N':
            return PieceType::Knight;

        default:
            return PieceType::None;
    }
}


// ============================================================
// PIECE -> CHARACTER
// ============================================================

char pieceToChar(const Piece& piece)
{
    if (piece.isEmpty())
    {
        return '.';
    }

    char c = '.';

    switch (piece.type)
    {
        case PieceType::Pawn:
            c = 'p';
            break;

        case PieceType::Knight:
            c = 'n';
            break;

        case PieceType::Bishop:
            c = 'b';
            break;

        case PieceType::Rook:
            c = 'r';
            break;

        case PieceType::Queen:
            c = 'q';
            break;

        case PieceType::King:
            c = 'k';
            break;

        case PieceType::None:
        default:
            return '.';
    }

    if (piece.color == Color::White)
    {
        c = static_cast<char>(
            std::toupper(
                static_cast<unsigned char>(c)
            )
        );
    }

    return c;
}


// ============================================================
// BOARD -> 64 CHARACTER STRING
//
// a8 -> h8
// ...
// a1 -> h1
// ============================================================

std::string boardToString(const Board& board)
{
    std::string result;

    result.reserve(64);

    for (int rank = 7; rank >= 0; --rank)
    {
        for (int file = 0; file < 8; ++file)
        {
            const int square =
                rank * 8 + file;

            result +=
                pieceToChar(
                    board.getPiece(square)
                );
        }
    }

    return result;
}


// ============================================================
// GAME STATE -> STRING
// ============================================================

std::string gameStateToString(GameState state)
{
    switch (state)
    {
        case GameState::WhiteCheckmate:
            return "white_wins";

        case GameState::BlackCheckmate:
            return "black_wins";

        case GameState::Stalemate:
            return "stalemate";

        case GameState::DrawFiftyMove:
            return "draw_fifty_move";

        case GameState::DrawRepetition:
            return "draw_repetition";

        case GameState::DrawInsufficientMaterial:
            return "draw_insufficient_material";

        case GameState::Ongoing:
        default:
            return "ongoing";
    }
}


// ============================================================
// FIND KING
// ============================================================

int findKingSquare(
    const Board& board,
    Color color
)
{
    for (int square = 0; square < 64; ++square)
    {
        const Piece piece =
            board.getPiece(square);

        if (
            piece.type == PieceType::King &&
            piece.color == color
        )
        {
            return square;
        }
    }

    return -1;
}


// ============================================================
// FIND LEGAL MOVE
// ============================================================

bool findLegalMove(
    const Game& game,
    int fromSquare,
    int toSquare,
    PieceType promotionPiece,
    Move& result
)
{
    const std::vector<Move> legalMoves =
        game.getLegalMoves();

    for (const Move& move : legalMoves)
    {
        if (
            move.getFrom() != fromSquare ||
            move.getTo() != toSquare
        )
        {
            continue;
        }

        if (
            move.getFlag() ==
            MoveFlag::Promotion
        )
        {
            if (
                move.getPromotionPiece() !=
                promotionPiece
            )
            {
                continue;
            }
        }

        result = move;

        return true;
    }

    return false;
}


// ============================================================
// CAPTURE?
// ============================================================

bool isCaptureMove(
    const Board& board,
    const Move& move
)
{
    if (
        move.getFlag() == MoveFlag::Capture ||
        move.getFlag() == MoveFlag::EnPassant
    )
    {
        return true;
    }

    return !board
        .getPiece(
            move.getTo()
        )
        .isEmpty();
}


// ============================================================
// MAIN ENGINE PROTOCOL
// ============================================================

int main()
{
    GameController controller;

    std::string command;

    std::cout
        << "ready"
        << std::endl;


    while (
        std::getline(
            std::cin,
            command
        )
    )
    {
        std::istringstream input(
            command
        );

        std::string operation;

        input >> operation;

        if (operation == "evalmode")
        {
            std::string name, extra;
            if (!(input >> name))
                std::cout << "evalmode " << PositionEvaluator::modeName(controller.getEvaluationMode()) << std::endl;
            else if ((input >> extra) || (name != "classic" && name != "ml" && name != "hybrid"))
                std::cout << "error invalid_evalmode" << std::endl;
            else
            {
                const auto mode = name == "classic" ? EvaluationMode::Classic :
                    name == "ml" ? EvaluationMode::ML : EvaluationMode::Hybrid;
                std::cout << (controller.setEvaluationMode(mode) ? "ok" : "error model_unavailable") << std::endl;
            }
            continue;
        }
        if (operation == "hybridalpha") {
            std::cout << "hybridalpha " << controller.getHybridAlpha() << std::endl;
            continue;
        }
        if (operation == "evaluate")
        {
            const Board& board = controller.getGame().getBoard();
            PositionEvaluator evaluator;
            std::cout << "evaluation classic " << evaluator.evaluate(board, EvaluationMode::Classic);
            for (auto mode : {EvaluationMode::ML, EvaluationMode::Hybrid}) {
                std::cout << " " << PositionEvaluator::modeName(mode) << " ";
                if (PositionEvaluator::available(mode)) std::cout << evaluator.evaluate(board, mode);
                else std::cout << "unavailable";
            }
            std::cout << std::endl;
            continue;
        }
        if (operation == "model")
        {
            std::cout << "model " << PositionEvaluator::modelVersion() << std::endl;
            continue;
        }
        if (operation == "evalmodes") {
            std::cout << "evalmodes classic";
            for (auto mode : {EvaluationMode::ML, EvaluationMode::Hybrid})
                if (PositionEvaluator::available(mode)) std::cout << " " << PositionEvaluator::modeName(mode);
            std::cout << std::endl;
            continue;
        }


        // ====================================================
        // QUIT
        // ====================================================

        if (operation == "quit")
        {
            std::cout
                << "bye"
                << std::endl;

            break;
        }


        // ====================================================
        // PING
        // ====================================================

        if (operation == "ping")
        {
            std::cout
                << "pong"
                << std::endl;

            continue;
        }


        // ====================================================
        // NEW GAME
        // ====================================================

        if (operation == "newgame")
        {
            controller.newGame();

            std::cout
                << "ok"
                << std::endl;

            continue;
        }


        // ====================================================
        // POSITION
        // ====================================================

        if (operation == "position")
        {
            std::cout
                << "position "
                << boardToString(
                    controller
                        .getGame()
                        .getBoard()
                )
                << std::endl;

            continue;
        }


        // ====================================================
        // TURN
        // ====================================================

        if (operation == "turn")
        {
            const Color side =
                controller
                    .getGame()
                    .getSideToMove();

            std::cout
                << "turn "
                << (
                    side == Color::White
                        ? "white"
                        : "black"
                )
                << std::endl;

            continue;
        }


        // ====================================================
        // STATE
        // ====================================================

        if (operation == "state")
        {
            std::cout
                << "state "
                << gameStateToString(
                    controller
                        .getGame()
                        .getGameState()
                )
                << std::endl;

            continue;
        }


        // ====================================================
        // CHECK
        //
        // check
        //
        // ->
        //
        // check 0 -
        //
        // or
        //
        // check 1 e1
        // ====================================================

        if (operation == "check")
        {
            const Game& game =
                controller.getGame();

            const bool inCheck =
                game.isInCheck();

            if (!inCheck)
            {
                std::cout
                    << "check 0 -"
                    << std::endl;

                continue;
            }

            const int kingSquare =
                findKingSquare(
                    game.getBoard(),
                    game.getSideToMove()
                );

            std::cout
                << "check 1 "
                << squareToString(
                    kingSquare
                )
                << std::endl;

            continue;
        }


        // ====================================================
        // LEGAL MOVES
        //
        // legal e2
        //
        // ->
        //
        // legal e2e3 e2e4
        // ====================================================

        if (operation == "legal")
        {
            std::string squareString;

            input >> squareString;

            const int square =
                squareFromString(
                    squareString
                );

            std::cout
                << "legal";

            if (isValidSquare(square))
            {
                const std::vector<Move> moves =
                    controller
                        .getGame()
                        .getLegalMoves();

                for (const Move& move : moves)
                {
                    if (
                        move.getFrom() ==
                        square
                    )
                    {
                        std::cout
                            << " "
                            << move.toString();
                    }
                }
            }

            std::cout
                << std::endl;

            continue;
        }


        // ====================================================
        // PLAYER MOVE
        //
        // move e2e4
        //
        // move e7e8q
        // ====================================================

        if (operation == "move")
        {
            std::string moveString;

            input >> moveString;


            if (
                moveString.length() != 4 &&
                moveString.length() != 5
            )
            {
                std::cout
                    << "illegal"
                    << std::endl;

                continue;
            }


            const int fromSquare =
                squareFromString(
                    moveString.substr(
                        0,
                        2
                    )
                );


            const int toSquare =
                squareFromString(
                    moveString.substr(
                        2,
                        2
                    )
                );


            if (
                !isValidSquare(fromSquare) ||
                !isValidSquare(toSquare)
            )
            {
                std::cout
                    << "illegal"
                    << std::endl;

                continue;
            }


            PieceType promotionPiece =
                PieceType::Queen;


            if (moveString.length() == 5)
            {
                promotionPiece =
                    promotionPieceFromChar(
                        moveString[4]
                    );


                if (
                    promotionPiece ==
                    PieceType::None
                )
                {
                    std::cout
                        << "illegal"
                        << std::endl;

                    continue;
                }
            }


            Move legalMove;


            if (
                !findLegalMove(
                    controller.getGame(),
                    fromSquare,
                    toSquare,
                    promotionPiece,
                    legalMove
                )
            )
            {
                std::cout
                    << "illegal"
                    << std::endl;

                continue;
            }


            const bool capture =
                isCaptureMove(
                    controller
                        .getGame()
                        .getBoard(),

                    legalMove
                );


            const bool success =
                controller.makePlayerMove(
                    fromSquare,
                    toSquare,
                    promotionPiece
                );


            if (!success)
            {
                std::cout
                    << "illegal"
                    << std::endl;

                continue;
            }


            std::cout
                << "ok capture "
                << (
                    capture
                        ? 1
                        : 0
                )
                << std::endl;

            continue;
        }


        // ====================================================
        // ENGINE MOVE
        //
        // go <time> <max depth> <target elo>
        //
        // Example:
        //
        // go 200 3 1000
        // ====================================================

        if (operation == "go")
        {
            int thinkingTimeMs = 1000;
            int maxDepth = 64;
            int targetElo = 2000;


            input >>
                thinkingTimeMs;


            if (!(input >> maxDepth))
            {
                maxDepth = 64;

                input.clear();
            }


            if (!(input >> targetElo))
            {
                targetElo = 2000;

                input.clear();
            }


            if (thinkingTimeMs < 1)
            {
                thinkingTimeMs = 1;
            }


            if (maxDepth < 1)
            {
                maxDepth = 1;
            }


            if (targetElo < 100)
            {
                targetElo = 100;
            }


            const EngineMoveResult result =
                controller.makeEngineMove(
                    thinkingTimeMs,
                    maxDepth,
                    targetElo
                );


            if (!result.moveMade)
            {
                std::cout
                    << "nomove"
                    << std::endl;

                continue;
            }


            std::cout
                << "bestmove "
                << result.move.toString()

                << " score "
                << result.score

                << " depth "
                << result.depth

                << " nodes "
                << result.nodes

                << " tthits "
                << result.ttHits

                << " time "
                << result.timeMs

                << " capture "
                << (
                    result.wasCapture
                        ? 1
                        : 0
                )

                << " book "
                << (
                    result.fromBook
                        ? 1
                        : 0
                )

                << std::endl;

            continue;
        }


        // ====================================================
        // UNKNOWN COMMAND
        // ====================================================

        std::cout
            << "error unknown_command"
            << std::endl;
    }


    return 0;
}
