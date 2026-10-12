// Profiling-only decomposition. Never linked into the production engine.
// Splitting the fused tail deliberately exposes timing boundaries, not an optimization.
#include "HybridProfileStages.h"
#include "ResidualWeightsV2.h"
#include "engine/V2Kernels.h"
#include <algorithm>
#include <cmath>
#ifdef _MSC_VER
#define PROFILE_NOINLINE __declspec(noinline)
#else
#define PROFILE_NOINLINE __attribute__((noinline))
#endif
namespace HybridProfile {
using W = ResidualWeightsV2;
PROFILE_NOINLINE void optimizedTail(State& s) { s.residual = V2Kernels::tail(s.a1.data()); }
PROFILE_NOINLINE void optimizedLinear1(State& s) { V2Kernels::linear1(s.input.data(), s.h1.data()); }
PROFILE_NOINLINE void activeListLinear1(State& s) { V2Kernels::linear1(s.input.data(), s.h1.data(), true); }
PROFILE_NOINLINE void constructActiveList(State& s) {
    s.activeCount = 0;
    for (int i = 0; i < 789; ++i) if (s.input[i]) s.activeIndices[s.activeCount++] = i;
}
template<MLEvaluationV2::Backend backend> void candidateTotal(State& s) {
    const float residual = MLEvaluationV2::predictResidual(s.board, backend);
    const int handcrafted = Evaluation{}.evaluate(s.board);
    const float combined = EvaluationConfig::ProductionHybridAlpha * residual + handcrafted;
    s.score = std::isfinite(combined) ? static_cast<int>(std::lround(std::clamp(combined, -1500.0f, 1500.0f))) : handcrafted;
}
PROFILE_NOINLINE void referenceTotal(State& s) { candidateTotal<MLEvaluationV2::Backend::Reference>(s); }
PROFILE_NOINLINE void tailTotal(State& s) { candidateTotal<MLEvaluationV2::Backend::Tail>(s); }
PROFILE_NOINLINE void sparseTotal(State& s) { candidateTotal<MLEvaluationV2::Backend::Sparse>(s); }
PROFILE_NOINLINE void activeTotal(State& s) { candidateTotal<MLEvaluationV2::Backend::ActiveList>(s); }
PROFILE_NOINLINE void sparseOnlyTotal(State& s) { candidateTotal<MLEvaluationV2::Backend::SparseOnly>(s); }
PROFILE_NOINLINE void activeOnlyTotal(State& s) { candidateTotal<MLEvaluationV2::Backend::ActiveListOnly>(s); }
PROFILE_NOINLINE void empty(State&) {}
PROFILE_NOINLINE void classic(State& s) { s.classic = Evaluation{}.evaluate(s.board); }
PROFILE_NOINLINE void features(State& s) { s.input = MLEvaluationV2::features(s.board); }
PROFILE_NOINLINE void linear1(State& s) {
    std::copy_n(W::B1, 128, s.h1.begin());
    for (int i = 0; i < 789; ++i) {
        if (!s.input[i]) continue;
        for (int j = 0; j < 128; ++j) s.h1[j] += s.input[i] * W::W1[i * 128 + j];
    }
}
PROFILE_NOINLINE void relu1(State& s) {
    for (int i = 0; i < 128; ++i) s.a1[i] = std::max(0.0f, s.h1[i]);
}
PROFILE_NOINLINE void linear2(State& s) {
    for (int i = 0; i < 64; ++i) {
        float value = W::B2[i];
        for (int j = 0; j < 128; ++j) value += s.a1[j] * W::W2[i * 128 + j];
        s.h2[i] = value;
    }
}
PROFILE_NOINLINE void relu2(State& s) {
    for (int i = 0; i < 64; ++i) s.a2[i] = std::max(0.0f, s.h2[i]);
}
PROFILE_NOINLINE void output(State& s) {
    float value = W::B3[0];
    for (int i = 0; i < 64; ++i) value += s.a2[i] * W::W3[i];
    s.output = value;
}
PROFILE_NOINLINE void scaleAdd(State& s) {
    s.residual = s.output * W::TargetScale;
    s.combined = EvaluationConfig::ProductionHybridAlpha * s.residual + s.classic;
}
PROFILE_NOINLINE void clipRound(State& s) {
    s.score = std::isfinite(s.combined)
        ? static_cast<int>(std::lround(std::clamp(s.combined, -1500.0f, 1500.0f)))
        : Evaluation{}.evaluate(s.board);
}
PROFILE_NOINLINE void decomposed(State& s) {
    features(s); linear1(s); relu1(s); linear2(s); relu2(s); output(s);
    classic(s); scaleAdd(s); clipRound(s);
}
PROFILE_NOINLINE void production(State& s) { s.score = s.evaluator.evaluate(s.board, EvaluationMode::Hybrid); }
PROFILE_NOINLINE void fusedTail(State& s) {
    // Exactly the current production fused tail, including TargetScale.
    float value = W::B3[0];
    for (int i = 0; i < 64; ++i) {
        float hidden = W::B2[i];
        for (int j = 0; j < 128; ++j) hidden += s.a1[j] * W::W2[i * 128 + j];
        value += std::max(0.0f, hidden) * W::W3[i];
    }
    s.residual = value * W::TargetScale;
}
PROFILE_NOINLINE void noSkipLinear1(State& s) {
    // Slower control, never a deployed alternative. Measures the value of skipping zeros.
    std::copy_n(W::B1, 128, s.h1.begin());
    for (int i = 0; i < 789; ++i)
        for (int j = 0; j < 128; ++j) s.h1[j] += s.input[i] * W::W1[i * 128 + j];
}
PROFILE_NOINLINE void baseFeatures(State& s) { s.base = MLEvaluation::features(s.board); }
PROFILE_NOINLINE void featureCopySetup(State& s) {
    s.input.fill(0.0f);
    std::copy(s.base.begin(), s.base.end(), s.input.begin());
}
PROFILE_NOINLINE void planeCounts(State& s) {
    s.counts.fill(0);
    for (int plane = 0; plane < 12; ++plane)
        for (int square = 0; square < 64; ++square)
            s.counts[plane] += static_cast<int>(s.base[plane * 64 + square]);
}
}
