#pragma once
// Internal kernels; public wrappers always check CPU/OS support before dispatch.
namespace V2Kernels {
bool available();
void linear1(const float* input, float* hidden, bool activeList = false);
float tail(const float* hidden);
// Only called by the checked wrappers, never during static initialization.
void avxLinear1(const float*, float*, const float*, const float*, bool);
float avxTail(const float*, const float*, const float*, const float*, float, float);
}
