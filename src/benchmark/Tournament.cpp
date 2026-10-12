#ifdef _WIN32
#define NOMINMAX
#include <windows.h>
#endif
#include "Tournament.h"
#include <algorithm>
#include <cmath>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <numeric>
#include <random>
#include <stdexcept>
#include <system_error>

namespace Tournament {
const std::vector<Opening>& openings(const std::string& selected) {
    if (selected == "final") return finalOpenings();
    if (selected == "heldout") return heldoutOpenings();
    if (selected != "development") throw std::invalid_argument("Unknown opening suite: " + selected);
    static const std::vector<Opening> suite = {
        {"Italian (e4 e5)", {"e2e4","e7e5","g1f3","b8c6","f1c4","f8c5"}},
        {"Ruy Lopez", {"e2e4","e7e5","g1f3","b8c6","f1b5","a7a6","b5a4","g8f6"}},
        {"Scotch", {"e2e4","e7e5","g1f3","b8c6","d2d4","e5d4","f3d4","g8f6"}},
        {"Petrov", {"e2e4","e7e5","g1f3","g8f6","f3e5","d7d6"}},
        {"Sicilian", {"e2e4","c7c5","g1f3","d7d6","d2d4","c5d4","f3d4","g8f6"}},
        {"French", {"e2e4","e7e6","d2d4","d7d5","b1c3","g8f6"}},
        {"Caro-Kann", {"e2e4","c7c6","d2d4","d7d5","b1c3","d5e4","c3e4","c8f5"}},
        {"Queen's Gambit", {"d2d4","d7d5","c2c4","e7e6","b1c3","g8f6"}},
        {"Slav", {"d2d4","d7d5","c2c4","c7c6","g1f3","g8f6"}},
        {"King's Indian", {"d2d4","g8f6","c2c4","g7g6","b1c3","f8g7","e2e4","d7d6"}},
        {"English", {"c2c4","e7e5","b1c3","g8f6","g2g3","d7d5"}},
        {"Reti", {"g1f3","d7d5","g2g3","g8f6","f1g2","g7g6"}},
        {"Nimzo-Indian", {"d2d4","g8f6","c2c4","e7e6","b1c3","f8b4"}},
        {"Queen's Indian", {"d2d4","g8f6","c2c4","e7e6","g1f3","b7b6"}},
        {"Scandinavian", {"e2e4","d7d5","e4d5","d8d5","b1c3","d5a5"}},
        {"Pirc", {"e2e4","d7d6","d2d4","g8f6","b1c3","g7g6"}}
    };
    return suite;
}

// Rejection sampling makes opening order stable across standard-library versions.
static unsigned draw(std::mt19937& rng, unsigned bound) {
    const unsigned threshold = -bound % bound;
    unsigned value;
    do { value = rng(); } while (value < threshold);
    return value % bound;
}

std::vector<Assignment> schedule(const Config& config) {
    if (config.games < 2 || config.games % 2) throw std::invalid_argument("games must be positive and even (at least 2)");
    std::mt19937 rng(config.seed);
    std::vector<int> indices(openings(config.openingSuite).size());
    std::iota(indices.begin(), indices.end(), 0);
    std::vector<Assignment> result;
    for (int pair = 0; pair < config.games / 2; ++pair) {
        const int slot = pair % static_cast<int>(indices.size());
        if (slot == 0) {
            std::iota(indices.begin(), indices.end(), 0);
            for (unsigned n = static_cast<unsigned>(indices.size()); n > 1; --n)
                std::swap(indices[n - 1], indices[draw(rng, n)]);
        }
        result.push_back({pair * 2 + 1, indices[slot], config.first, config.second});
        result.push_back({pair * 2 + 2, indices[slot], config.second, config.first});
    }
    return result;
}

EvaluationMode evaluatorFor(const Assignment& assignment, Color side) {
    if (side == Color::White) return assignment.white;
    if (side == Color::Black) return assignment.black;
    throw std::invalid_argument("Invalid side to move");
}

void applyOpening(Game& game, const Opening& opening) {
    for (const auto& uci : opening.moves) {
        bool found = false;
        for (const auto& move : game.getLegalMoves()) {
            if (move.toString() == uci) {
                found = game.tryMove(move);
                break;
            }
        }
        if (!found || game.getGameState() != GameState::Ongoing)
            throw std::runtime_error("Invalid opening " + opening.name + " at " + uci);
    }
}

std::pair<std::string, std::string> outcome(GameState state) {
    switch (state) {
        case GameState::WhiteCheckmate: return {"1-0", "checkmate"};
        case GameState::BlackCheckmate: return {"0-1", "checkmate"};
        case GameState::Stalemate: return {"1/2-1/2", "stalemate"};
        case GameState::DrawRepetition: return {"1/2-1/2", "repetition"};
        case GameState::DrawFiftyMove: return {"1/2-1/2", "fifty_move_rule"};
        case GameState::DrawInsufficientMaterial: return {"1/2-1/2", "insufficient_material"};
        default: throw std::invalid_argument("Ongoing game has no result");
    }
}

GameRecord play(const Config& config, const Assignment& assignment, Search& first, Search& second) {
    if (!first.setHybridAlpha(config.hybridAlpha) || !second.setHybridAlpha(config.hybridAlpha))
        throw std::runtime_error("Invalid Hybrid alpha");
    if (!first.setEvaluationMode(config.first) || !second.setEvaluationMode(config.second))
        throw std::runtime_error("Requested evaluator unavailable");
    // Separate evaluator-specific TTs; equal fresh state at every game boundary.
    first.clearTranspositionTable();
    second.clearTranspositionTable();
    Game game;
    applyOpening(game, openings(config.openingSuite).at(assignment.openingIndex));
    GameRecord record;
    record.assignment = assignment;
    const auto start = std::chrono::steady_clock::now();
    while (true) {
        const auto state = game.getGameState();
        if (state != GameState::Ongoing) {
            const auto end = outcome(state);
            record.result = end.first;
            record.termination = end.second;
            break;
        }
        if (game.getMoveHistory().size() >= static_cast<size_t>(config.maxPlies)) {
            record.result = "1/2-1/2";
            record.termination = "max_ply_draw";
            break;
        }
        const auto mode = evaluatorFor(assignment, game.getSideToMove());
        Search& search = mode == config.first ? first : second;
        if (search.getEvaluationMode() != mode) throw std::logic_error("Evaluator assignment mismatch");
        const auto result = config.depth ? search.findBestMove(game.getBoard(), config.depth)
            : search.findBestMoveTimed(game.getBoard(), config.timeMs, 64);
        record.nodes += result.nodes;
        if (!game.tryMove(result.bestMove)) throw std::runtime_error("Search returned an illegal move");
    }
    for (const auto& move : game.getMoveHistory()) record.moves.push_back(move.toString());
    record.elapsedMs = std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - start).count();
    return record;
}

