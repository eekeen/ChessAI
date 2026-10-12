#include "benchmark/Tournament.h"
#include <iostream>
#include <set>
#include <stdexcept>

static void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}

int main() {
    using namespace Tournament;
    try {
        std::set<std::string> oldPositions, oldWithoutEp, finalPositions, finalWithoutEp;
        for (const char* suite : {"development", "heldout"}) {
            for (const auto& opening : openings(suite)) {
                // Includes the initial position, every intermediate and the endpoint.
                for (size_t length = 0; length <= opening.moves.size(); ++length) {
                    Game game;
                    applyOpening(game, {opening.name, {opening.moves.begin(), opening.moves.begin() + length}});
                    const auto fen = normalizedFen(game.getBoard());
                    oldPositions.insert(fen);
                    oldWithoutEp.insert(fen.substr(0, fen.rfind(' ')));
                }
            }
        }
        require(openings("final").size() == 64, "final must have 64 positions");
        require(std::string(suiteVersion("final")) == "final-openings-v1", "final version");
        for (const auto& opening : openings("final")) {
            require(opening.moves.size() >= 8 && opening.moves.size() <= 14, "final opening length");
            Game game; applyOpening(game, opening);
            const auto fen = normalizedFen(game.getBoard());
            const auto withoutEp = fen.substr(0, fen.rfind(' '));
            require(game.getGameState() == GameState::Ongoing, "final nonterminal legality");
            require(!oldPositions.count(fen), "final overlaps prior endpoint/intermediate four-field FEN");
            require(!oldWithoutEp.count(withoutEp), "final overlaps prior position ignoring EP");
            require(finalPositions.insert(fen).second, "duplicate final four-field FEN");
            require(finalWithoutEp.insert(withoutEp).second, "duplicate final ignoring EP");
            Board restored;
            require(restored.loadFEN(fen + " 99 75") && normalizedFen(restored) == fen, "normalization ignores clocks");
        }
        Config depth;
        depth.openingSuite = "final"; depth.games = 128; depth.seed = 8675309;
        depth.hybridAlpha = .25f; depth.depth = 3;
        Config timed = depth; timed.depth = 0; timed.timeMs = 250;
        const auto a = schedule(depth), b = schedule(timed), again = schedule(depth);
        std::set<int> covered;
        require(a.size() == 128, "final game count");
        for (size_t i = 0; i < a.size(); ++i) {
            require(a[i].openingIndex == b[i].openingIndex && a[i].openingIndex == again[i].openingIndex,
                    "final experiments must have identical deterministic order");
            require(a[i].openingIndex == a[i - i % 2].openingIndex, "paired opening");
            require(a[i].white == (i % 2 ? depth.second : depth.first) &&
                    a[i].black == (i % 2 ? depth.first : depth.second), "paired colors");
            covered.insert(a[i].openingIndex);
        }
        require(covered.size() == 64, "each final position once per color");
        Config defaults;
        require(defaults.openingSuite == "development" && defaults.hybridAlpha == EvaluationConfig::ProductionHybridAlpha, "production defaults");
        std::cout << "Final suite: 64 legal unique positions; zero overlaps with " << oldPositions.size()
                  << " distinct prior endpoint/intermediate FENs (also ignoring EP).\n"
                  << "Seed 8675309: 128 assignments, identical depth/timed order and paired colors. No searches or matches run.\n";
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n'; return 1;
    }
}
