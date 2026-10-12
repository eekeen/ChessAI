#include "engine/Search.h"
#include <array>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <sstream>
#include <stdexcept>
#include <string>
#include <vector>

using Clock = std::chrono::steady_clock;
static double elapsedMs(Clock::time_point start) {
    return std::chrono::duration<double, std::milli>(Clock::now() - start).count();
}
static int positive(const std::string& text) {
    size_t used;
    int value = std::stoi(text, &used);
    if (used != text.size() || value < 1) throw std::invalid_argument("Expected positive integer: " + text);
    return value;
}
static void quote(const std::string& text) {
    std::cout << '"';
    for (unsigned char c : text) {
        if (c == '"' || c == '\\') std::cout << '\\' << c;
        else if (c < 32) throw std::invalid_argument("Control character in manifest text");
        else std::cout << c;
    }
    std::cout << '"';
}
struct Position { std::string id, fen; Board board; };

int main(int argc, char** argv) {
    try {
        std::string manifest = "benchmarks/performance-middlegames-v1.tsv";
        int repetitions = 3, evaluations = 200000, warmup = 10000;
        std::vector<int> budgets{100, 250, 1000};
        for (int i = 1; i < argc; ++i) {
            const std::string option = argv[i];
            if (option == "--help") {
                std::cout << "ChessAI_performance --positions FILE --repetitions 3 --evaluations 200000 --warmup 10000 --budgets 100,250,1000\n";
                return 0;
            }
            if (++i == argc) throw std::invalid_argument("Missing option value");
            const std::string value = argv[i];
            if (option == "--positions") manifest = value;
            else if (option == "--repetitions") repetitions = positive(value);
            else if (option == "--evaluations") evaluations = positive(value);
            else if (option == "--warmup") warmup = positive(value);
            else if (option == "--budgets") {
                budgets.clear(); std::istringstream values(value); std::string part;
                while (std::getline(values, part, ',')) budgets.push_back(positive(part));
                if (budgets.empty() || value.back() == ',') throw std::invalid_argument("Invalid budgets");
            } else throw std::invalid_argument("Unknown option: " + option);
        }
        if (!MLEvaluationV2::directAvailable() || !MLEvaluationV2::residualAvailable())
            throw std::runtime_error("Both real V2 models are required; no V1 fallback in performance comparisons");
        std::ifstream input(manifest);
        std::string version, line;
        if (!std::getline(input, version)) throw std::runtime_error("Cannot read position manifest");
        if (!version.empty() && version.back() == '\r') version.pop_back();
        std::vector<Position> positions;
        while (std::getline(input, line)) {
            if (!line.empty() && line.back() == '\r') line.pop_back();
            if (line.empty()) continue;
            const auto tab = line.find('\t');
            if (tab == std::string::npos) throw std::invalid_argument("Manifest rows must be id TAB six-field FEN");
            Position position{line.substr(0, tab), line.substr(tab + 1), Board{}};
            if (!position.board.loadFEN(position.fen) || MoveGenerator{}.generateLegalMoves(position.board).empty())
                throw std::invalid_argument("Invalid or terminal manifest position: " + position.id);
            if (MoveGenerator{}.isInCheck(position.board, position.board.getSideToMove() == Color::White ? Color::Black : Color::White))
                throw std::invalid_argument("Side not to move is in check: " + position.id);
            positions.push_back(position);
        }
        if (positions.empty()) throw std::invalid_argument("Empty position manifest");
        std::cout << std::setprecision(12);
        std::cout << "{\"type\":\"metadata\",\"build_type\":\"" << CHESSAI_BUILD_TYPE
                  << "\",\"compiler\":\"" << CHESSAI_COMPILER << "\",\"hybrid_alpha\":"
                  << EvaluationConfig::ProductionHybridAlpha << ",\"models\":{\"classic\":\"handcrafted-material-pst\",\"ml\":";
        quote(MLEvaluationV2::directModelVersion()); std::cout << ",\"hybrid\":";
        quote(MLEvaluationV2::residualModelVersion());
        std::cout << "},\"inference_backend\":"; quote(MLEvaluationV2::residualBackendName());
        std::cout << ",\"manifest_version\":"; quote(version);
        std::cout << ",\"positions\":" << positions.size() << ",\"repetitions\":" << repetitions
                  << ",\"evaluations_per_batch\":" << evaluations << ",\"warmup_evaluations_per_batch\":" << warmup
                  << ",\"search_warmup_ms_per_position_mode\":10,\"max_depth\":64,\"tt_entries\":262144,\"search_threads\":1}\n";
        for (size_t i = 0; i < positions.size(); ++i) {
            std::cout << "{\"type\":\"position\",\"index\":" << i << ",\"id\":";
            quote(positions[i].id); std::cout << ",\"fen\":"; quote(positions[i].fen); std::cout << "}\n";
        }
        const std::array<EvaluationMode, 3> modes{EvaluationMode::Classic, EvaluationMode::ML, EvaluationMode::Hybrid};
        volatile long long sink = 0;
        // Aggregate clocks: no timer call within the repeated evaluation loop.
        for (int repeat = 0; repeat < repetitions; ++repeat) {
            for (int slot = 0; slot < 3; ++slot) {
                const auto mode = modes[(slot + repeat) % 3];
                PositionEvaluator evaluator; evaluator.setMode(mode);
                for (int i = 0; i < warmup; ++i) sink += evaluator.evaluate(positions[i % positions.size()].board);
                long long checksum = 0;
                const auto start = Clock::now();
                for (int i = 0; i < evaluations; ++i) checksum += evaluator.evaluate(positions[i % positions.size()].board);
                const double ms = elapsedMs(start);
                sink += checksum;
                std::cout << "{\"type\":\"static\",\"mode\":\"" << PositionEvaluator::modeName(mode)
                          << "\",\"repetition\":" << repeat << ",\"evaluations\":" << evaluations
                          << ",\"elapsed_ms\":" << ms << ",\"checksum\":" << checksum << "}\n";
            }
        }
        std::array<Search, 3> searches;
        for (size_t m = 0; m < modes.size(); ++m) {
            searches[m].setEvaluationMode(modes[m]);
            for (const auto& position : positions) {
                searches[m].clearTranspositionTable();
                searches[m].findBestMoveTimed(position.board, 10, 64);
            }
        }
        for (size_t budgetIndex = 0; budgetIndex < budgets.size(); ++budgetIndex) {
            const int budget = budgets[budgetIndex];
            for (int repeat = 0; repeat < repetitions; ++repeat) {
                for (size_t p = 0; p < positions.size(); ++p) {
                    for (int slot = 0; slot < 3; ++slot) {
                        const size_t m = (slot + repeat + p + budgetIndex) % 3;
                        auto& search = searches[m];
                        search.clearTranspositionTable(); // Outside timing; identical cold TT for every sample.
                        const auto start = Clock::now();
                        const auto result = search.findBestMoveTimed(positions[p].board, budget, 64);
                        const double ms = elapsedMs(start);
                        bool legal = false;
                        for (const auto& move : MoveGenerator{}.generateLegalMoves(positions[p].board))
                            legal |= move.toString() == result.bestMove.toString();
                        if (!legal) throw std::runtime_error("Search returned illegal move");
                        std::cout << "{\"type\":\"search\",\"mode\":\"" << PositionEvaluator::modeName(modes[m])
                                  << "\",\"budget_ms\":" << budget << ",\"repetition\":" << repeat << ",\"position\":" << p
                                  << ",\"elapsed_ms\":" << ms << ",\"engine_elapsed_ms\":" << result.timeMs
                                  << ",\"completed_depth\":" << result.depthReached << ",\"nodes\":" << result.nodes
                                  << ",\"tt_hits\":" << result.ttHits << ",\"score\":" << result.score
                                  << ",\"bestmove\":\"" << result.bestMove.toString() << "\"}\n";
                    }
                    std::cerr << "Performance " << budget << " ms, repetition " << repeat + 1 << '/' << repetitions
                              << ", position " << p + 1 << '/' << positions.size() << '\n';
                }
            }
        }
        std::cout << "{\"type\":\"complete\",\"warmup_and_static_checksum\":" << sink << "}\n";
    } catch (const std::exception& error) { std::cerr << "Performance error: " << error.what() << '\n'; return 1; }
}
