#include "Move.h"

Move::Move()
    : fromSquare(-1),
      toSquare(-1),
      flag(MoveFlag::Quiet),
      promotionPiece(PieceType::None)
{
}

Move::Move(
    int from,
    int to,
    MoveFlag moveFlag,
    PieceType promotion
)
    : fromSquare(from),
      toSquare(to),
      flag(moveFlag),
      promotionPiece(promotion)
{
}

int Move::getFrom() const
{
    return fromSquare;
}

int Move::getTo() const
{
    return toSquare;
}

MoveFlag Move::getFlag() const
{
    return flag;
}

PieceType Move::getPromotionPiece() const
{
    return promotionPiece;
}

std::string Move::toString() const
{
    if (!isValidSquare(fromSquare) || !isValidSquare(toSquare))
        return "invalid";

    std::string result;

    result += static_cast<char>('a' + fileOf(fromSquare));
    result += static_cast<char>('1' + rankOf(fromSquare));

    result += static_cast<char>('a' + fileOf(toSquare));
    result += static_cast<char>('1' + rankOf(toSquare));

    if (flag == MoveFlag::Promotion)
    {
        switch (promotionPiece)
        {
            case PieceType::Queen:
                result += 'q';
                break;

            case PieceType::Rook:
                result += 'r';
                break;

            case PieceType::Bishop:
                result += 'b';
                break;

            case PieceType::Knight:
                result += 'n';
                break;

            default:
                break;
        }
    }

    return result;
}