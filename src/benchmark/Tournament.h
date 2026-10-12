#pragma once
#include "engine/Search.h"
#include "game/Game.h"
#include <map>
#include <optional>
#include <string>
#include <vector>

namespace Tournament {
struct Config {
    EvaluationMode first = EvaluationMode::Classic;
    EvaluationMode second = EvaluationMode::Hybrid;
    int games = 200;
    int timeMs = 250;
    int depth = 0; // zero selects timed iterative deepening
    int maxPlies = 300; // includes the forced opening moves
    unsigned seed = 42;
    int bootstrapSamples = 10000;
    float hybridAlpha = EvaluationConfig::ProductionHybridAlpha;
    std::string openingSuite = "development";
    std::string output = "benchmark_results.json";
};
struct Opening { std::string name; std::vector<std::string> moves; };
struct Assignment {
    int number, openingIndex;
    EvaluationMode white, black;
};
struct GameRecord {
    Assignment assignment;
    std::string result, termination;
    std::vector<std::string> moves;
    long long elapsedMs = 0;
    uint64_t nodes = 0;
};
struct EvaluatorStats { int wins = 0, losses = 0, draws = 0; double points = 0; };
struct Summary {
    int whiteWins = 0, blackWins = 0, draws = 0;
    double averagePlies = 0;
    std::map<std::string, EvaluatorStats> evaluators;
    std::map<std::string, std::map<std::string, EvaluatorStats>> byColor;
    std::map<std::string, int> terminations;
    double firstScore = 0;
    std::optional<double> elo, ciLow, ciHigh;
    int openingClusters = 0;
};
const std::vector<Opening>& openings(const std::string& suite = "development");
const std::vector<Opening>& heldoutOpenings();
const std::vector<Opening>& finalOpenings();
const char* suiteVersion(const std::string& suite);
std::string normalizedFen(const Board& board);
std::vector<Assignment> schedule(const Config& config);
EvaluationMode evaluatorFor(const Assignment& assignment, Color side);
void applyOpening(Game& game, const Opening& opening);
std::pair<std::string, std::string> outcome(GameState state);
GameRecord play(const Config& config, const Assignment& assignment, Search& first, Search& second);
Summary summarize(const Config& config, const std::vector<GameRecord>& games);
std::optional<double> eloDifference(double score);
void writeReport(const Config& config, const std::vector<GameRecord>& games, const Summary& summary);
void printSummary(const Config& config, const Summary& summary, int completed);
}
