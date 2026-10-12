#pragma once
#include "engine/PositionEvaluator.h"
#include <array>
namespace HybridProfile {
struct State {
    Board board;
    PositionEvaluator evaluator;
    std::array<float, 789> input{};
    std::array<float, 128> h1{}, a1{};
    std::array<float, 64> h2{}, a2{};
    std::array<float, 773> base{};
    std::array<int, 12> counts{};
    std::array<int, 789> activeIndices{};
    int activeCount = 0;
    int classic = 0, score = 0;
    float output = 0, residual = 0, combined = 0;
};
using Operation = void(*)(State&);
void empty(State&);
void classic(State&);
void features(State&);
void linear1(State&);
void relu1(State&);
void linear2(State&);
void relu2(State&);
void output(State&);
void scaleAdd(State&);
void clipRound(State&);
void decomposed(State&);
void production(State&);
void fusedTail(State&);
void noSkipLinear1(State&);
void baseFeatures(State&);
void featureCopySetup(State&);
void planeCounts(State&);
void optimizedTail(State&);
void optimizedLinear1(State&);
void activeListLinear1(State&);
void constructActiveList(State&);
void referenceTotal(State&);
void tailTotal(State&);
void sparseTotal(State&);
void activeTotal(State&);
void sparseOnlyTotal(State&);
void activeOnlyTotal(State&);
}
