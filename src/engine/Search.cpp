#include "Search.h"
#include "Zobrist.h"

#include <algorithm>
#include <cmath>

bool Search::setHybridAlpha(float alpha) {
    if (alpha == evaluation.getHybridAlpha()) return true;
    if (!evaluation.setHybridAlpha(alpha)) return false;
    clearTranspositionTable();
    return true;
}

#ifdef CHESSAI_SEARCH_DIAGNOSTICS
int Search::observedEvaluation(const Board& board, int ply) {
    if (leafObserver) leafObserver(board, ply, ply > 0 ? incomingMoveKind[ply] : -1);
    return evaluation.evaluate(board);
}
void Search::recordIncoming(const Board& board, const Move& move, int childPly) {
    incomingMoveKind[childPly] = move.getFlag() == MoveFlag::EnPassant ||
        !board.getPiece(move.getTo()).isEmpty() ? 1 : 0;
}
#define STATIC_EVALUATE(board, ply) observedEvaluation(board, ply)
#define RECORD_INCOMING(board, move, ply) recordIncoming(board, move, ply)
#else
#define STATIC_EVALUATE(board, ply) evaluation.evaluate(board)
#define RECORD_INCOMING(board, move, ply) ((void)0)
#endif

bool Search::setEvaluationMode(EvaluationMode mode)
{
    if (mode == evaluation.getMode()) return true;
    if (!evaluation.setMode(mode)) return false;
    // Bounds computed by another evaluator are no longer valid.
    clearTranspositionTable();
    return true;
}

// ============================================================
// FIXED-DEPTH SEARCH
// ============================================================

SearchResult Search::findBestMove(
    const Board& board,
    int depth
)
{
    if (depth < 1)
    {
        depth = 1;
    }

    nodes = 0;
    ttHits = 0;

    timeLimited = false;
    searchStopped = false;

    const auto startTime =
        std::chrono::steady_clock::now();

    SearchResult result =
        searchRoot(
            board,
            depth
        );

    const auto endTime =
        std::chrono::steady_clock::now();

    result.nodes = nodes;
    result.ttHits = ttHits;
    result.depthReached = depth;

    result.timeMs =
        std::chrono::duration_cast<
            std::chrono::milliseconds
        >(
            endTime - startTime
        ).count();

    return result;
}


// ============================================================
// TIMED SEARCH + ITERATIVE DEEPENING
// ============================================================

SearchResult Search::findBestMoveTimed(
    const Board& board,
    int timeLimitMs,
    int maxDepth
)
{
    if (timeLimitMs < 1)
    {
        timeLimitMs = 1;
    }

    if (maxDepth < 1)
    {
        maxDepth = 1;
    }

    nodes = 0;
    ttHits = 0;

    timeLimited = true;
    searchStopped = false;

    const auto startTime =
        std::chrono::steady_clock::now();

    deadline =
        startTime +
        std::chrono::milliseconds(
            timeLimitMs
        );

    std::vector<Move> legalMoves =
        moveGenerator.generateLegalMoves(board);

    SearchResult bestResult;


    // ========================================================
    // NO LEGAL MOVES
    // ========================================================

    if (legalMoves.empty())
    {
        if (
            moveGenerator.isInCheck(
                board,
                board.getSideToMove()
            )
        )
        {
            bestResult.score =
                (board.getSideToMove() == Color::White)
                    ? -MATE_SCORE
                    : MATE_SCORE;
        }
        else
        {
            bestResult.score = 0;
        }

        bestResult.nodes = nodes;
        bestResult.ttHits = ttHits;
        bestResult.depthReached = 0;

        const auto endTime =
            std::chrono::steady_clock::now();

        bestResult.timeMs =
            std::chrono::duration_cast<
                std::chrono::milliseconds
            >(
                endTime - startTime
            ).count();

        timeLimited = false;

        return bestResult;
    }


    // ========================================================
    // FALLBACK MOVE
    //
    // Ensures that even an extremely short search always
    // returns a legal move.
    // ========================================================

    orderMoves(
        board,
        legalMoves
    );

    bestResult.bestMove =
        legalMoves.front();

    bestResult.score =
        STATIC_EVALUATE(board, 0);

    bestResult.depthReached = 0;


    // ========================================================
    // ITERATIVE DEEPENING
    //
    // Depth 1
    // Depth 2
    // Depth 3
    // ...
    //
    // Only completed iterations are accepted.
    // ========================================================

    for (
        int depth = 1;
        depth <= maxDepth;
        ++depth
    )
    {
        if (shouldStop())
        {
            break;
        }

        SearchResult iteration =
            searchRoot(
                board,
                depth
            );

        // Search stopped in the middle of this depth.
        // Keep the result from the previous completed depth.
        if (searchStopped)
        {
            break;
        }

        bestResult.bestMove =
            iteration.bestMove;

        bestResult.score =
            iteration.score;

        bestResult.depthReached =
            depth;


        // Forced mate found
        if (
            std::abs(iteration.score) >=
            MATE_SCORE - 1000
        )
        {
            break;
        }
    }


    // ========================================================
    // FINAL RESULT
    // ========================================================

    const auto endTime =
        std::chrono::steady_clock::now();

    bestResult.nodes = nodes;
    bestResult.ttHits = ttHits;

    bestResult.timeMs =
        std::chrono::duration_cast<
            std::chrono::milliseconds
        >(
            endTime - startTime
        ).count();

    timeLimited = false;

    return bestResult;
}


