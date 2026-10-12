#include "engine/PositionEvaluator.h"
#include "engine/Search.h"
#include <chrono>
#include <iostream>
#include <string>
#include <vector>
#include <iomanip>
#include <algorithm>
#include <cmath>
#include <cstring>

int main(int argc, char** argv)
{
    const std::string operation = argc > 1 ? argv[1] : "bench";
    PositionEvaluator evaluator;
    if (operation == "compare-residual") {
        using B = MLEvaluationV2::Backend;
        if (!MLEvaluationV2::residualAvailable()) return 1;
        size_t count = 0, exact[6]{}, integerChanges[6]{};
        double sums[6]{}, maxima[6]{};
        const B backends[] = {B::Tail, B::Sparse, B::ActiveList, B::SparseOnly, B::ActiveListOnly};
        std::string fen;
        while (std::getline(std::cin, fen)) {
            Board board;
            if (!board.loadFEN(fen)) return 1;
            const auto reference = MLEvaluationV2::predictResidual(board, B::Reference);
            const int classic = Evaluation{}.evaluate(board);
            const auto rounded = [classic](float residual) {
                return std::lround(std::clamp(.25f * residual + classic, -1500.0f, 1500.0f));
            };
            for (int i = 0; i < 6; ++i) {
                const float candidate = i == 5 ? MLEvaluationV2::predict(board, true)
                                              : MLEvaluationV2::predictResidual(board, backends[i]);
                if (!std::isfinite(reference) || !std::isfinite(candidate)) return 1;
                exact[i] += std::memcmp(&reference, &candidate, sizeof(float)) == 0;
                const double difference = std::abs(double(reference) - candidate);
                sums[i] += difference; maxima[i] = std::max(maxima[i], difference);
                const auto candidateScore = i == 5 ? evaluator.evaluate(board, EvaluationMode::Hybrid) : rounded(candidate);
                integerChanges[i] += rounded(reference) != candidateScore;
            }
            ++count;
        }
        if (!count) return 1;
        std::cout << std::setprecision(12) << "{\"model\":\"" << MLEvaluationV2::residualModelVersion()
                  << "\",\"alpha\":0.25,\"positions\":" << count
                  << ",\"avx2_active\":" << (MLEvaluationV2::optimizedAvailable() ? "true" : "false") << ",\"backends\":[";
        const char* names[] = {"tail", "sparse", "active_list", "sparse_only", "active_list_only", "production"};
        for (int i = 0; i < 6; ++i) {
            if (i) std::cout << ',';
            std::cout << "{\"name\":\"" << names[i] << "\",\"exact_residual_matches\":" << exact[i]
                      << ",\"max_difference_cp\":" << maxima[i] << ",\"mean_difference_cp\":" << sums[i]/count
                      << ",\"integer_hybrid_changes\":" << integerChanges[i] << '}';
        }
        std::cout << "]}\n";
        for (int i = 0; i < 6; ++i) if (integerChanges[i] || exact[i] != count) return 1;
        return 0;
    }
    if (operation == "production-alpha") { std::cout << evaluator.getHybridAlpha() << '\n'; return 0; }
    if (operation == "hybrid-v2") evaluator.setHybridAlpha(1.0f); // Legacy parity operation.
    if (operation == "search-diagnostic-reference" || operation == "search-production-reference") {
        std::string fen;
        int root = 0;
        while (std::getline(std::cin, fen)) {
            Board board;
            if (!board.loadFEN(fen)) return 1;
            for (auto mode : {EvaluationMode::Classic, EvaluationMode::ML, EvaluationMode::Hybrid}) {
                Search search;
                if (operation == "search-diagnostic-reference")
                    search.setHybridAlpha(1.0f); // Match the preserved alpha-1 diagnostic executable.
                if (!search.setEvaluationMode(mode)) return 1;
                const auto result = search.findBestMove(board, 3);
                std::cout << root << ' ' << PositionEvaluator::modeName(mode) << ' ' << result.nodes << ' '
                          << result.score << ' ' << result.bestMove.toString() << '\n';
            }
            ++root;
        }
        return 0;
    }
    if (operation == "features" || operation == "predict" || operation == "classic" ||
        operation == "features-v2" || operation == "direct-v2" || operation == "residual-v2" || operation == "hybrid-v2" || operation == "hybrid-production") {
        std::cout << std::setprecision(9);
        std::string fen;
        while (std::getline(std::cin, fen)) {
            Board board;
            if (!board.loadFEN(fen)) { std::cerr << "invalid FEN\n"; return 1; }
            if (operation == "classic") {
                std::cout << Evaluation{}.evaluate(board) << '\n';
            } else if (operation == "features-v2") {
                for (float value : MLEvaluationV2::features(board)) std::cout << value << ' ';
                std::cout << '\n';
            } else if (operation == "direct-v2" || operation == "residual-v2" || operation == "hybrid-v2" || operation == "hybrid-production") {
                const bool residual = operation != "direct-v2";
                if (!(residual ? MLEvaluationV2::residualAvailable() : MLEvaluationV2::directAvailable())) return 1;
                if (operation == "hybrid-v2" || operation == "hybrid-production") std::cout << evaluator.evaluate(board, EvaluationMode::Hybrid) << '\n';
                else std::cout << MLEvaluationV2::predict(board, residual) << '\n';
            } else if (operation == "features") {
                for (float value : MLEvaluation::features(board)) std::cout << value << ' ';
                std::cout << '\n';
            } else {
                if (!MLEvaluation::available()) { std::cerr << "model unavailable\n"; return 1; }
                std::cout << MLEvaluation{}.evaluate(board) << '\n';
            }
        }
        return 0;
    }
    if (operation != "bench") { std::cerr << "Use features, predict, or bench [iterations]\n"; return 1; }
    int iterations = 20000;
    try { if (argc > 2) iterations = std::stoi(argv[2]); }
    catch (...) { return 1; }
    if (iterations < 1) return 1;
    const std::vector<std::string> fens = {
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1",
        "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNB1KBNR w KQkq - 0 1",
        "rnb1kbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR b KQkq - 0 1",
        "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1",
        "8/8/4k3/8/3P4/4K3/8/8 b - - 0 1"
    };
    std::vector<Board> boards;
    std::cout << "model " << PositionEvaluator::modelVersion() << '\n';
    for (const auto& fen : fens) {
        Board board;
        if (!board.loadFEN(fen)) return 1;
        boards.push_back(board);
        std::cout << "FEN " << fen << "\nclassic " << evaluator.evaluate(board, EvaluationMode::Classic);
        for (auto mode : {EvaluationMode::ML, EvaluationMode::Hybrid}) {
            std::cout << ' ' << PositionEvaluator::modeName(mode) << ' ';
            if (PositionEvaluator::available(mode)) std::cout << evaluator.evaluate(board, mode);
            else std::cout << "unavailable";
        }
        std::cout << '\n';
    }
    volatile long long checksum = 0;
    for (auto mode : {EvaluationMode::Classic, EvaluationMode::ML, EvaluationMode::Hybrid}) {
        if (!PositionEvaluator::available(mode)) continue;
        for (int i = 0; i < 1000; ++i) checksum += evaluator.evaluate(boards[i % boards.size()], mode);
        const auto start = std::chrono::steady_clock::now();
        for (int i = 0; i < iterations; ++i) checksum += evaluator.evaluate(boards[i % boards.size()], mode);
        const double seconds = std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
        std::cout << PositionEvaluator::modeName(mode) << " evaluations/second " << iterations / seconds << '\n';
    }
    std::cout << "checksum " << checksum << '\n';
}
