#include "GameController.h"

#include <algorithm>
#include <cmath>
#include <random>
#include <set>
#include <string>
#include <vector>

namespace
{
    struct CandidateMove
    {
        Move move;

        int score = 0;
        uint64_t nodes = 0;
        uint64_t ttHits = 0;

        int depth = 0;
        long long timeMs = 0;
    };


    struct DifficultyProfile
    {
        int analysisDepth = 1;

        double temperatureCp = 100.0;
        double randomMoveChance = 0.0;

        double bookChance = 0.0;

        int maxBookPlies = 0;
    };


    // ========================================================
    // DIFFICULTY PROFILE
    // ========================================================

    DifficultyProfile getDifficultyProfile(
        int elo
    )
    {
        if (elo <= 500)
        {
            return {
                1,      // analysis depth
                300.0,  // tolerate large inaccuracies
                0.20,   // random legal move chance
                0.45,   // opening book chance
                4       // book plies
            };
        }


        if (elo <= 1000)
        {
            return {
                1,
                145.0,
                0.08,
                0.70,
                6
            };
        }


        if (elo <= 1500)
        {
            return {
                2,
                65.0,
                0.025,
                0.85,
                8
            };
        }


        return {
            3,
            20.0,
            0.0,
            0.95,
            10
        };
    }


    // ========================================================
    // RANDOM GENERATOR
    // ========================================================

    std::mt19937& randomGenerator()
    {
        static std::mt19937 generator(
            std::random_device{}()
        );

        return generator;
    }


    double randomUnit()
    {
        std::uniform_real_distribution<double> distribution(
            0.0,
            1.0
        );

        return distribution(
            randomGenerator()
        );
    }


    // ========================================================
    // OPENING BOOK
    //
    // UCI move sequences.
    // ========================================================

    const std::vector<
        std::vector<std::string>
    > OPENING_BOOK =
    {
        // Ruy Lopez
        {
            "e2e4", "e7e5",
            "g1f3", "b8c6",
            "f1b5", "a7a6",
            "b5a4", "g8f6"
        },

        // Italian
        {
            "e2e4", "e7e5",
            "g1f3", "b8c6",
            "f1c4", "g8f6",
            "d2d3", "f8c5"
        },

        // Scotch
        {
            "e2e4", "e7e5",
            "g1f3", "b8c6",
            "d2d4", "e5d4",
            "f3d4", "g8f6"
        },

        // Sicilian - Najdorf-ish
        {
            "e2e4", "c7c5",
            "g1f3", "d7d6",
            "d2d4", "c5d4",
            "f3d4", "g8f6"
        },

        // Sicilian - Classical
        {
            "e2e4", "c7c5",
            "g1f3", "b8c6",
            "d2d4", "c5d4",
            "f3d4", "g8f6"
        },

        // French
        {
            "e2e4", "e7e6",
            "d2d4", "d7d5",
            "b1c3", "g8f6"
        },

        // Caro-Kann
        {
            "e2e4", "c7c6",
            "d2d4", "d7d5",
            "b1c3", "d5e4"
        },

        // Scandinavian
        {
            "e2e4", "d7d5",
            "e4d5", "d8d5",
            "b1c3", "d5d8"
        },

        // Queen's Gambit Declined
        {
            "d2d4", "d7d5",
            "c2c4", "e7e6",
            "b1c3", "g8f6"
        },

        // Slav
        {
            "d2d4", "d7d5",
            "c2c4", "c7c6",
            "g1f3", "g8f6"
        },

        // Nimzo-Indian
        {
            "d2d4", "g8f6",
            "c2c4", "e7e6",
            "b1c3", "f8b4"
        },

        // King's Indian
        {
            "d2d4", "g8f6",
            "c2c4", "g7g6",
            "b1c3", "f8g7",
            "e2e4", "d7d6"
        },

        // English
        {
            "c2c4", "e7e5",
            "b1c3", "g8f6",
            "g2g3", "d7d5"
        },

        {
            "c2c4", "g8f6",
            "b1c3", "e7e5",
            "g1f3", "b8c6"
        },

        // Reti
        {
            "g1f3", "d7d5",
            "g2g3", "g8f6",
            "f1g2", "g7g6"
        }
    };


    // ========================================================
    // GAME HISTORY -> UCI STRINGS
    // ========================================================

    std::vector<std::string> getHistory(
        const Game& game
    )
    {
        std::vector<std::string> history;


        for (
            const Move& move :
            game.getMoveHistory()
        )
        {
            history.push_back(
                move.toString()
            );
        }


        return history;
    }


    // ========================================================
    // OPENING PREFIX MATCH
    // ========================================================