// ============================================================
// ROOT SEARCH
// ============================================================

SearchResult Search::searchRoot(
    const Board& board,
    int depth
)
{
    SearchResult result;

    std::vector<Move> moves =
        moveGenerator.generateLegalMoves(board);


    // ========================================================
    // CHECKMATE / STALEMATE
    // ========================================================

    if (moves.empty())
    {
        if (
            moveGenerator.isInCheck(
                board,
                board.getSideToMove()
            )
        )
        {
            result.score =
                (board.getSideToMove() == Color::White)
                    ? -MATE_SCORE
                    : MATE_SCORE;
        }
        else
        {
            result.score = 0;
        }

        return result;
    }


    // ========================================================
    // TRANSPOSITION TABLE ROOT LOOKUP
    //
    // Mainly used here for move ordering.
    // ========================================================

    const uint64_t key =
        Zobrist::hash(board);

    TTEntry previousEntry;

    Move ttMove;
    bool hasTTMove = false;

    if (
        transpositionTable.probe(
            key,
            previousEntry
        )
    )
    {
        ++ttHits;

        if (
            isValidSquare(
                previousEntry.bestMove.getFrom()
            ) &&
            isValidSquare(
                previousEntry.bestMove.getTo()
            )
        )
        {
            ttMove =
                previousEntry.bestMove;

            hasTTMove = true;
        }
    }


    // ========================================================
    // MOVE ORDERING
    // ========================================================

    orderMoves(
        board,
        moves,
        hasTTMove
            ? &ttMove
            : nullptr
    );


    const Color side =
        board.getSideToMove();

    int alpha = -INF;
    int beta = INF;

    int bestScore =
        (side == Color::White)
            ? -INF
            : INF;

    Move bestMove;


    // ========================================================
    // WHITE ROOT
    // ========================================================

    if (side == Color::White)
    {
        for (const Move& move : moves)
        {
            if (shouldStop())
            {
                break;
            }

            Board nextBoard = board;

            nextBoard.makeMove(move);
            RECORD_INCOMING(board, move, 1);

            const int score =
                alphaBeta(
                    nextBoard,
                    depth - 1,
                    alpha,
                    beta,
                    1
                );

            if (searchStopped)
            {
                break;
            }

            if (score > bestScore)
            {
                bestScore = score;
                bestMove = move;
            }

            alpha =
                std::max(
                    alpha,
                    bestScore
                );
        }
    }


    // ========================================================
    // BLACK ROOT
    // ========================================================

    else
    {
        for (const Move& move : moves)
        {
            if (shouldStop())
            {
                break;
            }

            Board nextBoard = board;

            nextBoard.makeMove(move);
            RECORD_INCOMING(board, move, 1);

            const int score =
                alphaBeta(
                    nextBoard,
                    depth - 1,
                    alpha,
                    beta,
                    1
                );

            if (searchStopped)
            {
                break;
            }

            if (score < bestScore)
            {
                bestScore = score;
                bestMove = move;
            }

            beta =
                std::min(
                    beta,
                    bestScore
                );
        }
    }


    // ========================================================
    // STORE ROOT POSITION
    // ========================================================

    if (!searchStopped)
    {
        transpositionTable.store(
            key,
            depth,
            scoreToTT(
                bestScore,
                0
            ),
            TTFlag::Exact,
            bestMove
        );
    }


    result.bestMove = bestMove;
    result.score = bestScore;

    return result;
}


