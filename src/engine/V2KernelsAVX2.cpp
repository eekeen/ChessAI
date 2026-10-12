// Separate ISA boundary: no global constructors, no FMA, no horizontal reduction.
#include "V2Kernels.h"
#include <immintrin.h>
#include <algorithm>

namespace V2Kernels {
void avxLinear1(const float* input, float* hidden, const float* weights, const float* bias, bool activeList) {
    std::copy_n(bias, 128, hidden);
    int indices[789];
    int count = 0;
    if (activeList) {
        for (int i = 0; i < 789; ++i) if (input[i]) indices[count++] = i;
    }
    for (int k = 0; k < (activeList ? count : 789); ++k) {
        const int i = activeList ? indices[k] : k;
        if (!activeList && !input[i]) continue;
        const auto value = _mm256_set1_ps(input[i]);
        for (int j = 0; j < 128; j += 8) {
            const auto product = _mm256_mul_ps(value, _mm256_loadu_ps(weights + i * 128 + j));
            _mm256_storeu_ps(hidden + j, _mm256_add_ps(_mm256_loadu_ps(hidden + j), product));
        }
    }
}
float avxTail(const float* hidden, const float* packed, const float* bias,
              const float* outputWeights, float output, float scale) {
    for (int block = 0; block < 8; ++block) {
        auto values = _mm256_loadu_ps(bias + block * 8);
        for (int j = 0; j < 128; ++j) {
            const auto product = _mm256_mul_ps(_mm256_set1_ps(hidden[j]),
                                              _mm256_load_ps(packed + block * 1024 + j * 8));
            values = _mm256_add_ps(values, product);
        }
        alignas(32) float lanes[8];
        _mm256_store_ps(lanes, values);
        // Preserve the reference's scalar output summation order exactly.
        for (int lane = 0; lane < 8; ++lane)
            output += std::max(0.0f, lanes[lane]) * outputWeights[block * 8 + lane];
    }
    return output * scale;
}
}
