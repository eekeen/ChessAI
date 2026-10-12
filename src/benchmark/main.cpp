#include "Tournament.h"
#include <filesystem>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <cmath>

static EvaluationMode mode(const std::string& name) {
    if (name == "classic") return EvaluationMode::Classic;
    if (name == "ml") return EvaluationMode::ML;
    if (name == "hybrid") return EvaluationMode::Hybrid;
    throw std::invalid_argument("Evaluator must be classic, ml or hybrid");
}
static long long integer(const std::string& value, long long minimum, long long maximum) {
    size_t used = 0;
    long long result = std::stoll(value, &used);
    if (used != value.size() || result < minimum || result > maximum) throw std::invalid_argument("Invalid numeric argument: " + value);
    return result;
}
int main(int argc, char** argv) {
    try {
        Tournament::Config config;
        bool explicitTime = false, overwrite = false, listOpenings = false;
        for (int i = 1; i < argc; ++i) {
            const std::string option = argv[i];
            if (option == "--help") {
                std::cout << "ChessAI_tournament --white classic --black hybrid --games 200 --time-ms 250 --seed 42 --output benchmark_results.json\n"
                          << "Options: --depth N (instead of --time-ms), --max-plies 300, --hybrid-alpha " << EvaluationConfig::ProductionHybridAlpha << ", --bootstrap-samples 10000, --overwrite\n"
                          << "--white/--black specify game 1 only. Every opening is played twice with evaluator colors reversed.\n";
                std::cout << "--opening-suite development|heldout|final (default development); --list-openings validates/lists positions without search.\n";
                return 0;
            }
            if (option == "--overwrite") { overwrite = true; continue; }
            if (option == "--list-openings") { listOpenings = true; continue; }
            if (++i == argc) throw std::invalid_argument("Missing value for " + option);
            const std::string value = argv[i];
            if (option == "--white") config.first = mode(value);
            else if (option == "--black") config.second = mode(value);
            else if (option == "--games") config.games = static_cast<int>(integer(value, 2, 1000000));
            else if (option == "--time-ms") { config.timeMs = static_cast<int>(integer(value, 1, 3600000)); explicitTime = true; }
            else if (option == "--depth") config.depth = static_cast<int>(integer(value, 1, 64));
            else if (option == "--max-plies") config.maxPlies = static_cast<int>(integer(value, 10, 100000));
            else if (option == "--seed") config.seed = static_cast<unsigned>(integer(value, 0, std::numeric_limits<unsigned>::max()));
            else if (option == "--bootstrap-samples") config.bootstrapSamples = static_cast<int>(integer(value, 100, 1000000));
            else if (option == "--output") config.output = value;
            else if (option == "--opening-suite") config.openingSuite = value;
            else if (option == "--hybrid-alpha") {
                size_t used = 0;
                config.hybridAlpha = std::stof(value, &used);
                if (used != value.size() || !std::isfinite(config.hybridAlpha) || config.hybridAlpha < 0 || config.hybridAlpha > 1)
                    throw std::invalid_argument("hybrid-alpha must be in [0,1]");
            }
            else throw std::invalid_argument("Unknown option: " + option);
        }
        const auto& suite = Tournament::openings(config.openingSuite);
        if (listOpenings) {
            std::cout << Tournament::suiteVersion(config.openingSuite) << '\n';
            for (const auto& opening : suite) {
                Game game; Tournament::applyOpening(game, opening);
                std::cout << opening.name << '\t' << opening.moves.size() << '\t'
                          << Tournament::normalizedFen(game.getBoard()) << '\t';
                for (size_t m = 0; m < opening.moves.size(); ++m) {
                    if (m) std::cout << ' ';
                    std::cout << opening.moves[m];
                }
                std::cout << '\n';
            }
            return 0;
        }
        if (config.first == config.second) throw std::invalid_argument("Choose two distinct evaluators");
        if (config.depth && explicitTime) throw std::invalid_argument("Use either --depth or --time-ms, not both");
        for (auto evaluator : {config.first, config.second}) {
            // Do not silently benchmark a V1 fallback under a V2 name.
            if (evaluator == EvaluationMode::ML && !MLEvaluationV2::directAvailable())
                throw std::runtime_error("V2 Direct weights unavailable; compile DirectWeightsV2.h first");
            if (evaluator == EvaluationMode::Hybrid && !MLEvaluationV2::residualAvailable())
                throw std::runtime_error("V2 Hybrid weights unavailable; compile ResidualWeightsV2.h first");
        }
        if (!overwrite && std::filesystem::exists(config.output)) throw std::invalid_argument("Output exists; use a new path or --overwrite");
        const auto assignments = Tournament::schedule(config);
        // Validate every opening before starting a potentially long match.
        for (const auto& opening : suite) { Game game; Tournament::applyOpening(game, opening); }
        Search first, second;
        std::vector<Tournament::GameRecord> records;
        std::cout << "Starting " << config.games << " games; " << (config.depth ? "fixed depth " : "milliseconds/move ")
                  << (config.depth ? config.depth : config.timeMs) << "; model " << PositionEvaluator::modelVersion() << std::endl;
        for (const auto& assignment : assignments) {
            auto record = Tournament::play(config, assignment, first, second);
            std::cout << "Game " << assignment.number << '/' << config.games << ' '
                      << PositionEvaluator::modeName(assignment.white) << " - " << PositionEvaluator::modeName(assignment.black)
                      << ' ' << record.result << ' ' << record.termination << " plies " << record.moves.size()
                      << " opening " << suite[assignment.openingIndex].name << std::endl;
            records.push_back(std::move(record));
            if (records.size() % 2 == 0)
                Tournament::writeReport(config, records, Tournament::summarize(config, records));
        }
        Tournament::printSummary(config, Tournament::summarize(config, records), static_cast<int>(records.size()));
    } catch (const std::exception& error) {
        std::cerr << "Tournament error: " << error.what() << '\n';
        return 1;
    }
}