// ============================================================
// ALPHA-BETA SEARCH
// ============================================================

int Search::alphaBeta(
    const Board& board,
    int depth,
    int alpha,
    int beta,
    int ply
)
{
    ++nodes;


    // ========================================================
    // TIME LIMIT
    // ========================================================

    if (shouldStop())
    {
        return STATIC_EVALUATE(board, ply);
    }


    // ========================================================
    // SAFETY LIMIT
    // ========================================================

    if (ply >= MAX_SEARCH_PLY)
    {
        return STATIC_EVALUATE(board, ply);
    }


    // ========================================================
    // QUIESCENCE
    // ========================================================

    if (depth <= 0)
    {
        return quiescence(
            board,
            alpha,
            beta,
            ply
        );
    }


    const int originalAlpha = alpha;
    const int originalBeta = beta;


    // ========================================================
    // TRANSPOSITION TABLE LOOKUP
    // ========================================================

    const uint64_t key =
        Zobrist::hash(board);

    TTEntry ttEntry;

    Move ttMove;
    bool hasTTMove = false;

    if (
        transpositionTable.probe(
            key,
            ttEntry
        )
    )
    {
        ++ttHits;

        if (
            isValidSquare(
                ttEntry.bestMove.getFrom()
            ) &&
            isValidSquare(
                ttEntry.bestMove.getTo()
            )
        )
        {
            ttMove =
                ttEntry.bestMove;

            hasTTMove = true;
        }


        // Only trust stored score when it was searched
        // at least as deeply as this position.
        if (ttEntry.depth >= depth)
        {
            const int ttScore =
                scoreFromTT(
                    ttEntry.score,
                    ply
                );

            if (ttEntry.flag == TTFlag::Exact)
            {
                return ttScore;
            }

            if (ttEntry.flag == TTFlag::LowerBound)
            {
                alpha =
                    std::max(
                        alpha,
                        ttScore
                    );
            }
            else if (ttEntry.flag == TTFlag::UpperBound)
            {
                beta =
                    std::min(
                        beta,
                        ttScore
                    );
            }

            if (alpha >= beta)
            {
                return ttScore;
            }
        }
    }


    // ========================================================
    // GENERATE LEGAL MOVES
    // ========================================================

    std::vector<Move> moves =
        moveGenerator.generateLegalMoves(board);


    // ========================================================
    // CHECKMATE / STALEMATE
    // ========================================================

    if (moves.empty())
    {
        const Color side =
            board.getSideToMove();

        if (
            moveGenerator.isInCheck(
                board,
                side
            )
        )
        {
            if (side == Color::White)
            {
                return -MATE_SCORE + ply;
            }

            return MATE_SCORE - ply;
        }

        return 0;
    }


    // ========================================================
    // MOVE ORDERING
    // ========================================================

    orderMoves(
        board,
        moves,
        hasTTMove
            ? &ttMove
            : nullptr
    );


    Move bestMove;

    int bestScore =
        (board.getSideToMove() == Color::White)
            ? -INF
            : INF;


    // ========================================================
    // WHITE = MAXIMIZING
    // ========================================================

    if (board.getSideToMove() == Color::White)
    {
        for (const Move& move : moves)
        {
            if (shouldStop())
            {
                return STATIC_EVALUATE(board, ply);
            }

            Board nextBoard = board;

            nextBoard.makeMove(move);
            RECORD_INCOMING(board, move, ply + 1);

            const int score =
                alphaBeta(
                    nextBoard,
                    depth - 1,
                    alpha,
                    beta,
                    ply + 1
                );

            if (searchStopped)
            {
                return STATIC_EVALUATE(board, ply);
            }

            if (score > bestScore)
            {
                bestScore = score;
                bestMove = move;
            }

            alpha =
                std::max(
                    alpha,
                    bestScore
                );

            if (alpha >= beta)
            {
                break;
            }
        }
    }


    // ========================================================
    // BLACK = MINIMIZING
    // ========================================================

    else
    {
        for (const Move& move : moves)
        {
            if (shouldStop())
            {
                return STATIC_EVALUATE(board, ply);
            }

            Board nextBoard = board;

            nextBoard.makeMove(move);
            RECORD_INCOMING(board, move, ply + 1);

            const int score =
                alphaBeta(
                    nextBoard,
                    depth - 1,
                    alpha,
                    beta,
                    ply + 1
                );

            if (searchStopped)
            {
                return STATIC_EVALUATE(board, ply);
            }

            if (score < bestScore)
            {
                bestScore = score;
                bestMove = move;
            }

            beta =
                std::min(
                    beta,
                    bestScore
                );

            if (alpha >= beta)
            {
                break;
            }
        }
    }


    // ========================================================
    // STORE RESULT IN TRANSPOSITION TABLE
    // ========================================================

    if (!searchStopped)
    {
        TTFlag flag;

        if (bestScore <= originalAlpha)
        {
            flag =
                TTFlag::UpperBound;
        }
        else if (bestScore >= originalBeta)
        {
            flag =
                TTFlag::LowerBound;
        }
        else
        {
            flag =
                TTFlag::Exact;
        }

        transpositionTable.store(
            key,
            depth,
            scoreToTT(
                bestScore,
                ply
            ),
            flag,
            bestMove
        );
    }


    return bestScore;
}


