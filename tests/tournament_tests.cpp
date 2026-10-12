#include "benchmark/Tournament.h"
#include <cmath>
#include <iostream>
#include <set>
#include <stdexcept>

static void require(bool condition, const char* message) {
    if (!condition) throw std::runtime_error(message);
}
int main() {
    using namespace Tournament;
    try {
        Config config;
        require(config.openingSuite == "development", "production suite default preserved");
        require(openings().size() == 16, "development suite size frozen");
        require(openings("heldout").size() == 32, "heldout suite size");
        require(std::string(suiteVersion("development")) == "common-openings-v1" &&
                std::string(suiteVersion("heldout")) == "heldout-openings-v1", "separate suite versions");
        std::set<std::string> developmentFens, developmentWithoutEp, heldoutFens;
        // Include every development prefix, a stronger check than endpoints alone.
        for (const auto& opening : openings()) {
            for (size_t length = 0; length <= opening.moves.size(); ++length) {
                Game game;
                applyOpening(game, {opening.name, {opening.moves.begin(), opening.moves.begin() + length}});
                const auto fen = normalizedFen(game.getBoard());
                developmentFens.insert(fen);
                developmentWithoutEp.insert(fen.substr(0, fen.rfind(' ')));
            }
        }
        for (const auto& opening : openings("heldout")) {
            require(opening.moves.size() >= 6 && opening.moves.size() <= 12, "heldout opening length");
            Game game; applyOpening(game, opening);
            const auto fen = normalizedFen(game.getBoard());
            require(!developmentFens.count(fen), "normalized four-field FEN overlap");
            require(!developmentWithoutEp.count(fen.substr(0, fen.rfind(' '))), "overlap ignoring EP convention");
            require(heldoutFens.insert(fen).second, "duplicate heldout position");
            require(game.getGameState() == GameState::Ongoing, "heldout legal nonterminal position");
            Board restored;
            require(restored.loadFEN(fen + " 0 1") && normalizedFen(restored) == fen, "normalized FEN round trip");
        }
        Config heldout;
        heldout.openingSuite = "heldout"; heldout.games = 64; heldout.seed = 12345; heldout.hybridAlpha = .1f;
        const auto pilotA = schedule(heldout);
        heldout.hybridAlpha = .25f;
        const auto pilotB = schedule(heldout);
        std::set<int> heldoutCoverage;
        for (size_t i = 0; i < pilotA.size(); ++i) {
            require(pilotA[i].openingIndex == pilotB[i].openingIndex, "alpha does not affect heldout order");
            require(pilotA[i].openingIndex == pilotA[i - i % 2].openingIndex, "heldout reversed pair identity");
            require(pilotA[i].white == (i % 2 ? heldout.second : heldout.first) &&
                    pilotA[i].black == (i % 2 ? heldout.first : heldout.second), "heldout color reversal");
            heldoutCoverage.insert(pilotA[i].openingIndex);
        }
        require(pilotA.size() == 64 && heldoutCoverage.size() == 32, "every heldout opening exactly twice");
        auto assignments = schedule(config);
        auto replay = schedule(config);
        require(assignments.size() == 200, "default schedule size");
        std::set<int> firstCycle;
        for (size_t i = 0; i < assignments.size(); ++i) {
            const auto& game = assignments[i];
            require(game.number == static_cast<int>(i + 1), "game numbering");
            require(game.white == (i % 2 ? config.second : config.first), "color alternation");
            require(game.black == (i % 2 ? config.first : config.second), "black alternation");
            require(evaluatorFor(game, Color::White) == game.white && evaluatorFor(game, Color::Black) == game.black, "per-side evaluator assignment");
            require(game.openingIndex == assignments[i - i % 2].openingIndex, "paired opening identity");
            require(game.openingIndex == replay[i].openingIndex, "seed reproducibility");
            if (i < 2 * openings().size()) firstCycle.insert(game.openingIndex);
        }
        require(firstCycle.size() == openings().size(), "opening coverage");
        config.seed = 43;
        const auto different = schedule(config);
        bool changed = false;
        for (size_t i = 0; i < assignments.size(); ++i) changed |= assignments[i].openingIndex != different[i].openingIndex;
        require(changed, "seed changes opening order");
        config.seed = 42;
        config.games = 3;
        bool rejected = false;
        try { schedule(config); } catch (const std::invalid_argument&) { rejected = true; }
        require(rejected, "odd game count rejected");
        config.games = 6;
        for (const auto& opening : openings()) {
            require(opening.moves.size() >= 4 && opening.moves.size() <= 10, "opening length");
            Game game;
            applyOpening(game, opening);
            require(game.getMoveHistory().size() == opening.moves.size() && game.getGameState() == GameState::Ongoing, "legal opening");
        }
        const std::vector<std::string> results = {"1-0", "0-1", "0-1", "1/2-1/2", "1/2-1/2", "0-1"};
        const auto planned = schedule(config);
        std::vector<GameRecord> records;
        for (int i = 0; i < 6; ++i) {
            GameRecord game;
            game.assignment = planned[i];
            game.result = results[i];
            game.termination = i == 3 ? "repetition" : i == 4 ? "max_ply_draw" : "checkmate";
            game.moves.resize(20 + i, "e2e4");
            records.push_back(game);
        }
        auto summary = summarize(config, records);
        require(summary.whiteWins == 1 && summary.blackWins == 3 && summary.draws == 2, "color result accounting");
        require(summary.evaluators["classic"].wins == 3 && summary.evaluators["hybrid"].wins == 1, "evaluator win accounting");
        require(summary.evaluators["classic"].points == 4 && summary.evaluators["hybrid"].points == 2, "draws worth half a point");
        require(summary.byColor["classic"]["white"].wins == 1 && summary.byColor["classic"]["white"].losses == 1 &&
                summary.byColor["classic"]["white"].draws == 1, "Classic white breakdown");
        require(summary.byColor["classic"]["black"].wins == 2 && summary.byColor["classic"]["black"].draws == 1 &&
                summary.byColor["classic"]["black"].points == 2.5, "Classic black breakdown");
        require(std::abs(summary.firstScore - 2.0 / 3) < 1e-12 && summary.averagePlies == 22.5, "score and mean length");
        require(summary.terminations["repetition"] == 1 && summary.terminations["max_ply_draw"] == 1, "distinct draw accounting");
        require(summary.elo && std::abs(*summary.elo - 400 * std::log10(2.0)) < 1e-10, "Elo formula");
        require(!eloDifference(0) && !eloDifference(1) && *eloDifference(0.5) == 0, "Elo boundaries");
        require(summary.ciLow && summary.ciHigh && *summary.ciLow <= summary.firstScore && *summary.ciHigh >= summary.firstScore, "bootstrap range");
        const auto repeated = summarize(config, records);
        require(repeated.ciLow == summary.ciLow && repeated.ciHigh == summary.ciHigh, "bootstrap deterministic");
        auto duplicated = records;
        duplicated.insert(duplicated.end(), records.begin(), records.end());
        const auto sameOpenings = summarize(config, duplicated);
        require(sameOpenings.openingClusters == summary.openingClusters && sameOpenings.ciLow == summary.ciLow &&
                sameOpenings.ciHigh == summary.ciHigh, "repeated identical games do not shrink uncertainty");
        require(!summarize(config, {records[0], records[1]}).ciLow, "single opening is insufficient for CI");
        require(outcome(GameState::WhiteCheckmate) == std::make_pair(std::string("1-0"), std::string("checkmate")), "white checkmate outcome");
        require(outcome(GameState::BlackCheckmate).first == "0-1", "black checkmate outcome");
        require(outcome(GameState::Stalemate).second == "stalemate", "stalemate reason");
        require(outcome(GameState::DrawRepetition).second == "repetition", "repetition reason");
        require(outcome(GameState::DrawFiftyMove).second == "fifty_move_rule", "fifty-move reason");
        require(outcome(GameState::DrawInsufficientMaterial).second == "insufficient_material", "insufficient-material reason");
        if (MLEvaluationV2::residualAvailable()) {
            config.depth = 1;
            config.maxPlies = 10;
            Search first, second;
            for (int i = 0; i < 2; ++i) {
                const auto game = play(config, planned[i], first, second);
                require(game.moves.size() == 10 && game.termination == "max_ply_draw", "actual game length guard");
                require(first.getEvaluationMode() == config.first && second.getEvaluationMode() == config.second, "actual search modes");
                require(game.nodes > 0, "search ran");
                Game replayGame;
                applyOpening(replayGame, {"replay", game.moves});
            }
        }
        std::cout << "Tournament scheduling, legal openings, modes, results, scores and uncertainty tests passed\n";
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}
