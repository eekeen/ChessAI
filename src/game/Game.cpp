#include "Game.h"

#include "../engine/Zobrist.h"

// ============================================================
// CONSTRUCTOR
// ============================================================

Game::Game()
{
    reset();
}


// ============================================================
// RESET GAME
// ============================================================

void Game::reset()
{
    board.reset();

    moveHistory.clear();
    positionHistory.clear();

    // Starting position counts as the first occurrence.
    recordPosition();
}


// ============================================================
// BOARD ACCESS
// ============================================================

const Board& Game::getBoard() const
{
    return board;
}


// ============================================================
// SIDE TO MOVE
// ============================================================

Color Game::getSideToMove() const
{
    return board.getSideToMove();
}


// ============================================================
// LEGAL MOVES
// ============================================================

std::vector<Move> Game::getLegalMoves() const
{
    return moveGenerator.generateLegalMoves(board);
}


// ============================================================
// MOVE HISTORY
// ============================================================

const std::vector<Move>& Game::getMoveHistory() const
{
    return moveHistory;
}


// ============================================================
// TRY MOVE USING SQUARES
// ============================================================

bool Game::tryMove(
    int fromSquare,
    int toSquare,
    PieceType promotionPiece
)
{
    const std::vector<Move> legalMoves =
        moveGenerator.generateLegalMoves(board);

    for (const Move& move : legalMoves)
    {
        if (
            movesMatch(
                move,
                fromSquare,
                toSquare,
                promotionPiece
            )
        )
        {
            board.makeMove(move);

            moveHistory.push_back(move);

            recordPosition();

            return true;
        }
    }

    return false;
}


// ============================================================
// TRY MOVE OBJECT
// ============================================================

bool Game::tryMove(const Move& requestedMove)
{
    const std::vector<Move> legalMoves =
        moveGenerator.generateLegalMoves(board);

    for (const Move& legalMove : legalMoves)
    {
        if (
            legalMove.getFrom() ==
                requestedMove.getFrom() &&

            legalMove.getTo() ==
                requestedMove.getTo() &&

            legalMove.getFlag() ==
                requestedMove.getFlag() &&

            legalMove.getPromotionPiece() ==
                requestedMove.getPromotionPiece()
        )
        {
            board.makeMove(legalMove);

            moveHistory.push_back(legalMove);

            recordPosition();

            return true;
        }
    }

    return false;
}


// ============================================================
// GAME STATE
// ============================================================

GameState Game::getGameState() const
{
    const std::vector<Move> legalMoves =
        moveGenerator.generateLegalMoves(board);

    // ========================================================
    // CHECKMATE / STALEMATE
    //
    // These are checked first because a checkmate ends the
    // game immediately.
    // ========================================================

    if (legalMoves.empty())
    {
        const Color side =
            board.getSideToMove();

        if (
            moveGenerator.isInCheck(
                board,
                side
            )
        )
        {
            if (side == Color::White)
            {
                return GameState::BlackCheckmate;
            }

            return GameState::WhiteCheckmate;
        }

        return GameState::Stalemate;
    }


    // ========================================================
    // INSUFFICIENT MATERIAL
    // ========================================================

    if (isInsufficientMaterial())
    {
        return GameState::DrawInsufficientMaterial;
    }


    // ========================================================
    // FIFTY-MOVE RULE
    //
    // 100 half-moves = 50 moves by each side combined.
    // ========================================================

    if (isFiftyMoveDraw())
    {
        return GameState::DrawFiftyMove;
    }


    // ========================================================
    // THREEFOLD REPETITION
    // ========================================================

    if (isThreefoldRepetition())
    {
        return GameState::DrawRepetition;
    }


    return GameState::Ongoing;
}


// ============================================================
// CURRENT SIDE IN CHECK
// ============================================================

bool Game::isInCheck() const
{
    return moveGenerator.isInCheck(
        board,
        board.getSideToMove()
    );
}


// ============================================================
// THREEFOLD REPETITION
// ============================================================

bool Game::isThreefoldRepetition() const
{
    if (positionHistory.empty())
    {
        return false;
    }

    const uint64_t currentPosition =
        positionHistory.back();

    int occurrences = 0;

    for (const uint64_t position : positionHistory)
    {
        if (position == currentPosition)
        {
            ++occurrences;

            if (occurrences >= 3)
            {
                return true;
            }
        }
    }

    return false;
}


// ============================================================
// FIFTY-MOVE RULE
// ============================================================

bool Game::isFiftyMoveDraw() const
{
    return board.getHalfmoveClock() >= 100;
}


// ============================================================
// INSUFFICIENT MATERIAL
//
// Automatic draw for positions such as:
//
// K vs K
// K+B vs K
// K+N vs K
// K+B vs K+B when all bishops are on the same square colour
// ============================================================

bool Game::isInsufficientMaterial() const
{
    int knightCount = 0;
    int bishopCount = 0;

    bool bishopSquareColorSet = false;
    int bishopSquareColor = 0;

    bool allBishopsSameColor = true;


    for (int square = 0; square < 64; ++square)
    {
        const Piece piece =
            board.getPiece(square);

        if (piece.isEmpty())
        {
            continue;
        }


        switch (piece.type)
        {
            // Pawns, rooks and queens mean mating material
            // definitely remains.
            case PieceType::Pawn:
            case PieceType::Rook:
            case PieceType::Queen:
                return false;


            case PieceType::Knight:
                ++knightCount;
                break;


            case PieceType::Bishop:
            {
                ++bishopCount;

                const int squareColor =
                    (fileOf(square) + rankOf(square)) % 2;

                if (!bishopSquareColorSet)
                {
                    bishopSquareColor =
                        squareColor;

                    bishopSquareColorSet =
                        true;
                }
                else if (
                    squareColor !=
                    bishopSquareColor
                )
                {
                    allBishopsSameColor =
                        false;
                }

                break;
            }


            case PieceType::King:
            case PieceType::None:
            default:
                break;
        }
    }


    const int minorPieceCount =
        knightCount + bishopCount;


    // K vs K
    if (minorPieceCount == 0)
    {
        return true;
    }


    // K+B vs K
    // K+N vs K
    if (minorPieceCount == 1)
    {
        return true;
    }


    // Only bishops remain and every bishop is restricted
    // to the same colour complex.
    if (
        knightCount == 0 &&
        bishopCount > 0 &&
        allBishopsSameColor
    )
    {
        return true;
    }


    return false;
}


// ============================================================
// MOVE MATCHING
// ============================================================

bool Game::movesMatch(
    const Move& legalMove,
    int fromSquare,
    int toSquare,
    PieceType promotionPiece
) const
{
    if (
        legalMove.getFrom() != fromSquare ||
        legalMove.getTo() != toSquare
    )
    {
        return false;
    }


    // Promotion moves must also match the selected piece.
    if (
        legalMove.getFlag() ==
        MoveFlag::Promotion
    )
    {
        return
            legalMove.getPromotionPiece() ==
            promotionPiece;
    }


    return true;
}


// ============================================================
// RECORD POSITION
// ============================================================

void Game::recordPosition()
{
    positionHistory.push_back(
        Zobrist::hash(board)
    );
}