std::optional<double> eloDifference(double score) {
    if (score <= 0 || score >= 1) return std::nullopt;
    return 400 * std::log10(score / (1 - score));
}

Summary summarize(const Config& config, const std::vector<GameRecord>& games) {
    Summary result;
    const std::string firstName = PositionEvaluator::modeName(config.first);
    result.evaluators[firstName];
    result.evaluators[PositionEvaluator::modeName(config.second)];
    for (auto mode : {config.first, config.second})
        for (const char* color : {"white", "black"}) result.byColor[PositionEvaluator::modeName(mode)][color];
    for (const char* reason : {"checkmate", "stalemate", "repetition", "fifty_move_rule", "insufficient_material", "max_ply_draw"})
        result.terminations[reason] = 0;
    // Group ALL repeats of an opening, retaining reversed colors together.
    // Deterministic repeated games must not masquerade as independent samples.
    std::map<int, std::pair<double, int>> clusters;
    for (const auto& game : games) {
        double whiteScore;
        if (game.result == "1-0") { ++result.whiteWins; whiteScore = 1; }
        else if (game.result == "0-1") { ++result.blackWins; whiteScore = 0; }
        else if (game.result == "1/2-1/2") { ++result.draws; whiteScore = 0.5; }
        else throw std::invalid_argument("Invalid completed game result");
        auto& white = result.evaluators[PositionEvaluator::modeName(game.assignment.white)];
        auto& black = result.evaluators[PositionEvaluator::modeName(game.assignment.black)];
        auto& whiteColor = result.byColor[PositionEvaluator::modeName(game.assignment.white)]["white"];
        auto& blackColor = result.byColor[PositionEvaluator::modeName(game.assignment.black)]["black"];
        whiteColor.points += whiteScore;
        blackColor.points += 1 - whiteScore;
        if (whiteScore == 1) { ++whiteColor.wins; ++blackColor.losses; }
        else if (whiteScore == 0) { ++blackColor.wins; ++whiteColor.losses; }
        else { ++whiteColor.draws; ++blackColor.draws; }
        white.points += whiteScore;
        black.points += 1 - whiteScore;
        if (whiteScore == 1) { ++white.wins; ++black.losses; }
        else if (whiteScore == 0) { ++black.wins; ++white.losses; }
        else { ++white.draws; ++black.draws; }
        ++result.terminations[game.termination];
        result.averagePlies += game.moves.size();
        auto& cluster = clusters[game.assignment.openingIndex];
        cluster.first += game.assignment.white == config.first ? whiteScore : 1 - whiteScore;
        ++cluster.second;
    }
    if (games.empty()) return result;
    result.averagePlies /= games.size();
    result.firstScore = result.evaluators[firstName].points / games.size();
    result.elo = eloDifference(result.firstScore);
    result.openingClusters = static_cast<int>(clusters.size());
    if (clusters.size() < 2 || games.size() % 2) return result;
    std::vector<std::pair<double, int>> groups;
    for (const auto& item : clusters) groups.push_back(item.second);
    std::mt19937 rng(config.seed ^ 0xB0057A9u);
    std::vector<double> samples;
    for (int iteration = 0; iteration < config.bootstrapSamples; ++iteration) {
        double points = 0;
        int count = 0;
        for (size_t i = 0; i < groups.size(); ++i) {
            const auto& group = groups[draw(rng, static_cast<unsigned>(groups.size()))];
            points += group.first;
            count += group.second;
        }
        samples.push_back(points / count);
    }
    if (!samples.empty()) {
        std::sort(samples.begin(), samples.end());
        result.ciLow = samples[static_cast<size_t>(0.025 * (samples.size() - 1))];
        result.ciHigh = samples[static_cast<size_t>(0.975 * (samples.size() - 1))];
    }
    return result;
}

