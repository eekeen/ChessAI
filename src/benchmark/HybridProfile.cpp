#include "HybridProfileStages.h"
#include "chess/MoveGenerator.h"
#include <algorithm>
#include <chrono>
#include <cstring>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <vector>
#ifdef _MSC_VER
#include <intrin.h>
#endif
using namespace HybridProfile;
struct Task { const char* name; Operation operation; };
// steady_clock on this Windows host ticks at 0.1 us. A 20-call empty batch
// can fit between two ticks even with floating-point duration conversion.
// Retime progressively larger real batches; never clamp or fabricate durations.
static constexpr double MinimumBatchMicroseconds = 100.0;
struct TimedBatch { int iterations; double elapsedUs; int attempts; };
static TimedBatch timeBatch(Operation operation, State& state, int requestedIterations) {
    int count = requestedIterations;
    for (int attempt = 1; ; ++attempt) {
        const auto start = std::chrono::steady_clock::now();
        for (int i = 0; i < count; ++i) operation(state);
        const auto end = std::chrono::steady_clock::now();
        const double elapsedUs = std::chrono::duration<double, std::micro>(end - start).count();
        if (elapsedUs >= MinimumBatchMicroseconds) return {count, elapsedUs, attempt};
        if (count > std::numeric_limits<int>::max() / 2)
            throw std::runtime_error("Unable to obtain a sufficiently long real timing batch");
        count *= 2;
    }
}
const std::vector<Task> tasks = {
    {"classic", classic}, {"features", features}, {"linear1", linear1}, {"relu1", relu1},
    {"linear2", linear2}, {"relu2", relu2}, {"output", output}, {"scale_add", scaleAdd}, {"clip_round", clipRound},
    {"empty_control", empty}, {"production_total", production}, {"decomposed_total", decomposed},
    {"fused_tail_control", fusedTail}, {"linear1_no_skip_control", noSkipLinear1},
    {"base_features_control", baseFeatures}, {"feature_copy_setup_control", featureCopySetup}, {"plane_counts_control", planeCounts},
    {"optimized_tail_control", optimizedTail}, {"optimized_linear1_control", optimizedLinear1}, {"active_list_linear1_control", activeListLinear1}
};
const std::vector<Task> candidateTasks = {
    {"empty_control", empty}, {"production_total", production},
    {"reference_total", referenceTotal}, {"tail_total", tailTotal},
    {"sparse_total", sparseTotal}, {"active_total", activeTotal},
    {"sparse_only_total", sparseOnlyTotal}, {"active_only_total", activeOnlyTotal},
    {"linear1", linear1}, {"optimized_linear1_control", optimizedLinear1},
    {"active_list_linear1_control", activeListLinear1}, {"list_construction_control", constructActiveList},
    {"fused_tail_control", fusedTail}, {"optimized_tail_control", optimizedTail}, {"features", features}
};
static void verify(State& s) {
    decomposed(s);
    const float reference = MLEvaluationV2::predict(s.board, true);
    if (std::memcmp(&reference, &s.residual, sizeof(float)) != 0 ||
        s.score != PositionEvaluator{}.evaluate(s.board, EvaluationMode::Hybrid))
        throw std::runtime_error("Decomposition is not bit-exact with production");
    const auto h1 = s.h1;
    noSkipLinear1(s);
    if (std::memcmp(h1.data(), s.h1.data(), sizeof(h1))) throw std::runtime_error("No-skip control parity failed");
    fusedTail(s);
    if (std::memcmp(&reference, &s.residual, sizeof(float))) throw std::runtime_error("Fused control parity failed");
    optimizedTail(s);
    if (std::memcmp(&reference, &s.residual, sizeof(float))) throw std::runtime_error("Optimized tail parity failed");
    optimizedLinear1(s);
    if (std::memcmp(h1.data(), s.h1.data(), sizeof(h1))) throw std::runtime_error("Optimized Linear1 parity failed");
    activeListLinear1(s);
    if (std::memcmp(h1.data(), s.h1.data(), sizeof(h1))) throw std::runtime_error("Active-list Linear1 parity failed");
}
static int positive(const std::string& text) {
    size_t used;
    const int n = std::stoi(text, &used);
    if (n < 1 || used != text.size()) throw std::invalid_argument("Positive integer required");
    return n;
}
int main(int argc, char** argv) {
    try {
#ifndef NDEBUG
        throw std::runtime_error("Profiling requires Release build");
#endif
        int iterations = 50000, repeats = 5, warmup = 2000;
        std::string manifest = "benchmarks/performance-middlegames-v1.tsv";
        bool verifyOnly = false, compareCandidates = false;
        for (int i = 1; i < argc; ++i) {
            const std::string option = argv[i];
            if (option == "--verify-only") { verifyOnly = true; continue; }
            if (option == "--compare-candidates") { compareCandidates = true; continue; }
            if (++i == argc) throw std::invalid_argument("Missing argument");
            if (option == "--positions") manifest = argv[i];
            else if (option == "--iterations") iterations = positive(argv[i]);
            else if (option == "--repetitions") repeats = positive(argv[i]);
            else if (option == "--warmup") warmup = positive(argv[i]);
            else throw std::invalid_argument("Unknown option");
        }
        if (!MLEvaluationV2::residualAvailable() || EvaluationConfig::ProductionHybridAlpha != .25f)
            throw std::runtime_error("Expected production V2 Hybrid alpha 0.25");
        std::ifstream file(manifest); std::string line;
        if (!std::getline(file, line)) throw std::runtime_error("Cannot read manifest");
        std::vector<State> states;
        std::vector<std::string> ids;
        size_t parityCount = 0;
        while (std::getline(file, line)) {
            if (!line.empty() && line.back() == '\r') line.pop_back();
            if (line.empty()) continue;
            const auto tab = line.find('\t');
            State state;
            if (tab == std::string::npos || !state.board.loadFEN(line.substr(tab + 1))) throw std::runtime_error("Invalid manifest");
            const auto legal = MoveGenerator{}.generateLegalMoves(state.board);
            if (legal.empty()) throw std::runtime_error("Terminal benchmark position");
            verify(state); ++parityCount;
            for (const auto& move : legal) {
                State child; child.board = state.board; child.board.makeMove(move);
                verify(child); ++parityCount;
            }
            ids.push_back(line.substr(0, tab)); states.push_back(state);
        }
        if (states.empty()) throw std::runtime_error("Empty manifest");
        bool avx2 = false;
#ifdef _MSC_VER
        int registers[4]; __cpuid(registers, 0);
        if (registers[0] >= 7) {
            __cpuidex(registers, 7, 0); const bool cpuAvx2 = (registers[1] & (1 << 5)) != 0;
            __cpuid(registers, 1); const bool osXsave = (registers[2] & (1 << 27)) != 0;
            avx2 = cpuAvx2 && osXsave && (_xgetbv(0) & 6) == 6;
        }
#endif
        std::cout << std::setprecision(12);
        std::cout << "{\"type\":\"metadata\",\"model\":\"" << MLEvaluationV2::residualModelVersion()
                  << "\",\"inference_backend\":\"" << MLEvaluationV2::residualBackendName()
                  << "\",\"alpha\":" << EvaluationConfig::ProductionHybridAlpha << ",\"positions\":" << states.size()
                  << ",\"parity_positions_including_children\":" << parityCount << ",\"avx2_cpu_and_os\":" << (avx2 ? "true" : "false")
                  << ",\"build\":\"" << CHESSAI_BUILD_TYPE << "\",\"compiler\":\"" << CHESSAI_COMPILER
                  << "\",\"iterations\":" << iterations << ",\"repetitions\":" << repeats << ",\"warmup\":" << warmup
                  << ",\"minimum_batch_us\":" << std::showpoint << MinimumBatchMicroseconds << std::noshowpoint << "}\n";
        if (verifyOnly) return 0;
        const auto& measuredTasks = compareCandidates ? candidateTasks : tasks;
        volatile double sink = 0;
        for (int repeat = 0; repeat < repeats; ++repeat) {
            for (size_t p = 0; p < states.size(); ++p) {
                auto& s = states[p];
                for (size_t slot = 0; slot < measuredTasks.size(); ++slot) {
                    const auto& task = measuredTasks[(slot + repeat + p) % measuredTasks.size()];
                    // Restore real preactivations before every batch; not part of timing.
                    decomposed(s); baseFeatures(s);
                    for (int i = 0; i < warmup; ++i) task.operation(s);
                    const auto measured = timeBatch(task.operation, s, iterations);
                    sink += s.score + s.output + s.input[0] + s.h1[0] + s.a1[0] + s.h2[0] + s.a2[0] + s.counts[0] + s.activeCount;
                    std::cout << "{\"type\":\"measurement\",\"position\":" << p << ",\"stage\":\"" << task.name
                              << "\",\"repetition\":" << repeat << ",\"iterations\":" << measured.iterations
                              << ",\"requested_iterations\":" << iterations << ",\"timing_attempts\":" << measured.attempts
                              << ",\"elapsed_us\":" << std::showpoint << measured.elapsedUs << std::noshowpoint << "}\n";
                }
                features(s);
                const auto nonzero = std::count_if(s.input.begin(), s.input.end(), [](float v) { return v != 0; });
                if (!repeat) std::cout << "{\"type\":\"sparsity\",\"position\":" << p << ",\"nonzero_inputs\":" << nonzero << ",\"total_inputs\":789}\n";
                std::cerr << "Profile repetition " << repeat + 1 << '/' << repeats << ", position " << p + 1 << '/' << states.size() << '\n';
            }
        }
        std::cout << "{\"type\":\"complete\",\"checksum\":" << sink << "}\n";
    } catch (const std::exception& error) { std::cerr << error.what() << '\n'; return 1; }
}