// ============================================================
// QUIESCENCE SEARCH
// ============================================================

int Search::quiescence(
    const Board& board,
    int alpha,
    int beta,
    int ply
)
{
    ++nodes;


    // ========================================================
    // TIME LIMIT
    // ========================================================

    if (shouldStop())
    {
        return STATIC_EVALUATE(board, ply);
    }


    // ========================================================
    // SAFETY LIMIT
    // ========================================================

    if (ply >= MAX_SEARCH_PLY)
    {
        return STATIC_EVALUATE(board, ply);
    }


    const Color side =
        board.getSideToMove();

    const bool inCheck =
        moveGenerator.isInCheck(
            board,
            side
        );


    std::vector<Move> moves =
        moveGenerator.generateLegalMoves(board);


    // ========================================================
    // CHECKMATE / STALEMATE
    // ========================================================

    if (moves.empty())
    {
        if (inCheck)
        {
            if (side == Color::White)
            {
                return -MATE_SCORE + ply;
            }

            return MATE_SCORE - ply;
        }

        return 0;
    }


    // ========================================================
    // IN CHECK
    //
    // Stand-pat is not allowed while the king is in check.
    // We must search every legal escape.
    // ========================================================

    if (inCheck)
    {
        orderMoves(
            board,
            moves
        );


        // ----------------------------------------------------
        // WHITE
        // ----------------------------------------------------

        if (side == Color::White)
        {
            int bestScore = -INF;

            for (const Move& move : moves)
            {
                if (shouldStop())
                {
                    return STATIC_EVALUATE(board, ply);
                }

                Board nextBoard = board;

                nextBoard.makeMove(move);
            RECORD_INCOMING(board, move, ply + 1);

                const int score =
                    quiescence(
                        nextBoard,
                        alpha,
                        beta,
                        ply + 1
                    );

                if (searchStopped)
                {
                    return STATIC_EVALUATE(board, ply);
                }

                bestScore =
                    std::max(
                        bestScore,
                        score
                    );

                alpha =
                    std::max(
                        alpha,
                        bestScore
                    );

                if (alpha >= beta)
                {
                    break;
                }
            }

            return bestScore;
        }


        // ----------------------------------------------------
        // BLACK
        // ----------------------------------------------------

        int bestScore = INF;

        for (const Move& move : moves)
        {
            if (shouldStop())
            {
                return STATIC_EVALUATE(board, ply);
            }

            Board nextBoard = board;

            nextBoard.makeMove(move);
            RECORD_INCOMING(board, move, ply + 1);

            const int score =
                quiescence(
                    nextBoard,
                    alpha,
                    beta,
                    ply + 1
                );

            if (searchStopped)
            {
                return STATIC_EVALUATE(board, ply);
            }

            bestScore =
                std::min(
                    bestScore,
                    score
                );

            beta =
                std::min(
                    beta,
                    bestScore
                );

            if (alpha >= beta)
            {
                break;
            }
        }

        return bestScore;
    }


    // ========================================================
    // STATIC EVALUATION
    // ========================================================

    const int standPat =
        STATIC_EVALUATE(board, ply);


    // ========================================================
    // WHITE QUIESCENCE
    // ========================================================

    if (side == Color::White)
    {
        if (standPat >= beta)
        {
            return beta;
        }

        if (standPat > alpha)
        {
            alpha = standPat;
        }

        orderMoves(
            board,
            moves
        );

        for (const Move& move : moves)
        {
            // Only tactical moves
            if (
                move.getFlag() != MoveFlag::Capture &&
                move.getFlag() != MoveFlag::EnPassant &&
                move.getFlag() != MoveFlag::Promotion
            )
            {
                continue;
            }

            if (shouldStop())
            {
                return STATIC_EVALUATE(board, ply);
            }

            Board nextBoard = board;

            nextBoard.makeMove(move);
            RECORD_INCOMING(board, move, ply + 1);

            const int score =
                quiescence(
                    nextBoard,
                    alpha,
                    beta,
                    ply + 1
                );

            if (searchStopped)
            {
                return STATIC_EVALUATE(board, ply);
            }

            if (score >= beta)
            {
                return beta;
            }

            if (score > alpha)
            {
                alpha = score;
            }
        }

        return alpha;
    }


    // ========================================================
    // BLACK QUIESCENCE
    // ========================================================

    if (standPat <= alpha)
    {
        return alpha;
    }

    if (standPat < beta)
    {
        beta = standPat;
    }

    orderMoves(
        board,
        moves
    );

    for (const Move& move : moves)
    {
        // Only tactical moves
        if (
            move.getFlag() != MoveFlag::Capture &&
            move.getFlag() != MoveFlag::EnPassant &&
            move.getFlag() != MoveFlag::Promotion
        )
        {
            continue;
        }

        if (shouldStop())
        {
            return STATIC_EVALUATE(board, ply);
        }

        Board nextBoard = board;

        nextBoard.makeMove(move);
            RECORD_INCOMING(board, move, ply + 1);

        const int score =
            quiescence(
                nextBoard,
                alpha,
                beta,
                ply + 1
            );

        if (searchStopped)
        {
            return STATIC_EVALUATE(board, ply);
        }

        if (score <= alpha)
        {
            return alpha;
        }

        if (score < beta)
        {
            beta = score;
        }
    }

    return beta;
}


