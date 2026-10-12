#pragma once

#include "Types.h"
#include <string>

enum class MoveFlag : uint8_t
{
    Quiet,
    Capture,
    DoublePawnPush,
    KingCastle,
    QueenCastle,
    EnPassant,
    Promotion
};

class Move
{
public:
    Move();

    Move(
        int from,
        int to,
        MoveFlag flag = MoveFlag::Quiet,
        PieceType promotionPiece = PieceType::None
    );

    int getFrom() const;
    int getTo() const;

    MoveFlag getFlag() const;
    PieceType getPromotionPiece() const;

    std::string toString() const;

private:
    int fromSquare;
    int toSquare;

    MoveFlag flag;
    PieceType promotionPiece;
};