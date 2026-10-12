#pragma once

#include <cstdint>

enum class Color : uint8_t
{
    White,
    Black,
    None
};

enum class PieceType : uint8_t
{
    None,
    Pawn,
    Knight,
    Bishop,
    Rook,
    Queen,
    King
};

struct Piece
{
    PieceType type = PieceType::None;
    Color color = Color::None;

    bool isEmpty() const
    {
        return type == PieceType::None;
    }
};

inline Color oppositeColor(Color color)
{
    if (color == Color::White)
        return Color::Black;

    if (color == Color::Black)
        return Color::White;

    return Color::None;
}

inline int fileOf(int square)
{
    return square % 8;
}

inline int rankOf(int square)
{
    return square / 8;
}

inline bool isValidSquare(int square)
{
    return square >= 0 && square < 64;
}