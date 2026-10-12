#include "MLEvaluation.h"
#include "Evaluation.h"
#include <algorithm>
#include <cmath>

#if defined(CHESSAI_ML_WEIGHTS_HEADER)
#include CHESSAI_ML_WEIGHTS_HEADER
#define CHESSAI_HAS_ML 1
#elif __has_include("generated/MLWeights.h")
#include "generated/MLWeights.h"
#define CHESSAI_HAS_ML 1
#else
#define CHESSAI_HAS_ML 0
#endif

#if CHESSAI_HAS_ML
static_assert(MLWeights::FeatureVersion == 1 && MLWeights::InputSize == 773 &&
              MLWeights::Hidden1 == 128 && MLWeights::Hidden2 == 64,
              "Unsupported ML model contract");
static_assert(MLWeights::TargetScale == 1000.0f && MLWeights::ClipCp == 1500.0f,
              "Unsupported ML score scale");
#endif

std::array<float, MLEvaluation::InputSize> MLEvaluation::features(const Board& board)
{
    std::array<float, InputSize> result{};
    for (int square = 0; square < 64; ++square)
    {
        const Piece piece = board.getPiece(square);
        if (piece.isEmpty()) continue;
        const int plane = static_cast<int>(piece.type) - 1 +
            (piece.color == Color::Black ? 6 : 0);
        result[plane * 64 + square] = 1.0f;
    }
    result[768] = board.getSideToMove() == Color::White ? 1.0f : -1.0f;
    result[769] = board.canCastleKingside(Color::White);
    result[770] = board.canCastleQueenside(Color::White);
    result[771] = board.canCastleKingside(Color::Black);
    result[772] = board.canCastleQueenside(Color::Black);
    return result;
}

bool MLEvaluation::available() { return CHESSAI_HAS_ML != 0; }

const char* MLEvaluation::modelVersion()
{
#if CHESSAI_HAS_ML
    return MLWeights::ModelVersion;
#else
    return "unavailable";
#endif
}

int MLEvaluation::evaluate(const Board& board) const
{
#if CHESSAI_HAS_ML
    const auto input = features(board);
    std::array<float, 128> h1;
    std::copy_n(MLWeights::B1, 128, h1.begin());
    // Sparse input: only occupied squares, turn and enabled rights contribute.
    for (int i = 0; i < InputSize; ++i)
    {
        if (input[i] == 0.0f) continue;
        for (int j = 0; j < 128; ++j)
            h1[j] += input[i] * MLWeights::W1[i * 128 + j];
    }
    for (float& value : h1) value = std::max(0.0f, value);
    std::array<float, 64> h2;
    for (int i = 0; i < 64; ++i)
    {
        float value = MLWeights::B2[i];
        for (int j = 0; j < 128; ++j)
            value += MLWeights::W2[i * 128 + j] * h1[j];
        h2[i] = std::max(0.0f, value);
    }
    float cp = MLWeights::B3[0];
    for (int i = 0; i < 64; ++i) cp += MLWeights::W3[i] * h2[i];
    cp *= MLWeights::TargetScale;
    if (!std::isfinite(cp)) return Evaluation{}.evaluate(board);
    return static_cast<int>(std::lround(std::clamp(cp, -MLWeights::ClipCp, MLWeights::ClipCp)));
#else
    return Evaluation{}.evaluate(board);
#endif
}
