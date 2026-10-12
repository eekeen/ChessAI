#pragma once

#include "Board.h"
#include "Move.h"

#include <utility>
#include <vector>

class MoveGenerator
{
public:
    std::vector<Move> generatePseudoLegalMoves(
        const Board& board
    ) const;

    std::vector<Move> generateLegalMoves(
        const Board& board
    ) const;

    bool isSquareAttacked(
        const Board& board,
        int square,
        Color attacker
    ) const;

    bool isInCheck(
        const Board& board,
        Color color
    ) const;

private:
    void generatePawnMoves(
        const Board& board,
        int square,
        Color color,
        std::vector<Move>& moves
    ) const;

    void generateKnightMoves(
        const Board& board,
        int square,
        Color color,
        std::vector<Move>& moves
    ) const;

    void generateBishopMoves(
        const Board& board,
        int square,
        Color color,
        std::vector<Move>& moves
    ) const;

    void generateRookMoves(
        const Board& board,
        int square,
        Color color,
        std::vector<Move>& moves
    ) const;

    void generateQueenMoves(
        const Board& board,
        int square,
        Color color,
        std::vector<Move>& moves
    ) const;

    void generateKingMoves(
        const Board& board,
        int square,
        Color color,
        std::vector<Move>& moves
    ) const;

    void generateSlidingMoves(
        const Board& board,
        int square,
        Color color,
        const std::vector<std::pair<int, int>>& directions,
        std::vector<Move>& moves
    ) const;
};