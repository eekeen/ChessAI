#include "PositionEvaluator.h"
#include <algorithm>
#include <cmath>

static_assert(EvaluationConfig::HybridMLWeight >= 0.0f &&
              EvaluationConfig::HybridMLWeight <= 1.0f, "Hybrid weight must be in [0,1]");

EvaluationMode PositionEvaluator::defaultMode()
{
    return available(EvaluationMode::Hybrid) ? EvaluationMode::Hybrid : EvaluationMode::Classic;
}

bool PositionEvaluator::available(EvaluationMode mode) {
    if (mode == EvaluationMode::Classic) return true;
    if (mode == EvaluationMode::ML) return MLEvaluationV2::directAvailable() || MLEvaluation::available();
    return MLEvaluationV2::residualAvailable() || MLEvaluation::available();
}

const char* PositionEvaluator::modelVersion() {
    return MLEvaluationV2::directAvailable() || MLEvaluationV2::residualAvailable()
        ? MLEvaluationV2::modelVersion() : MLEvaluation::modelVersion();
}

const char* PositionEvaluator::modeName(EvaluationMode mode)
{
    switch (mode) {
        case EvaluationMode::ML: return "ml";
        case EvaluationMode::Hybrid: return "hybrid";
        default: return "classic";
    }
}

bool PositionEvaluator::setMode(EvaluationMode requested)
{
    if (!available(requested)) return false;
    mode = requested;
    return true;
}

bool PositionEvaluator::setHybridAlpha(float alpha) {
    if (!std::isfinite(alpha) || alpha < 0.0f || alpha > 1.0f) return false;
    hybridAlpha = alpha;
    return true;
}

int PositionEvaluator::evaluate(const Board& board, EvaluationMode requested) const
{
    // Alpha zero is EXACT Classic, including scores beyond the ML clip boundary.
    if (requested == EvaluationMode::Hybrid && hybridAlpha == 0.0f)
        return Evaluation{}.evaluate(board);
    if (requested == EvaluationMode::Classic || !available(requested))
        return Evaluation{}.evaluate(board);
    if ((requested == EvaluationMode::ML && MLEvaluationV2::directAvailable()) ||
        (requested == EvaluationMode::Hybrid && MLEvaluationV2::residualAvailable())) {
        const bool residual = requested == EvaluationMode::Hybrid;
        float score = MLEvaluationV2::predict(board, residual);
        if (residual) score = hybridAlpha * score + Evaluation{}.evaluate(board);
        if (!std::isfinite(score)) return Evaluation{}.evaluate(board);
        // Clip the final position score, never the correction before adding Classic.
        return static_cast<int>(std::lround(std::clamp(score, -1500.0f, 1500.0f)));
    }
    const int learned = MLEvaluation{}.evaluate(board);
    if (requested == EvaluationMode::ML) return learned;
    const float weight = EvaluationConfig::HybridMLWeight;
    const int mixed = static_cast<int>(std::lround(
        weight * learned + (1.0f - weight) * Evaluation{}.evaluate(board)));
    // Well below Search's +/-100000 mate band, even on unusual debug boards.
    return std::clamp(mixed, -30000, 30000);
}
