#pragma once

#include "../chess/Move.h"

#include <cstddef>
#include <cstdint>
#include <vector>

enum class TTFlag
{
    Exact,
    LowerBound,
    UpperBound
};

struct TTEntry
{
    uint64_t key = 0;

    int depth = -1;
    int score = 0;

    TTFlag flag = TTFlag::Exact;

    Move bestMove;
};

class TranspositionTable
{
public:
    explicit TranspositionTable(
        std::size_t entryCount = 1 << 18
    );

    bool probe(
        uint64_t key,
        TTEntry& result
    ) const;

    void store(
        uint64_t key,
        int depth,
        int score,
        TTFlag flag,
        const Move& bestMove
    );

    void clear();

private:
    std::vector<TTEntry> entries;
};