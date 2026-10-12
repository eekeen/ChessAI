#pragma once

#include "../chess/Board.h"
#include "../chess/Move.h"
#include "../chess/MoveGenerator.h"

#include "PositionEvaluator.h"
#include "TranspositionTable.h"

#include <chrono>
#include <array>
#include <cstdint>
#include <vector>
#ifdef CHESSAI_SEARCH_DIAGNOSTICS
#include <functional>
#endif

struct SearchResult
{
    Move bestMove;

    int score = 0;

    uint64_t nodes = 0;
    uint64_t ttHits = 0;

    int depthReached = 0;

    long long timeMs = 0;
};

class Search
{
public:
    SearchResult findBestMove(
        const Board& board,
        int depth
    );

    SearchResult findBestMoveTimed(
        const Board& board,
        int timeLimitMs,
        int maxDepth = 64
    );

    void clearTranspositionTable();

    bool setEvaluationMode(EvaluationMode mode);
    bool setHybridAlpha(float alpha);
    float getHybridAlpha() const { return evaluation.getHybridAlpha(); }
    EvaluationMode getEvaluationMode() const { return evaluation.getMode(); }
#ifdef CHESSAI_SEARCH_DIAGNOSTICS
    using LeafObserver = std::function<void(const Board&, int, int)>;
    void setLeafObserver(LeafObserver observer) { leafObserver = std::move(observer); }
#endif

private:
#ifdef CHESSAI_SEARCH_DIAGNOSTICS
    LeafObserver leafObserver;
    // -1 unknown/root, 0 quiet, 1 capture. Only compiled in the diagnostics core.
    std::array<int, 66> incomingMoveKind{};
    int observedEvaluation(const Board& board, int ply);
    void recordIncoming(const Board& board, const Move& move, int childPly);
#endif
    static constexpr int INF = 1000000;
    static constexpr int MATE_SCORE = 100000;
    static constexpr int MAX_SEARCH_PLY = 64;

    MoveGenerator moveGenerator;
    PositionEvaluator evaluation;

    TranspositionTable transpositionTable;

    uint64_t nodes = 0;
    uint64_t ttHits = 0;

    bool timeLimited = false;
    bool searchStopped = false;

    std::chrono::steady_clock::time_point deadline;

    SearchResult searchRoot(
        const Board& board,
        int depth
    );

    int alphaBeta(
        const Board& board,
        int depth,
        int alpha,
        int beta,
        int ply
    );

    int quiescence(
        const Board& board,
        int alpha,
        int beta,
        int ply
    );

    bool shouldStop();

    void orderMoves(
        const Board& board,
        std::vector<Move>& moves,
        const Move* ttMove = nullptr
    ) const;

    int scoreMove(
        const Board& board,
        const Move& move,
        const Move* ttMove
    ) const;

    int moveOrderingPieceValue(
        PieceType pieceType
    ) const;

    bool movesEqual(
        const Move& a,
        const Move& b
    ) const;

    int scoreToTT(
        int score,
        int ply
    ) const;

    int scoreFromTT(
        int score,
        int ply
    ) const;
};
