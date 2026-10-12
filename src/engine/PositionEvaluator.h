#pragma once
#include "Evaluation.h"
#include "MLEvaluation.h"
#include "MLEvaluationV2.h"

enum class EvaluationMode { Classic, ML, Hybrid };

struct EvaluationConfig
{
    // Frozen V2 candidate, validated on the separately versioned final suite.
    static constexpr float ProductionHybridAlpha = 0.25f;
    // Retain the original V1 blend for legacy builds.
    static constexpr float HybridMLWeight = 0.25f;
};

class PositionEvaluator
{
public:
    static EvaluationMode defaultMode();
    static bool available(EvaluationMode mode);
    static const char* modelVersion();
    static const char* modeName(EvaluationMode mode);
    bool setMode(EvaluationMode mode);
    bool setHybridAlpha(float alpha);
    float getHybridAlpha() const { return hybridAlpha; }
    EvaluationMode getMode() const { return mode; }
    int evaluate(const Board& board) const { return evaluate(board, mode); }
    int evaluate(const Board& board, EvaluationMode requested) const;
private:
    EvaluationMode mode = defaultMode();
    float hybridAlpha = EvaluationConfig::ProductionHybridAlpha;
};