    bool prefixMatches(
        const std::vector<std::string>& line,
        const std::vector<std::string>& history
    )
    {
        if (
            history.size() >
            line.size()
        )
        {
            return false;
        }


        for (
            std::size_t i = 0;
            i < history.size();
            ++i
        )
        {
            if (
                line[i] !=
                history[i]
            )
            {
                return false;
            }
        }


        return true;
    }


    // ========================================================
    // GET OPENING BOOK MOVE
    // ========================================================

    bool getBookMove(
        const Game& game,
        int targetElo,
        Move& result
    )
    {
        const DifficultyProfile profile =
            getDifficultyProfile(
                targetElo
            );


        const std::vector<std::string> history =
            getHistory(
                game
            );


        if (
            static_cast<int>(
                history.size()
            ) >=
            profile.maxBookPlies
        )
        {
            return false;
        }


        if (
            randomUnit() >
            profile.bookChance
        )
        {
            return false;
        }


        std::set<std::string> possibleMoves;


        for (
            const auto& line :
            OPENING_BOOK
        )
        {
            if (
                !prefixMatches(
                    line,
                    history
                )
            )
            {
                continue;
            }


            if (
                history.size() >=
                line.size()
            )
            {
                continue;
            }


            possibleMoves.insert(
                line[
                    history.size()
                ]
            );
        }


        if (possibleMoves.empty())
        {
            return false;
        }


        const std::vector<Move> legalMoves =
            game.getLegalMoves();


        std::vector<Move> availableBookMoves;


        for (
            const std::string& bookMove :
            possibleMoves
        )
        {
            for (
                const Move& legalMove :
                legalMoves
            )
            {
                if (
                    legalMove.toString() ==
                    bookMove
                )
                {
                    availableBookMoves.push_back(
                        legalMove
                    );

                    break;
                }
            }
        }


        if (availableBookMoves.empty())
        {
            return false;
        }


        std::uniform_int_distribution<std::size_t>
            distribution(
                0,
                availableBookMoves.size() - 1
            );


        result =
            availableBookMoves[
                distribution(
                    randomGenerator()
                )
            ];


        return true;
    }


    // ========================================================
    // CAPTURE CHECK
    // ========================================================

    bool isCapture(
        const Board& board,
        const Move& move
    )
    {
        if (
            move.getFlag() ==
                MoveFlag::Capture ||

            move.getFlag() ==
                MoveFlag::EnPassant
        )
        {
            return true;
        }


        return !board
            .getPiece(
                move.getTo()
            )
            .isEmpty();
    }
}


// ============================================================
// CONSTRUCTOR
// ============================================================

GameController::GameController()
{
    newGame();
}


// ============================================================
// NEW GAME
// ============================================================

void GameController::newGame()
{
    game.reset();

    search.clearTranspositionTable();
}


// ============================================================
// GAME ACCESS
// ============================================================

const Game& GameController::getGame() const
{
    return game;
}


// ============================================================
// PLAYER MOVE
// ============================================================

bool GameController::makePlayerMove(
    int fromSquare,
    int toSquare,
    PieceType promotionPiece
)
{
    if (
        game.getGameState() !=
        GameState::Ongoing
    )
    {
        return false;
    }


    return game.tryMove(
        fromSquare,
        toSquare,
        promotionPiece
    );
}


// ============================================================
// ENGINE MOVE
//
// IMPORTANT:
// Signature must match GameController.h exactly:
//
// makeEngineMove(int, int, int)
// ============================================================

