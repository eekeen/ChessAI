#pragma once

#include "../chess/Board.h"
#include "../chess/Types.h"

class Evaluation
{
public:
    // Positive = White advantage
    // Negative = Black advantage
    int evaluate(const Board& board) const;

private:
    int getPieceValue(PieceType pieceType) const;

    int getPieceSquareValue(
        PieceType pieceType,
        Color color,
        int square
    ) const;
};