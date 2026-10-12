#include "Tournament.h"
#include <sstream>
#include <stdexcept>

namespace Tournament {
const char* suiteVersion(const std::string& suite) {
    if (suite == "final") return "final-openings-v1";
    if (suite == "development") return "common-openings-v1";
    if (suite == "heldout") return "heldout-openings-v1";
    throw std::invalid_argument("Unknown opening suite: " + suite);
}

// Frozen before held-out matches. Curated for opening-family coverage only;
// no evaluator scores or match outcomes were consulted. Never adapt to results.
const std::vector<Opening>& heldoutOpenings() {
    static const std::vector<Opening> suite = {
        {"Italian d3", {"e2e4","e7e5","g1f3","b8c6","f1c4","f8c5","d2d3","g8f6"}},
        {"Ruy Lopez Exchange", {"e2e4","e7e5","g1f3","b8c6","f1b5","a7a6","b5c6","d7c6"}},
        {"Four Knights", {"e2e4","e7e5","g1f3","b8c6","b1c3","g8f6","f1b5","f8b4"}},
        {"Scotch Classical", {"e2e4","e7e5","g1f3","b8c6","d2d4","e5d4","f3d4","f8c5","c1e3","d8f6"}},
        {"Vienna", {"e2e4","e7e5","b1c3","g8f6","f1c4","b8c6","d2d3","f8c5"}},
        {"Bishop's Opening", {"e2e4","e7e5","f1c4","g8f6","d2d3","c7c6","g1f3","d7d5"}},
        {"Closed Sicilian", {"e2e4","c7c5","b1c3","b8c6","g2g3","g7g6","f1g2","f8g7"}},
        {"Sicilian Alapin", {"e2e4","c7c5","c2c3","d7d5","e4d5","d8d5","d2d4","g8f6"}},
        {"Sicilian Kan", {"e2e4","c7c5","g1f3","e7e6","d2d4","c5d4","f3d4","a7a6","f1d3","b8c6"}},
        {"French Advance", {"e2e4","e7e6","d2d4","d7d5","e4e5","c7c5","c2c3","b8c6"}},
        {"French Exchange", {"e2e4","e7e6","d2d4","d7d5","e4d5","e6d5","g1f3","g8f6"}},
        {"French Tarrasch", {"e2e4","e7e6","d2d4","d7d5","b1d2","g8f6","e4e5","f6d7"}},
        {"Caro-Kann Advance", {"e2e4","c7c6","d2d4","d7d5","e4e5","c8f5","g1f3","e7e6"}},
        {"Caro-Kann Panov", {"e2e4","c7c6","d2d4","d7d5","e4d5","c6d5","c2c4","g8f6"}},
        {"Scandinavian Modern", {"e2e4","d7d5","e4d5","g8f6","d2d4","f6d5","g1f3","c8g4"}},
        {"Scandinavian Qd6", {"e2e4","d7d5","e4d5","d8d5","b1c3","d5d6","d2d4","g8f6"}},
        {"Queen's Gambit Exchange", {"d2d4","d7d5","c2c4","e7e6","b1c3","g8f6","c4d5","e6d5","c1g5","f8e7"}},
        {"Queen's Gambit Accepted", {"d2d4","d7d5","c2c4","d5c4","g1f3","g8f6","e2e3","e7e6"}},
        {"Queen's Gambit Tarrasch", {"d2d4","d7d5","c2c4","e7e6","b1c3","c7c5","c4d5","e6d5"}},
        {"Slav Exchange", {"d2d4","d7d5","c2c4","c7c6","c4d5","c6d5","b1c3","g8f6"}},
        {"Semi-Slav", {"d2d4","d7d5","c2c4","c7c6","g1f3","g8f6","b1c3","e7e6"}},
        {"King's Indian Fianchetto", {"d2d4","g8f6","c2c4","g7g6","g1f3","f8g7","g2g3","e8g8","f1g2","d7d6"}},
        {"King's Indian Classical", {"d2d4","g8f6","c2c4","g7g6","b1c3","f8g7","e2e4","d7d6","g1f3","e8g8"}},
        {"Queen's Indian Fianchetto", {"d2d4","g8f6","c2c4","e7e6","g1f3","b7b6","g2g3","c8b7"}},
        {"Nimzo-Indian Classical", {"d2d4","g8f6","c2c4","e7e6","b1c3","f8b4","d1c2","e8g8"}},
        {"Nimzo-Indian Rubinstein", {"d2d4","g8f6","c2c4","e7e6","b1c3","f8b4","e2e3","e8g8"}},
        {"English Symmetrical", {"c2c4","c7c5","b1c3","b8c6","g2g3","g7g6","f1g2","f8g7"}},
        {"English Four Knights", {"c2c4","e7e5","b1c3","g8f6","g1f3","b8c6","g2g3","f8b4"}},
        {"Reti c4", {"g1f3","d7d5","c2c4","e7e6","g2g3","g8f6","f1g2","f8e7"}},
        {"Catalan", {"d2d4","g8f6","c2c4","e7e6","g2g3","d7d5","f1g2","f8e7"}},
        {"Dutch", {"d2d4","f7f5","g2g3","g8f6","f1g2","e7e6","g1f3","f8e7"}},
        {"Modern Benoni", {"d2d4","g8f6","c2c4","c7c5","d4d5","e7e6","b1c3","e6d5"}}
    };
    return suite;
}

// Canonical piece layout, side, ordered castling rights, and literal EP square.
// Clocks are intentionally omitted. Used for overlap tests and report identity.
std::string normalizedFen(const Board& board) {
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
    return out.str();
}
}