EngineMoveResult GameController::makeEngineMove(
    int thinkingTimeMs,
    int maxDepth,
    int targetElo
)
{
    EngineMoveResult result;


    if (
        game.getGameState() !=
        GameState::Ongoing
    )
    {
        return result;
    }


    const Color engineSide =
        game.getSideToMove();


    const std::vector<Move> legalMoves =
        game.getLegalMoves();


    if (legalMoves.empty())
    {
        return result;
    }


    // ========================================================
    // OPENING BOOK
    // ========================================================

    Move bookMove;


    if (
        getBookMove(
            game,
            targetElo,
            bookMove
        )
    )
    {
        result.wasCapture =
            isCapture(
                game.getBoard(),
                bookMove
            );


        if (
            !game.tryMove(
                bookMove
            )
        )
        {
            return result;
        }


        result.moveMade = true;

        result.wasCapture =
            result.wasCapture;

        result.fromBook = true;

        result.move =
            bookMove;

        result.score = 0;
        result.depth = 0;

        result.nodes = 0;
        result.ttHits = 0;

        result.timeMs = 0;


        return result;
    }


    // ========================================================
    // 2000 MODE
    //
    // Our strongest current engine.
    // ========================================================

    if (targetElo >= 2000)
    {
        const SearchResult searchResult =
            search.findBestMoveTimed(
                game.getBoard(),
                thinkingTimeMs,
                maxDepth
            );


        if (
            !isValidSquare(
                searchResult
                    .bestMove
                    .getFrom()
            ) ||

            !isValidSquare(
                searchResult
                    .bestMove
                    .getTo()
            )
        )
        {
            return result;
        }


        result.wasCapture =
            isCapture(
                game.getBoard(),
                searchResult.bestMove
            );


        if (
            !game.tryMove(
                searchResult.bestMove
            )
        )
        {
            return result;
        }


        result.moveMade = true;

        result.fromBook = false;

        result.move =
            searchResult.bestMove;


        result.score =
            searchResult.score;


        result.depth =
            searchResult.depthReached;


        result.nodes =
            searchResult.nodes;


        result.ttHits =
            searchResult.ttHits;


        result.timeMs =
            searchResult.timeMs;


        return result;
    }


    // ========================================================
    // WEAK ENGINE PROFILES
    // ========================================================

    const DifficultyProfile profile =
        getDifficultyProfile(
            targetElo
        );


    // ========================================================
    // RANDOM BLUNDER
    // ========================================================

    if (
        randomUnit() <
        profile.randomMoveChance
    )
    {
        std::uniform_int_distribution<std::size_t>
            distribution(
                0,
                legalMoves.size() - 1
            );


        const Move selected =
            legalMoves[
                distribution(
                    randomGenerator()
                )
            ];


        result.wasCapture =
            isCapture(
                game.getBoard(),
                selected
            );


        if (
            !game.tryMove(
                selected
            )
        )
        {
            return result;
        }


        result.moveMade = true;
        result.fromBook = false;

        result.move =
            selected;


        result.score = 0;
        result.depth = 0;

        result.nodes = 0;
        result.ttHits = 0;

        result.timeMs = 0;


        return result;
    }


    // ========================================================
    // ANALYSE ALL LEGAL MOVES
    // ========================================================

    std::vector<CandidateMove> candidates;


    for (
        const Move& move :
        legalMoves
    )
    {
        Board nextBoard =
            game.getBoard();


        nextBoard.makeMove(
            move
        );


        const SearchResult candidateSearch =
            search.findBestMove(
                nextBoard,
                profile.analysisDepth
            );


        CandidateMove candidate;


        candidate.move =
            move;


        candidate.score =
            candidateSearch.score;


        candidate.nodes =
            candidateSearch.nodes;


        candidate.ttHits =
            candidateSearch.ttHits;


        candidate.depth =
            profile.analysisDepth;


        candidate.timeMs =
            candidateSearch.timeMs;


        candidates.push_back(
            candidate
        );
    }


    if (candidates.empty())
    {
        return result;
    }


    // ========================================================
    // FIND BEST SCORE
    //
    // Evaluation uses White's perspective.
    // ========================================================

    int bestScore =
        candidates.front().score;


    for (
        const CandidateMove& candidate :
        candidates
    )
    {
        if (
            engineSide ==
            Color::White
        )
        {
            bestScore =
                std::max(
                    bestScore,
                    candidate.score
                );
        }
        else
        {
            bestScore =
                std::min(
                    bestScore,
                    candidate.score
                );
        }
    }


    // ========================================================
    // PROBABILISTIC MOVE SELECTION
    // ========================================================

    std::vector<double> weights;

    double totalWeight = 0.0;


    for (
        const CandidateMove& candidate :
        candidates
    )
    {
        int loss = 0;


        if (
            engineSide ==
            Color::White
        )
        {
            loss =
                bestScore -
                candidate.score;
        }
        else
        {
            loss =
                candidate.score -
                bestScore;
        }


        loss =
            std::max(
                0,
                loss
            );


        const double weight =
            std::exp(
                -static_cast<double>(
                    loss
                )
                /
                profile.temperatureCp
            );


        weights.push_back(
            weight
        );


        totalWeight +=
            weight;
    }


    if (totalWeight <= 0.0)
    {
        totalWeight = 1.0;
    }


    std::uniform_real_distribution<double>
        distribution(
            0.0,
            totalWeight
        );


    const double randomValue =
        distribution(
            randomGenerator()
        );


    double runningWeight = 0.0;

    std::size_t selectedIndex = 0;


    for (
        std::size_t i = 0;
        i < weights.size();
        ++i
    )
    {
        runningWeight +=
            weights[i];


        if (
            randomValue <=
            runningWeight
        )
        {
            selectedIndex = i;

            break;
        }
    }


    const CandidateMove selected =
        candidates[
            selectedIndex
        ];


    result.wasCapture =
        isCapture(
            game.getBoard(),
            selected.move
        );


    if (
        !game.tryMove(
            selected.move
        )
    )
    {
        return result;
    }


    result.moveMade = true;

    result.fromBook = false;

    result.move =
        selected.move;


    result.score =
        selected.score;


    result.depth =
        selected.depth;


    result.nodes =
        selected.nodes;


    result.ttHits =
        selected.ttHits;


    result.timeMs =
        selected.timeMs;


    return result;
}