#include "Evaluation.h"

#include <array>

// ============================================================
// PIECE-SQUARE TABLES
//
// Tables are written from White's perspective.
//
// a1 = index 0
// h8 = index 63
//
// Values are centipawns.
// ============================================================

static constexpr std::array<int, 64> PAWN_TABLE =
{
     0,  0,  0,  0,  0,  0,  0,  0,
     5, 10, 10,-20,-20, 10, 10,  5,
     5, -5,-10,  0,  0,-10, -5,  5,
     0,  0,  0, 20, 20,  0,  0,  0,
     5,  5, 10, 25, 25, 10,  5,  5,
    10, 10, 20, 30, 30, 20, 10, 10,
    50, 50, 50, 50, 50, 50, 50, 50,
     0,  0,  0,  0,  0,  0,  0,  0
};

static constexpr std::array<int, 64> KNIGHT_TABLE =
{
    -50,-40,-30,-30,-30,-30,-40,-50,
    -40,-20,  0,  5,  5,  0,-20,-40,
    -30,  5, 10, 15, 15, 10,  5,-30,
    -30,  0, 15, 20, 20, 15,  0,-30,
    -30,  5, 15, 20, 20, 15,  5,-30,
    -30,  0, 10, 15, 15, 10,  0,-30,
    -40,-20,  0,  0,  0,  0,-20,-40,
    -50,-40,-30,-30,-30,-30,-40,-50
};

static constexpr std::array<int, 64> BISHOP_TABLE =
{
    -20,-10,-10,-10,-10,-10,-10,-20,
    -10,  5,  0,  0,  0,  0,  5,-10,
    -10, 10, 10, 10, 10, 10, 10,-10,
    -10,  0, 10, 10, 10, 10,  0,-10,
    -10,  5,  5, 10, 10,  5,  5,-10,
    -10,  0,  5, 10, 10,  5,  0,-10,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -20,-10,-10,-10,-10,-10,-10,-20
};

static constexpr std::array<int, 64> ROOK_TABLE =
{
     0,  0,  0,  5,  5,  0,  0,  0,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
    -5,  0,  0,  0,  0,  0,  0, -5,
     5, 10, 10, 10, 10, 10, 10,  5,
     0,  0,  0,  0,  0,  0,  0,  0
};

static constexpr std::array<int, 64> QUEEN_TABLE =
{
    -20,-10,-10, -5, -5,-10,-10,-20,
    -10,  0,  5,  0,  0,  0,  0,-10,
    -10,  5,  5,  5,  5,  5,  0,-10,
      0,  0,  5,  5,  5,  5,  0, -5,
     -5,  0,  5,  5,  5,  5,  0, -5,
    -10,  0,  5,  5,  5,  5,  0,-10,
    -10,  0,  0,  0,  0,  0,  0,-10,
    -20,-10,-10, -5, -5,-10,-10,-20
};

static constexpr std::array<int, 64> KING_TABLE =
{
     20, 30, 10,  0,  0, 10, 30, 20,
     20, 20,  0,  0,  0,  0, 20, 20,
    -10,-20,-20,-20,-20,-20,-20,-10,
    -20,-30,-30,-40,-40,-30,-30,-20,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30,
    -30,-40,-40,-50,-50,-40,-40,-30
};


// ============================================================
// MATERIAL VALUES
// ============================================================

int Evaluation::getPieceValue(PieceType pieceType) const
{
    switch (pieceType)
    {
        case PieceType::Pawn:
            return 100;

        case PieceType::Knight:
            return 320;

        case PieceType::Bishop:
            return 330;

        case PieceType::Rook:
            return 500;

        case PieceType::Queen:
            return 900;

        case PieceType::King:
            return 0;

        case PieceType::None:
        default:
            return 0;
    }
}


// ============================================================
// POSITIONAL VALUE
// ============================================================

int Evaluation::getPieceSquareValue(
    PieceType pieceType,
    Color color,
    int square
) const
{
    // Tables are defined from White's perspective.
    //
    // For Black we mirror the board vertically.
    const int tableSquare =
        (color == Color::White)
            ? square
            : square ^ 56;

    switch (pieceType)
    {
        case PieceType::Pawn:
            return PAWN_TABLE[tableSquare];

        case PieceType::Knight:
            return KNIGHT_TABLE[tableSquare];

        case PieceType::Bishop:
            return BISHOP_TABLE[tableSquare];

        case PieceType::Rook:
            return ROOK_TABLE[tableSquare];

        case PieceType::Queen:
            return QUEEN_TABLE[tableSquare];

        case PieceType::King:
            return KING_TABLE[tableSquare];

        case PieceType::None:
        default:
            return 0;
    }
}


// ============================================================
// FULL EVALUATION
// ============================================================

int Evaluation::evaluate(const Board& board) const
{
    int score = 0;

    for (int square = 0; square < 64; ++square)
    {
        const Piece piece =
            board.getPiece(square);

        if (piece.isEmpty())
        {
            continue;
        }

        const int materialValue =
            getPieceValue(piece.type);

        const int positionalValue =
            getPieceSquareValue(
                piece.type,
                piece.color,
                square
            );

        const int totalValue =
            materialValue + positionalValue;

        if (piece.color == Color::White)
        {
            score += totalValue;
        }
        else
        {
            score -= totalValue;
        }
    }

    return score;
}