#include "MLEvaluationV2.h"
#include "V2Kernels.h"
#include <algorithm>
#include <limits>

#if __has_include("DirectWeightsV2.h")
#include "DirectWeightsV2.h"
#define HAS_DIRECT_V2 1
#else
#define HAS_DIRECT_V2 0
#endif
#if __has_include("ResidualWeightsV2.h")
#include "ResidualWeightsV2.h"
#define HAS_RESIDUAL_V2 1
#else
#define HAS_RESIDUAL_V2 0
#endif

std::array<float, MLEvaluationV2::InputSize> MLEvaluationV2::features(const Board& board) {
    const auto base = MLEvaluation::features(board);
    std::array<float, InputSize> result{};
    std::copy(base.begin(), base.end(), result.begin());
    std::array<int, 12> counts{};
    for (int plane = 0; plane < 12; ++plane)
        for (int square = 0; square < 64; ++square)
            counts[plane] += static_cast<int>(base[plane * 64 + square]);
    int index = FeatureSchemaV2::BaseSize;
    for (const auto& spec : FeatureSchemaV2::Scalars) {
        float value = 0;
        switch (spec.kind) {
            case 0: value = counts[spec.plane] / spec.scale; break;
            case 1:
                for (int i = 0; i < 6; ++i)
                    value += (counts[i] - counts[i + 6]) * FeatureSchemaV2::Material[i];
                value /= spec.scale; break;
            case 2:
                for (int i = 0; i < 6; ++i)
                    value += (counts[i] + counts[i + 6]) * FeatureSchemaV2::Phase[i];
                value = std::min(1.0f, value / spec.scale); break;
            case 3: value = counts[spec.plane] >= spec.threshold; break;
            case 4: value = base[spec.plane * 64 + spec.square1] + base[spec.plane * 64 + spec.square2] > 0; break;
        }
        result[index++] = value;
    }
    return result;
}

namespace {
// Frozen reference: retain original feature construction, operation order and fusion.
// Direct ML and portable fallback continue to use this implementation.
template<class Weights>
float forward(const Board& board) {
    static_assert(Weights::InputSize == MLEvaluationV2::InputSize && Weights::Hidden1 == 128 && Weights::Hidden2 == 64,
                  "Invalid V2 architecture");
    const auto input = MLEvaluationV2::features(board);
    std::array<float, 128> h1;
    std::copy_n(Weights::B1, 128, h1.begin());
    for (int i = 0; i < MLEvaluationV2::InputSize; ++i) {
        if (!input[i]) continue;
        for (int j = 0; j < 128; ++j) h1[j] += input[i] * Weights::W1[i * 128 + j];
    }
    for (auto& value : h1) value = std::max(0.0f, value);
    float output = Weights::B3[0];
    for (int i = 0; i < 64; ++i) {
        float value = Weights::B2[i];
        for (int j = 0; j < 128; ++j) value += h1[j] * Weights::W2[i * 128 + j];
        output += std::max(0.0f, value) * Weights::W3[i];
    }
    return output * Weights::TargetScale;
}
}

bool MLEvaluationV2::directAvailable() { return HAS_DIRECT_V2; }
bool MLEvaluationV2::residualAvailable() { return HAS_RESIDUAL_V2; }
const char* MLEvaluationV2::directModelVersion() {
#if HAS_DIRECT_V2
    return DirectWeightsV2::ModelVersion;
#else
    return "unavailable";
#endif
}
const char* MLEvaluationV2::residualModelVersion() {
#if HAS_RESIDUAL_V2
    return ResidualWeightsV2::ModelVersion;
#else
    return "unavailable";
#endif
}
const char* MLEvaluationV2::modelVersion() {
#if HAS_RESIDUAL_V2
    return ResidualWeightsV2::ModelVersion;
#elif HAS_DIRECT_V2
    return DirectWeightsV2::ModelVersion;
#else
    return "unavailable";
#endif
}
float MLEvaluationV2::predict(const Board& board, bool residual) {
    if (residual) {
#if HAS_RESIDUAL_V2
#if CHESSAI_V2_OPTIMIZATION == 3
        return predictResidual(board, Backend::ActiveList);
#elif CHESSAI_V2_OPTIMIZATION == 2
        return predictResidual(board, Backend::Sparse);
#elif CHESSAI_V2_OPTIMIZATION == 1
        return predictResidual(board, Backend::Tail);
#else
        return forward<ResidualWeightsV2>(board);
#endif
#endif
    } else {
#if HAS_DIRECT_V2
        return forward<DirectWeightsV2>(board);
#endif
    }
    return std::numeric_limits<float>::quiet_NaN();
}

bool MLEvaluationV2::optimizedAvailable() { return V2Kernels::available(); }
const char* MLEvaluationV2::residualBackendName() {
#if CHESSAI_V2_OPTIMIZATION == 3
    return V2Kernels::available() ? "avx2-tail-active-list" : "reference";
#elif CHESSAI_V2_OPTIMIZATION == 2
    return V2Kernels::available() ? "avx2-tail-sparse" : "reference";
#elif CHESSAI_V2_OPTIMIZATION == 1
    return V2Kernels::available() ? "avx2-tail" : "reference";
#else
    return "reference";
#endif
}
float MLEvaluationV2::predictResidual(const Board& board, Backend backend) {
#if HAS_RESIDUAL_V2
    if (backend == Backend::Reference || !V2Kernels::available()) return forward<ResidualWeightsV2>(board);
    const auto input = features(board);
    std::array<float, 128> h1;
    if (backend == Backend::Tail) {
        std::copy_n(ResidualWeightsV2::B1, 128, h1.begin());
        for (int i = 0; i < InputSize; ++i) {
            if (!input[i]) continue;
            for (int j = 0; j < 128; ++j) h1[j] += input[i] * ResidualWeightsV2::W1[i * 128 + j];
        }
    } else V2Kernels::linear1(input.data(), h1.data(), backend == Backend::ActiveList || backend == Backend::ActiveListOnly);
    for (auto& value : h1) value = std::max(0.0f, value);
    if (backend == Backend::SparseOnly || backend == Backend::ActiveListOnly) {
        // Verification/measurement ablation: original tail with only Linear1 replaced.
        float output = ResidualWeightsV2::B3[0];
        for (int i = 0; i < 64; ++i) {
            float value = ResidualWeightsV2::B2[i];
            for (int j = 0; j < 128; ++j) value += h1[j] * ResidualWeightsV2::W2[i * 128 + j];
            output += std::max(0.0f, value) * ResidualWeightsV2::W3[i];
        }
        return output * ResidualWeightsV2::TargetScale;
    }
    return V2Kernels::tail(h1.data());
#else
    return std::numeric_limits<float>::quiet_NaN();
#endif
}
