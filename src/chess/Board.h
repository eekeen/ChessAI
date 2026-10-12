#pragma once

#include "Types.h"
#include "Move.h"

#include <array>
#include <string>

class Board
{
public:
    Board();

    void reset();

    bool loadFEN(const std::string& fen);

    Piece getPiece(int square) const;
    void setPiece(int square, Piece piece);

    Color getSideToMove() const;

    bool canCastleKingside(Color color) const;
    bool canCastleQueenside(Color color) const;

    int getEnPassantSquare() const;

    int getHalfmoveClock() const;
    int getFullmoveNumber() const;

    void makeMove(const Move& move);

    void print() const;

private:
    std::array<Piece, 64> squares;

    Color sideToMove;

    bool whiteCanCastleKingside;
    bool whiteCanCastleQueenside;
    bool blackCanCastleKingside;
    bool blackCanCastleQueenside;

    int enPassantSquare;

    int halfmoveClock;
    int fullmoveNumber;
};