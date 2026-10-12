#pragma once
#include "../chess/Board.h"
#include <array>

class MLEvaluation
{
public:
    static constexpr int InputSize = 773;
    static std::array<float, InputSize> features(const Board& board);
    static bool available();
    static const char* modelVersion();
    // White-relative cp, bounded to +/-1500. Classic fallback if unavailable.
    int evaluate(const Board& board) const;
};
