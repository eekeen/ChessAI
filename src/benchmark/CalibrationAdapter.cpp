// Private line protocol for the external calibration harness, not a UCI engine.
// Uses the production core unchanged; no controller/difficulty/book layer.
#include "engine/Search.h"
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>

int main() {
    try {
#ifndef NDEBUG
        throw std::runtime_error("Calibration requires a Release build");
#endif
        Search search;
        if (!MLEvaluationV2::residualAvailable() ||
            std::string(MLEvaluationV2::residualModelVersion()) != "v2-residual-3fb0a29e8514af8c" ||
            search.getHybridAlpha() != .25f || !search.setEvaluationMode(EvaluationMode::Hybrid))
            throw std::runtime_error("Expected production Hybrid V2 residual model and alpha 0.25");
        std::cout << std::setprecision(12);
        std::string line;
        while (std::getline(std::cin, line)) {
            if (line == "quit") return 0;
            if (line == "hello") {
                std::cout << "{\"type\":\"hello\",\"protocol\":1,\"model\":\""
                          << MLEvaluationV2::residualModelVersion() << "\",\"alpha\":0.25,\"mode\":\"hybrid\",\"backend\":\""
                          << MLEvaluationV2::residualBackendName() << "\",\"build\":\"Release\",\"compiler\":\""
                          << CHESSAI_COMPILER << "\",\"threads\":1,\"tt_entries\":262144,\"tt_bytes\":"
                          << 262144 * sizeof(TTEntry) << ",\"max_depth\":64}\n" << std::flush;
            } else if (line == "newgame") {
                search.clearTranspositionTable();
                std::cout << "{\"type\":\"ready\"}\n" << std::flush;
            } else if (line.rfind("legal\t", 0) == 0) {
                Board board;
                if (!board.loadFEN(line.substr(6))) throw std::runtime_error("Invalid FEN");
                std::cout << "{\"type\":\"legal\",\"moves\":[";
                bool comma = false;
                for (const auto& move : MoveGenerator{}.generateLegalMoves(board)) {
                    if (comma) std::cout << ',';
                    std::cout << '\"' << move.toString() << '\"'; comma = true;
                }
                std::cout << "]}\n" << std::flush;
            } else if (line.rfind("search ", 0) == 0) {
                const auto tab = line.find('\t');
                if (tab == std::string::npos) throw std::runtime_error("Expected search milliseconds TAB six-field FEN");
                size_t used = 0;
                const auto text = line.substr(7, tab - 7);
                const int ms = std::stoi(text, &used);
                if (used != text.size() || ms < 1 || ms > 3600000) throw std::runtime_error("Invalid move budget");
                Board board;
                if (!board.loadFEN(line.substr(tab + 1))) throw std::runtime_error("Invalid FEN");
                const auto legal = MoveGenerator{}.generateLegalMoves(board);
                if (legal.empty()) throw std::runtime_error("Search requested on terminal position");
                const auto start = std::chrono::steady_clock::now();
                const auto result = search.findBestMoveTimed(board, ms, 64);
                const double elapsed = std::chrono::duration<double, std::milli>(std::chrono::steady_clock::now() - start).count();
                bool valid = false;
                for (const auto& move : legal) valid |= move.toString() == result.bestMove.toString();
                if (!valid) throw std::runtime_error("Production search returned an illegal move");
                std::cout << "{\"type\":\"move\",\"move\":\"" << result.bestMove.toString()
                          << "\",\"search_ms\":" << elapsed << ",\"engine_time_ms\":" << result.timeMs
                          << ",\"nodes\":" << result.nodes << ",\"depth\":" << result.depthReached << "}\n" << std::flush;
            } else throw std::runtime_error("Unknown calibration adapter command");
        }
    } catch (const std::exception& e) { std::cerr << e.what() << '\n'; return 1; }
}
