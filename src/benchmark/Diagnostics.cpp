#include "engine/Search.h"
#include <algorithm>
#include <array>
#include <iomanip>
#include <iostream>
#include <random>
#include <sstream>
#include <stdexcept>

static std::string fen(const Board& board) {
    const std::string pieces = " PNBRQK";
    std::ostringstream out;
    for (int rank = 7; rank >= 0; --rank) {
        int empty = 0;
        for (int file = 0; file < 8; ++file) {
            const auto piece = board.getPiece(rank * 8 + file);
            if (piece.isEmpty()) { ++empty; continue; }
            if (empty) { out << empty; empty = 0; }
            char c = pieces[static_cast<int>(piece.type)];
            if (piece.color == Color::Black) c += 'a' - 'A';
            out << c;
        }
        if (empty) out << empty;
        if (rank) out << '/';
    }
    out << (board.getSideToMove() == Color::White ? " w " : " b ");
    std::string rights;
    if (board.canCastleKingside(Color::White)) rights += 'K';
    if (board.canCastleQueenside(Color::White)) rights += 'Q';
    if (board.canCastleKingside(Color::Black)) rights += 'k';
    if (board.canCastleQueenside(Color::Black)) rights += 'q';
    out << (rights.empty() ? "-" : rights) << ' ';
    const int ep = board.getEnPassantSquare();
    if (ep < 0) out << '-';
    else out << char('a' + ep % 8) << char('1' + ep / 8);
    out << ' ' << board.getHalfmoveClock() << ' ' << board.getFullmoveNumber();
    return out.str();
}

static void scores(const Board& board) {
    const int classic = Evaluation{}.evaluate(board);
    const float direct = MLEvaluationV2::predict(board, false);
    const float residual = MLEvaluationV2::predict(board, true);
    const float hybrid = classic + residual;
    PositionEvaluator evaluator;
    evaluator.setHybridAlpha(1.0f); // Preserve the original raw-residual diagnostic protocol.
    std::cout << "\"fen\":\"" << fen(board) << "\",\"side\":\"" << (board.getSideToMove() == Color::White ? "w" : "b")
              << "\",\"classic\":" << classic << ",\"direct_raw\":" << direct << ",\"residual_raw\":" << residual
              << ",\"hybrid_raw\":" << hybrid << ",\"ml\":" << evaluator.evaluate(board, EvaluationMode::ML)
              << ",\"hybrid\":" << evaluator.evaluate(board, EvaluationMode::Hybrid);
}

struct Leaf { Board board; int ply, incoming, root; };
struct Reservoir {
    std::vector<Leaf> leaves;
    uint64_t seen = 0;
    std::mt19937_64 rng;
    Reservoir(unsigned seed) : rng(seed) {}
    void add(const Board& board, int ply, int incoming, int root, size_t capacity) {
        ++seen;
        size_t slot = leaves.size();
        if (slot >= capacity) slot = static_cast<size_t>(std::uniform_int_distribution<uint64_t>(0, seen - 1)(rng));
        if (slot >= capacity) return;
        if (slot == leaves.size()) leaves.push_back({board, ply, incoming, root});
        else leaves[slot] = {board, ply, incoming, root};
    }
};