// ============================================================
// TIME CHECK
// ============================================================

bool Search::shouldStop()
{
    if (!timeLimited)
    {
        return false;
    }

    if (searchStopped)
    {
        return true;
    }

    if (
        std::chrono::steady_clock::now() >=
        deadline
    )
    {
        searchStopped = true;

        return true;
    }

    return false;
}


// ============================================================
// MOVE ORDERING
// ============================================================

void Search::orderMoves(
    const Board& board,
    std::vector<Move>& moves,
    const Move* ttMove
) const
{
    std::sort(
        moves.begin(),
        moves.end(),

        [&](const Move& a, const Move& b)
        {
            return
                scoreMove(
                    board,
                    a,
                    ttMove
                )
                >
                scoreMove(
                    board,
                    b,
                    ttMove
                );
        }
    );
}


// ============================================================
// MOVE ORDER SCORE
//
// This does not determine the actual quality of a move.
// It only determines which moves alpha-beta searches first.
// ============================================================

int Search::scoreMove(
    const Board& board,
    const Move& move,
    const Move* ttMove
) const
{
    // ========================================================
    // TRANSPOSITION TABLE MOVE
    // ========================================================

    if (
        ttMove != nullptr &&
        movesEqual(
            move,
            *ttMove
        )
    )
    {
        return 1000000;
    }


    int score = 0;

    const Piece movingPiece =
        board.getPiece(
            move.getFrom()
        );

    const Piece targetPiece =
        board.getPiece(
            move.getTo()
        );


    // ========================================================
    // PROMOTION
    // ========================================================

    if (move.getFlag() == MoveFlag::Promotion)
    {
        score += 10000;

        score +=
            moveOrderingPieceValue(
                move.getPromotionPiece()
            );

        if (!targetPiece.isEmpty())
        {
            score +=
                10 *
                moveOrderingPieceValue(
                    targetPiece.type
                );
        }
    }


    // ========================================================
    // CAPTURE
    //
    // MVV-LVA:
    // Most Valuable Victim / Least Valuable Attacker
    // ========================================================

    if (move.getFlag() == MoveFlag::Capture)
    {
        const int victimValue =
            moveOrderingPieceValue(
                targetPiece.type
            );

        const int attackerValue =
            moveOrderingPieceValue(
                movingPiece.type
            );

        score += 5000;

        score +=
            10 * victimValue
            - attackerValue;
    }


    // ========================================================
    // EN PASSANT
    // ========================================================

    if (move.getFlag() == MoveFlag::EnPassant)
    {
        const int attackerValue =
            moveOrderingPieceValue(
                movingPiece.type
            );

        score += 5000;

        score +=
            10 * 100
            - attackerValue;
    }


    // ========================================================
    // CASTLING
    // ========================================================

    if (
        move.getFlag() == MoveFlag::KingCastle ||
        move.getFlag() == MoveFlag::QueenCastle
    )
    {
        score += 1000;
    }


    return score;
}


