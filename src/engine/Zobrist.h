#pragma once

#include "../chess/Board.h"

#include <cstdint>

namespace Zobrist
{
    uint64_t hash(const Board& board);
}