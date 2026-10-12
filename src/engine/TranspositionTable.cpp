#include "TranspositionTable.h"

#include <algorithm>

// ============================================================
// CONSTRUCTOR
// ============================================================

TranspositionTable::TranspositionTable(
    std::size_t entryCount
)
    : entries(entryCount)
{
}


// ============================================================
// LOOK UP POSITION
// ============================================================

bool TranspositionTable::probe(
    uint64_t key,
    TTEntry& result
) const
{
    if (entries.empty())
    {
        return false;
    }

    const std::size_t index =
        key % entries.size();

    const TTEntry& entry =
        entries[index];

    if (
        entry.depth >= 0 &&
        entry.key == key
    )
    {
        result = entry;

        return true;
    }

    return false;
}


// ============================================================
// STORE POSITION
// ============================================================

void TranspositionTable::store(
    uint64_t key,
    int depth,
    int score,
    TTFlag flag,
    const Move& bestMove
)
{
    if (entries.empty())
    {
        return;
    }

    const std::size_t index =
        key % entries.size();

    TTEntry& entry =
        entries[index];

    // Replace if:
    // - slot is empty
    // - hash collision
    // - new result was searched at least as deeply
    if (
        entry.depth < 0 ||
        entry.key != key ||
        depth >= entry.depth
    )
    {
        entry.key = key;
        entry.depth = depth;
        entry.score = score;
        entry.flag = flag;
        entry.bestMove = bestMove;
    }
}


// ============================================================
// CLEAR TABLE
// ============================================================

void TranspositionTable::clear()
{
    std::fill(
        entries.begin(),
        entries.end(),
        TTEntry{}
    );
}