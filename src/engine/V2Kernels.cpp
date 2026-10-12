#include "V2Kernels.h"
#include <algorithm>
#include <limits>
#if defined(CHESSAI_V2_AVX2) && defined(_MSC_VER)
#include <intrin.h>
#endif
#if __has_include("ResidualWeightsV2.h")
#include "ResidualWeightsV2.h"
#define HAS_RESIDUAL_KERNEL 1
#endif
namespace V2Kernels {
bool available() {
    static const bool supported = [] {
#if defined(CHESSAI_V2_AVX2) && defined(HAS_RESIDUAL_KERNEL) && defined(_MSC_VER)
        int r[4]; __cpuid(r, 0);
        if (r[0] < 7) return false;
        __cpuid(r, 1);
        if (!(r[2] & (1 << 28)) || !(r[2] & (1 << 27))) return false;
        if ((_xgetbv(0) & 6) != 6) return false;
        __cpuidex(r, 7, 0);
        return (r[1] & (1 << 5)) != 0;
#else
        return false;
#endif
    }();
    return supported;
}
#ifdef HAS_RESIDUAL_KERNEL
using W = ResidualWeightsV2;
#endif
void linear1(const float* input, float* hidden, bool activeList) {
#ifdef HAS_RESIDUAL_KERNEL
#ifdef CHESSAI_V2_AVX2
    if (available()) { avxLinear1(input, hidden, W::W1, W::B1, activeList); return; }
#endif
    std::copy_n(W::B1, 128, hidden);
    for (int i = 0; i < 789; ++i) {
        if (!input[i]) continue;
        for (int j = 0; j < 128; ++j) hidden[j] += input[i] * W::W1[i * 128 + j];
    }
#endif
}
float tail(const float* hidden) {
#ifdef HAS_RESIDUAL_KERNEL
#ifdef CHESSAI_V2_AVX2
    if (available()) {
        struct Packed {
            alignas(32) float values[8192];
            Packed() {
                for (int block = 0; block < 8; ++block)
                    for (int j = 0; j < 128; ++j)
                        for (int lane = 0; lane < 8; ++lane)
                            values[block * 1024 + j * 8 + lane] = W::W2[(block * 8 + lane) * 128 + j];
            }
        };
        // Thread-safe, once-only exact copies; initialization uses baseline ISA.
        static const Packed packed;
        return avxTail(hidden, packed.values, W::B2, W::W3, W::B3[0], W::TargetScale);
    }
#endif
    float output = W::B3[0];
    for (int i = 0; i < 64; ++i) {
        float value = W::B2[i];
        for (int j = 0; j < 128; ++j) value += hidden[j] * W::W2[i * 128 + j];
        output += std::max(0.0f, value) * W::W3[i];
    }
    return output * W::TargetScale;
#else
    return std::numeric_limits<float>::quiet_NaN();
#endif
}
}