// ============================================================
// PIECE VALUES USED FOR MOVE ORDERING
// ============================================================

int Search::moveOrderingPieceValue(
    PieceType pieceType
) const
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
            return 20000;

        case PieceType::None:
        default:
            return 0;
    }
}


// ============================================================
// MOVE COMPARISON
// ============================================================

bool Search::movesEqual(
    const Move& a,
    const Move& b
) const
{
    return
        a.getFrom() ==
            b.getFrom() &&

        a.getTo() ==
            b.getTo() &&

        a.getFlag() ==
            b.getFlag() &&

        a.getPromotionPiece() ==
            b.getPromotionPiece();
}


// ============================================================
// STORE MATE SCORES IN TT
//
// Mate score depends on ply. We normalize it before storing.
// ============================================================

int Search::scoreToTT(
    int score,
    int ply
) const
{
    if (
        score >=
        MATE_SCORE - 1000
    )
    {
        return score + ply;
    }

    if (
        score <=
        -MATE_SCORE + 1000
    )
    {
        return score - ply;
    }

    return score;
}


// ============================================================
// RESTORE MATE SCORE FROM TT
// ============================================================

int Search::scoreFromTT(
    int score,
    int ply
) const
{
    if (
        score >=
        MATE_SCORE - 1000
    )
    {
        return score - ply;
    }

    if (
        score <=
        -MATE_SCORE + 1000
    )
    {
        return score + ply;
    }

    return score;
}


// ============================================================
// CLEAR TRANSPOSITION TABLE
// ============================================================

void Search::clearTranspositionTable()
{
    transpositionTable.clear();
}
