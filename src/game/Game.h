#pragma once

#include "../chess/Board.h"
#include "../chess/Move.h"
#include "../chess/MoveGenerator.h"

#include <cstdint>
#include <vector>

enum class GameState
{
    Ongoing,

    WhiteCheckmate,
    BlackCheckmate,

    Stalemate,

    DrawFiftyMove,
    DrawRepetition,
    DrawInsufficientMaterial
};

class Game
{
public:
    Game();

    void reset();

    const Board& getBoard() const;

    Color getSideToMove() const;

    std::vector<Move> getLegalMoves() const;

    const std::vector<Move>& getMoveHistory() const;

    bool tryMove(
        int fromSquare,
        int toSquare,
        PieceType promotionPiece = PieceType::Queen
    );

    bool tryMove(const Move& move);

    GameState getGameState() const;

    bool isInCheck() const;

    bool isThreefoldRepetition() const;

    bool isFiftyMoveDraw() const;

    bool isInsufficientMaterial() const;

private:
    Board board;
    MoveGenerator moveGenerator;

    std::vector<Move> moveHistory;

    std::vector<uint64_t> positionHistory;

    bool movesMatch(
        const Move& legalMove,
        int fromSquare,
        int toSquare,
        PieceType promotionPiece
    ) const;

    void recordPosition();
};