static void quote(std::ostream& stream, const std::string& text) {
    stream << '"';
    for (unsigned char c : text) {
        if (c == '"' || c == '\\') stream << '\\' << c;
        else if (c < 32) stream << "\\u" << std::hex << std::setw(4) << std::setfill('0') << int(c) << std::dec << std::setfill(' ');
        else stream << c;
    }
    stream << '"';
}
static void optional(std::ostream& stream, std::optional<double> value) {
    if (value) stream << *value;
    else stream << "null";
}
static void movesJson(std::ostream& stream, const std::vector<std::string>& moves) {
    stream << '[';
    for (size_t i = 0; i < moves.size(); ++i) { if (i) stream << ','; quote(stream, moves[i]); }
    stream << ']';
}

void writeReport(const Config& config, const std::vector<GameRecord>& games, const Summary& summary) {
    const std::filesystem::path destination(config.output);
    if (destination.has_parent_path()) std::filesystem::create_directories(destination.parent_path());
    auto temporary = destination;
    temporary += ".tmp";
    std::ofstream stream(temporary, std::ios::binary | std::ios::trunc);
    if (!stream) throw std::runtime_error("Cannot open report temporary file");
    stream << std::setprecision(10);
    stream << "{\n  \"format_version\": 1,\n  \"complete\": " << (games.size() == static_cast<size_t>(config.games) ? "true" : "false")
           << ",\n  \"config\": {\"first_evaluator\": "; quote(stream, PositionEvaluator::modeName(config.first));
    stream << ", \"second_evaluator\": "; quote(stream, PositionEvaluator::modeName(config.second));
    stream << ", \"games\": " << config.games << ", \"time_ms\": " << (config.depth ? 0 : config.timeMs)
           << ", \"fixed_depth\": " << config.depth << ", \"max_plies\": " << config.maxPlies << ", \"seed\": " << config.seed
           << ", \"bootstrap_samples\": " << config.bootstrapSamples << ", \"hybrid_alpha\": " << config.hybridAlpha
           << ", \"opening_suite\": "; quote(stream, suiteVersion(config.openingSuite));
    stream << ", \"opening_suite_selection\": "; quote(stream, config.openingSuite);
    stream << "},\n"
           << "  \"model\": "; quote(stream, PositionEvaluator::modelVersion());
    stream << ",\n  \"models\": {\"classic\": \"handcrafted-material-pst\", \"ml\": ";
    quote(stream, MLEvaluationV2::directModelVersion());
    stream << ", \"hybrid\": "; quote(stream, MLEvaluationV2::residualModelVersion()); stream << '}';
    stream << ",\n  \"summary\": {\n    \"games_completed\": " << games.size() << ", \"white_wins\": " << summary.whiteWins
           << ", \"black_wins\": " << summary.blackWins << ", \"draws\": " << summary.draws
           << ",\n    \"average_plies\": " << summary.averagePlies << ",\n    \"evaluators\": {";
    bool first = true;
    for (const auto& entry : summary.evaluators) {
        if (!first) stream << ',';
        first = false;
        stream << '\n'; quote(stream, entry.first);
        stream << ": {\"wins\": " << entry.second.wins << ", \"losses\": " << entry.second.losses << ", \"draws\": " << entry.second.draws
               << ", \"points\": " << entry.second.points << ", \"score_percent\": " << 100 * entry.second.points / games.size() << '}';
    }
    stream << "},\n    \"by_evaluator_color\": {";
    bool firstMode = true;
    for (const auto& mode : summary.byColor) {
        if (!firstMode) stream << ',';
        firstMode = false;
        quote(stream, mode.first); stream << ":{";
        bool firstColor = true;
        for (const auto& color : mode.second) {
            if (!firstColor) stream << ',';
            firstColor = false;
            const auto& stats = color.second;
            const int count = stats.wins + stats.losses + stats.draws;
            quote(stream, color.first);
            stream << ":{\"games\":" << count << ",\"wins\":" << stats.wins
                   << ",\"losses\":" << stats.losses << ",\"draws\":" << stats.draws
                   << ",\"points\":" << stats.points << ",\"score_percent\":";
            if (count) stream << 100 * stats.points / count; else stream << "null";
            stream << '}';
        }
        stream << '}';
    }
    stream << "},\n    \"termination_counts\": {";
    first = true;
    for (const auto& entry : summary.terminations) {
        if (!first) stream << ',';
        first = false;
        quote(stream, entry.first); stream << ':' << entry.second;
    }
    stream << "},\n    \"elo_first_minus_second\": "; optional(stream, summary.elo);
    stream << ",\n    \"uncertainty\": {\"method\": \"opening-cluster bootstrap, percentile 95%\", \"clusters\": " << summary.openingClusters
           << ", \"score_first_ci95\": ["; optional(stream, summary.ciLow); stream << ','; optional(stream, summary.ciHigh);
    stream << "], \"elo_first_minus_second_ci95\": [";
    optional(stream, summary.ciLow ? eloDifference(*summary.ciLow) : std::nullopt); stream << ',';
    optional(stream, summary.ciHigh ? eloDifference(*summary.ciHigh) : std::nullopt);
    stream << "], \"note\": \"Null score limits mean insufficient opening clusters. Null Elo limits at score 0/1 are unbounded. "
              "Bootstrap intervals are conditional on this finite opening suite; identical cluster outcomes yield a degenerate interval. "
              "Do not infer significance from small or degenerate samples. Max-ply draws are safety adjudications.\"}\n  },\n  \"games\": [\n";
    for (size_t i = 0; i < games.size(); ++i) {
        if (i) stream << ",\n";
        const auto& game = games[i];
        const auto& opening = openings(config.openingSuite).at(game.assignment.openingIndex);
        stream << "    {\"number\": " << game.assignment.number << ", \"pair\": " << (game.assignment.number + 1) / 2 << ", \"white\": ";
        quote(stream, PositionEvaluator::modeName(game.assignment.white)); stream << ", \"black\": "; quote(stream, PositionEvaluator::modeName(game.assignment.black));
        stream << ", \"opening\": "; quote(stream, opening.name);
        Game openingGame; applyOpening(openingGame, opening);
        stream << ", \"opening_fen\": "; quote(stream, normalizedFen(openingGame.getBoard()));
        stream << ", \"opening_index\": " << game.assignment.openingIndex << ", \"opening_moves\": "; movesJson(stream, opening.moves);
        stream << ", \"result\": "; quote(stream, game.result); stream << ", \"termination\": "; quote(stream, game.termination);
        stream << ", \"plies\": " << game.moves.size() << ", \"searched_plies\": " << game.moves.size() - opening.moves.size()
               << ", \"elapsed_ms\": " << game.elapsedMs << ", \"nodes\": " << game.nodes << ", \"moves\": "; movesJson(stream, game.moves);
        stream << '}';
    }
    stream << "\n  ]\n}\n";
    stream.flush();
    if (!stream) throw std::runtime_error("Failed writing tournament report");
    stream.close();
#ifdef _WIN32
    if (!MoveFileExW(temporary.c_str(), destination.c_str(), MOVEFILE_REPLACE_EXISTING | MOVEFILE_WRITE_THROUGH))
        throw std::system_error(GetLastError(), std::system_category(), "Cannot publish tournament report");
#else
    std::filesystem::rename(temporary, destination);
#endif
}

