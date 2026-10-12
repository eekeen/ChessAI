#include "engine/Search.h"
#include "engine/Zobrist.h"
#include "game/Game.h"
#include <cmath>
#include <iostream>
#include <algorithm>
#include <cmath>
#include <limits>
#include <stdexcept>

void require(bool condition, const char* message)
{
    if (!condition) throw std::runtime_error(message);
}

int main()
{
    try {
        Board board;
        PositionEvaluator evaluator;
        require(EvaluationConfig::ProductionHybridAlpha == .25f, "validated production alpha");
        require(evaluator.getHybridAlpha() == EvaluationConfig::ProductionHybridAlpha, "default evaluator alpha");
        require(Search{}.getHybridAlpha() == EvaluationConfig::ProductionHybridAlpha, "default search alpha");
        if (MLEvaluationV2::residualAvailable()) {
            require(evaluator.getMode() == EvaluationMode::Hybrid, "production default Hybrid V2");
            for (const char* fen : {"rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
                                   "7k/8/8/8/8/8/QQQQ4/K7 w - - 0 1"}) {
                require(board.loadFEN(fen), "production fixture");
                const int classic = Evaluation{}.evaluate(board);
                const float mixed = classic + EvaluationConfig::ProductionHybridAlpha * MLEvaluationV2::predict(board, true);
                require(evaluator.evaluate(board) == static_cast<int>(std::lround(std::clamp(mixed, -1500.f, 1500.f))), "production formula");
                require(evaluator.evaluate(board, EvaluationMode::Classic) == classic, "explicit Classic unchanged");
                if (MLEvaluationV2::directAvailable())
                    require(evaluator.evaluate(board, EvaluationMode::ML) == static_cast<int>(std::lround(std::clamp(MLEvaluationV2::predict(board, false), -1500.f, 1500.f))), "explicit Direct unchanged");
            }
            board.reset();
        }
        require(evaluator.evaluate(board, EvaluationMode::Classic) == 0, "classic start changed");
        auto input = MLEvaluation::features(board);
        int occupied = 0;
        for (int i = 0; i < 768; ++i) occupied += static_cast<int>(input[i]);
        require(occupied == 32 && input[768] == 1 && input[772] == 1, "start features");
        board.setPiece(3, {});
        require(evaluator.evaluate(board, EvaluationMode::Classic) < -800, "classic queen loss");
        for (auto mode : {EvaluationMode::Classic, EvaluationMode::ML, EvaluationMode::Hybrid}) {
            Search search;
            bool enabled = search.setEvaluationMode(mode);
            if (!PositionEvaluator::available(mode)) {
                require(!enabled && search.getEvaluationMode() == PositionEvaluator::defaultMode(), "missing-model mode");
                continue;
            }
            require(enabled, "mode selection");
            board.reset();
            const auto result = search.findBestMove(board, 2);
            bool legal = false;
            for (const auto& move : MoveGenerator{}.generateLegalMoves(board))
                legal |= move.toString() == result.bestMove.toString();
            require(legal, "search legal move");
            require(std::abs(evaluator.evaluate(board, mode)) < 99000, "static mate band");
            require(board.loadFEN("7k/6Q1/5K2/8/8/8/8/8 b - - 0 1"), "mate fen");
            require(search.findBestMove(board, 2).score == 100000, "mate independent of evaluator");
            require(board.loadFEN("7k/5K2/6Q1/8/8/8/8/8 b - - 0 1"), "stalemate fen");
            require(search.findBestMove(board, 2).score == 0, "stalemate");
        }
        if (PositionEvaluator::available(EvaluationMode::ML)) {
            board.reset();
            Search reused, fresh;
            reused.setEvaluationMode(EvaluationMode::Classic);
            reused.findBestMove(board, 2);
            reused.setEvaluationMode(EvaluationMode::ML);
            fresh.setEvaluationMode(EvaluationMode::ML);
            auto a = reused.findBestMove(board, 2), b = fresh.findBestMove(board, 2);
            require(a.score == b.score && a.nodes == b.nodes && a.ttHits == b.ttHits, "TT invalidation");
        }
        for (const char* fen : {"rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
                               "7k/8/8/8/8/8/QQQQ4/K7 w - - 0 1"}) {
            require(board.loadFEN(fen), "alpha fixture");
            const int classic = Evaluation{}.evaluate(board);
            require(evaluator.setHybridAlpha(0), "alpha zero accepted");
            require(evaluator.evaluate(board, EvaluationMode::Hybrid) == classic, "alpha zero EXACT Classic");
            require(evaluator.setHybridAlpha(1), "alpha one accepted");
            if (MLEvaluationV2::residualAvailable()) {
                const float oldHybrid = classic + MLEvaluationV2::predict(board, true);
                require(evaluator.evaluate(board, EvaluationMode::Hybrid) ==
                    static_cast<int>(std::lround(std::clamp(oldHybrid, -1500.0f, 1500.0f))), "alpha one preserves Hybrid");
                require(evaluator.setHybridAlpha(.25f), "alpha pilot accepted");
                const float scaled = classic + .25f * MLEvaluationV2::predict(board, true);
                require(evaluator.evaluate(board, EvaluationMode::Hybrid) ==
                    static_cast<int>(std::lround(std::clamp(scaled, -1500.0f, 1500.0f))), "alpha scales residual");
            }
        }
        require(!evaluator.setHybridAlpha(-.1f) && !evaluator.setHybridAlpha(1.1f) &&
                !evaluator.setHybridAlpha(std::numeric_limits<float>::quiet_NaN()), "reject invalid alpha");
        if (MLEvaluationV2::residualAvailable()) {
            board.reset();
            Search reused, fresh, classicSearch;
            reused.setEvaluationMode(EvaluationMode::Hybrid);
            fresh.setEvaluationMode(EvaluationMode::Hybrid);
            classicSearch.setEvaluationMode(EvaluationMode::Classic);
            reused.findBestMove(board, 2);
            require(reused.setHybridAlpha(0) && fresh.setHybridAlpha(0), "search alpha");
            auto a = reused.findBestMove(board, 2), b = fresh.findBestMove(board, 2), c = classicSearch.findBestMove(board, 2);
            require(a.score == b.score && a.nodes == b.nodes && a.ttHits == b.ttHits, "alpha clears TT");
            require(a.score == c.score && a.nodes == c.nodes && a.bestMove.toString() == c.bestMove.toString(), "alpha zero search equals Classic");
        }
        board.reset();
        Search timed, fixed;
        const auto completed = timed.findBestMoveTimed(board, 1000, 1);
        const auto reference = fixed.findBestMove(board, 1);
        require(completed.depthReached == 1 && completed.score == reference.score, "timed reports completed depth");
        const auto interrupted = timed.findBestMoveTimed(board, 1, 64);
        require(interrupted.depthReached >= 0 && interrupted.depthReached < 64, "interrupted iteration not reported complete");
        Game game;
        for (int i = 0; i < 2; ++i) {
            require(game.tryMove(6,21) && game.tryMove(62,45) && game.tryMove(21,6) && game.tryMove(45,62), "repetition moves");
        }
        require(game.getGameState() == GameState::DrawRepetition, "repetition preserved");
        board.reset();
        auto key = Zobrist::hash(board);
        board.makeMove(Move(12,28,MoveFlag::DoublePawnPush));
        require(key != Zobrist::hash(board), "zobrist move");
        std::cout << "Evaluation, search, TT, game-rule checks passed; model " << PositionEvaluator::modelVersion() << '\n';
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
