#pragma once

#include "Game.h"
#include "../engine/Search.h"

#include <cstdint>

struct EngineMoveResult
{
    bool moveMade = false;
    bool wasCapture = false;
    bool fromBook = false;

    Move move;

    int score = 0;
    int depth = 0;

    uint64_t nodes = 0;
    uint64_t ttHits = 0;

    long long timeMs = 0;
};

class GameController
{
public:
    GameController();

    void newGame();

    bool setEvaluationMode(EvaluationMode mode) { return search.setEvaluationMode(mode); }
    EvaluationMode getEvaluationMode() const { return search.getEvaluationMode(); }
    float getHybridAlpha() const { return search.getHybridAlpha(); }

    const Game& getGame() const;

    bool makePlayerMove(
        int fromSquare,
        int toSquare,
        PieceType promotionPiece = PieceType::Queen
    );

    EngineMoveResult makeEngineMove(
        int thinkingTimeMs,
        int maxDepth = 64,
        int targetElo = 2000
    );

private:
    Game game;
    Search search;
};
