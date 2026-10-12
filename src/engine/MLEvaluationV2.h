#pragma once
#include "MLEvaluation.h"
#include "FeatureSchemaV2.h"

class MLEvaluationV2 {
public:
    static constexpr int InputSize = FeatureSchemaV2::InputSize;
    static std::array<float, InputSize> features(const Board& board);
    static bool directAvailable();
    static bool residualAvailable();
    static const char* modelVersion();
    static const char* directModelVersion();
    static const char* residualModelVersion();
    // Raw cp output. Residual is NOT clipped before addition to Classic.
    static float predict(const Board& board, bool residual);
    // Explicit verification paths; unsupported CPUs safely use the reference.
    enum class Backend { Reference, Tail, Sparse, ActiveList, SparseOnly, ActiveListOnly };
    static float predictResidual(const Board& board, Backend backend);
    static bool optimizedAvailable();
    static const char* residualBackendName();
};