void printSummary(const Config& config, const Summary& summary, int completed) {
    std::cout << "Suite: " << suiteVersion(config.openingSuite) << "; Hybrid alpha: " << config.hybridAlpha << '\n';
    std::cout << "\nGames: " << completed << "  White wins: " << summary.whiteWins << "  Black wins: " << summary.blackWins << "  Draws: " << summary.draws << '\n';
    for (const auto& item : summary.evaluators)
        std::cout << item.first << ": " << item.second.wins << " wins, " << item.second.losses << " losses, " << item.second.draws
                  << " draws; score " << 100 * item.second.points / completed << "%\n";
    for (const auto& mode : summary.byColor)
        for (const auto& color : mode.second) {
            const auto& stats = color.second;
            const int count = stats.wins + stats.losses + stats.draws;
            std::cout << mode.first << " as " << color.first << ": " << stats.wins << " W / " << stats.losses
                      << " L / " << stats.draws << " D; score " << (count ? 100 * stats.points / count : 0) << "%\n";
        }
    std::cout << "Average plies: " << summary.averagePlies << '\n';
    for (const auto& item : summary.terminations) std::cout << item.first << ": " << item.second << '\n';
    std::cout << "Elo " << PositionEvaluator::modeName(config.first) << " minus " << PositionEvaluator::modeName(config.second) << ": ";
    optional(std::cout, summary.elo);
    std::cout << "\n95% score CI for " << PositionEvaluator::modeName(config.first) << ": [";
    optional(std::cout, summary.ciLow); std::cout << ", "; optional(std::cout, summary.ciHigh);
    std::cout << "] (opening-cluster bootstrap; " << summary.openingClusters << " clusters)\n"
              << "No significance claim is made by this benchmark. Inspect the CI, sample size and max-ply draws.\n"
              << "Report: " << config.output << '\n';
}
}
