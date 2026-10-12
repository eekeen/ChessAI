#include "chess/Board.h"
#include "chess/MoveGenerator.h"
#include <cstdint>
#include <iostream>
#include <vector>

uint64_t perft(const Board& board, int depth)
{
    if (depth == 0) return 1;
    const auto moves = MoveGenerator{}.generateLegalMoves(board);
    if (depth == 1) return moves.size();
    uint64_t nodes = 0;
    for (const auto& move : moves) {
        Board next = board;
        next.makeMove(move);
        nodes += perft(next, depth - 1);
    }
    return nodes;
}

int main()
{
    const std::vector<std::pair<const char*, std::vector<uint64_t>>> cases = {
        {"rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1", {20,400,8902,197281,4865609}},
        {"r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1", {48,2039,97862,4085603}}
    };
    for (const auto& item : cases) {
        Board board;
        if (!board.loadFEN(item.first)) return 1;
        for (int depth = 1; depth <= static_cast<int>(item.second.size()); ++depth) {
            const auto actual = perft(board, depth);
            std::cout << item.first << " depth " << depth << " nodes " << actual << std::endl;
            if (actual != item.second[depth - 1]) return 1;
        }
    }
}