int main(int argc, char** argv) {
    try {
        bool children = false;
        int leafRoots = 0, leafSamples = 1000, depth = 3;
        unsigned seed = 42;
        for (int i = 1; i < argc; ++i) {
            const std::string option = argv[i];
            if (option == "--children") { children = true; continue; }
            if (++i == argc) throw std::invalid_argument("Missing option value");
            size_t parsed = 0;
            const int value = std::stoi(argv[i], &parsed);
            if (parsed != std::string(argv[i]).size()) throw std::invalid_argument("Invalid numeric option");
            if (value < 0) throw std::invalid_argument("Negative option value");
            if (option == "--leaf-roots") leafRoots = value;
            else if (option == "--leaf-samples") leafSamples = value;
            else if (option == "--depth") depth = value;
            else if (option == "--seed") seed = static_cast<unsigned>(value);
            else throw std::invalid_argument("Unknown option " + option);
        }
        if (depth < 1 || depth > 64 || leafSamples < 1) throw std::invalid_argument("Invalid depth/sample count");
        if (!MLEvaluationV2::directAvailable() || !MLEvaluationV2::residualAvailable())
            throw std::runtime_error("Both V2 models are required for diagnostics");
        std::cout << std::setprecision(9);
        std::cout << "{\"type\":\"models\",\"ml\":\"" << MLEvaluationV2::directModelVersion()
                  << "\",\"hybrid\":\"" << MLEvaluationV2::residualModelVersion() << "\"}\n";
        std::array<Reservoir, 3> reservoirs = {Reservoir(seed), Reservoir(seed + 1), Reservoir(seed + 2)};
        for (auto& reservoir : reservoirs) reservoir.leaves.reserve(leafSamples);
        const std::array<EvaluationMode, 3> modes = {EvaluationMode::Classic, EvaluationMode::ML, EvaluationMode::Hybrid};
        int root = 0;
        std::string line;
        while (std::getline(std::cin, line)) {
            Board board;
            if (!board.loadFEN(line)) throw std::invalid_argument("Invalid input FEN at row " + std::to_string(root));
            std::cout << "{\"type\":\"parent\",\"id\":" << root << ",\"parent\":{";
            scores(board);
            std::cout << "},\"children\":[";
            if (children) {
                bool first = true;
                for (const auto& move : MoveGenerator{}.generateLegalMoves(board)) {
                    if (!first) std::cout << ',';
                    first = false;
                    Board child = board;
                    child.makeMove(move);
                    const bool capture = move.getFlag() == MoveFlag::EnPassant || !board.getPiece(move.getTo()).isEmpty();
                    std::cout << "{\"move\":\"" << move.toString() << "\",\"capture\":" << (capture ? "true" : "false")
                              << ",\"promotion\":" << (move.getFlag() == MoveFlag::Promotion ? "true" : "false") << ',';
                    scores(child);
                    std::cout << '}';
                }
            }
            std::cout << "]}\n";
            if (root < leafRoots) {
                for (size_t i = 0; i < modes.size(); ++i) {
                    Search search;
                    search.setHybridAlpha(1.0f);
                    search.setEvaluationMode(modes[i]);
                    search.setLeafObserver([&](const Board& leaf, int ply, int incoming) {
                        reservoirs[i].add(leaf, ply, incoming, root, static_cast<size_t>(leafSamples));
                    });
                    const auto result = search.findBestMove(board, depth);
                    std::cout << "{\"type\":\"search\",\"root\":" << root << ",\"mode\":\"" << PositionEvaluator::modeName(modes[i])
                              << "\",\"depth\":" << result.depthReached << ",\"nodes\":" << result.nodes << ",\"bestmove\":\""
                              << result.bestMove.toString() << "\",\"score\":" << result.score << "}\n";
                }
            }
            ++root;
        }
        for (size_t i = 0; i < modes.size(); ++i) {
            std::cout << "{\"type\":\"leaf_summary\",\"mode\":\"" << PositionEvaluator::modeName(modes[i])
                      << "\",\"events_seen\":" << reservoirs[i].seen << ",\"selected\":" << reservoirs[i].leaves.size() << "}\n";
            for (const auto& leaf : reservoirs[i].leaves) {
                std::cout << "{\"type\":\"leaf\",\"search_mode\":\"" << PositionEvaluator::modeName(modes[i])
                          << "\",\"root\":" << leaf.root << ",\"ply\":" << leaf.ply << ",\"incoming\":" << leaf.incoming << ',';
                scores(leaf.board);
                std::cout << "}\n";
            }
        }
    } catch (const std::exception& error) { std::cerr << error.what() << '\n'; return 1; }
}
