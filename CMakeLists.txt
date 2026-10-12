cmake_minimum_required(VERSION 3.16)

project(ChessAI)

option(CHESSAI_BUILD_PROFILER "Build isolated static Hybrid stage profiler" OFF)
set(CHESSAI_V2_OPTIMIZATION "3" CACHE STRING "Residual inference: 0 reference, 1 AVX2 tail, 2 tail+sparse, 3 tail+active-list")
if(NOT CHESSAI_V2_OPTIMIZATION MATCHES "^[0123]$")
    message(FATAL_ERROR "CHESSAI_V2_OPTIMIZATION must be 0, 1, 2 or 3")
endif()
option(CHESSAI_V2_ENABLE_AVX2 "Build runtime-checked MSVC x64 AVX2 kernels" ON)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

set(CHESS_CORE_SOURCES

    src/chess/Board.cpp
    src/chess/Move.cpp
    src/chess/MoveGenerator.cpp

    src/engine/Engine.cpp
    src/engine/Evaluation.cpp
    src/engine/MLEvaluation.cpp
    src/engine/MLEvaluationV2.cpp
    src/engine/V2Kernels.cpp
    src/engine/PositionEvaluator.cpp
    src/engine/Search.cpp
    src/engine/Zobrist.cpp
    src/engine/TranspositionTable.cpp

    src/game/Game.cpp
    src/game/GameController.cpp
)

add_library(ChessCore ${CHESS_CORE_SOURCES})
target_include_directories(ChessCore PUBLIC
    src
    src/chess
    src/engine
    src/game
)

set(CHESSAI_ML_WEIGHTS_HEADER "" CACHE FILEPATH "Optional alternate model header for isolated validation builds")
if(CHESSAI_ML_WEIGHTS_HEADER)
    target_compile_definitions(ChessCore PRIVATE CHESSAI_ML_WEIGHTS_HEADER="${CHESSAI_ML_WEIGHTS_HEADER}")
endif()

set(CHESSAI_V2_MODEL_DIR "${CMAKE_CURRENT_SOURCE_DIR}/src/engine/generated" CACHE PATH "Directory containing optional V2 model headers")
target_include_directories(ChessCore PRIVATE "${CHESSAI_V2_MODEL_DIR}")

# Instrumented copy only: normal engine/tournament contain no leaf-logging hooks.
add_library(ChessCoreDiagnostics ${CHESS_CORE_SOURCES})
foreach(core ChessCore ChessCoreDiagnostics)
    target_compile_definitions(${core} PRIVATE CHESSAI_V2_OPTIMIZATION=${CHESSAI_V2_OPTIMIZATION})
    if(CHESSAI_V2_ENABLE_AVX2 AND MSVC AND CMAKE_SIZEOF_VOID_P EQUAL 8 AND CMAKE_GENERATOR_PLATFORM STREQUAL "x64")
        target_sources(${core} PRIVATE src/engine/V2KernelsAVX2.cpp)
        target_compile_definitions(${core} PRIVATE CHESSAI_V2_AVX2=1)
        # ISA flags only on this TU. Strict FP forbids contraction/reassociation.
        set_source_files_properties(src/engine/V2KernelsAVX2.cpp PROPERTIES COMPILE_OPTIONS "/arch:AVX2;/fp:strict")
    endif()
endforeach()
target_include_directories(ChessCoreDiagnostics PUBLIC src src/chess src/engine src/game PRIVATE "${CHESSAI_V2_MODEL_DIR}")
target_compile_definitions(ChessCoreDiagnostics PUBLIC CHESSAI_SEARCH_DIAGNOSTICS=1)
if(CHESSAI_ML_WEIGHTS_HEADER)
    target_compile_definitions(ChessCoreDiagnostics PRIVATE CHESSAI_ML_WEIGHTS_HEADER="${CHESSAI_ML_WEIGHTS_HEADER}")
endif()
add_executable(ChessAI_diagnostics src/benchmark/Diagnostics.cpp)
target_link_libraries(ChessAI_diagnostics PRIVATE ChessCoreDiagnostics)

add_executable(ChessAI src/main.cpp)
target_link_libraries(ChessAI PRIVATE ChessCore)

include(CTest)
if(BUILD_TESTING)
    add_executable(perft_tests tests/perft_tests.cpp)
    target_link_libraries(perft_tests PRIVATE ChessCore)
    add_test(NAME perft COMMAND perft_tests)
    add_executable(evaluation_tests tests/evaluation_tests.cpp)
    target_link_libraries(evaluation_tests PRIVATE ChessCore)
    add_test(NAME evaluation COMMAND evaluation_tests)
endif()
add_executable(eval_tool tests/eval_tool.cpp)
target_link_libraries(eval_tool PRIVATE ChessCore)

add_library(TournamentCore src/benchmark/Tournament.cpp src/benchmark/OpeningSuites.cpp src/benchmark/FinalOpenings.cpp)
target_link_libraries(TournamentCore PUBLIC ChessCore)
add_executable(ChessAI_tournament src/benchmark/main.cpp)
target_link_libraries(ChessAI_tournament PRIVATE TournamentCore)
add_executable(ChessAI_performance src/benchmark/Performance.cpp)
add_executable(ChessAI_calibration src/benchmark/CalibrationAdapter.cpp)
target_link_libraries(ChessAI_calibration PRIVATE ChessCore)
target_compile_definitions(ChessAI_calibration PRIVATE CHESSAI_COMPILER="${CMAKE_CXX_COMPILER_ID}-${CMAKE_CXX_COMPILER_VERSION}")
target_link_libraries(ChessAI_performance PRIVATE ChessCore)
target_compile_definitions(ChessAI_performance PRIVATE
    CHESSAI_BUILD_TYPE="$<CONFIG>"
    CHESSAI_COMPILER="${CMAKE_CXX_COMPILER_ID}-${CMAKE_CXX_COMPILER_VERSION}")
if(CHESSAI_BUILD_PROFILER)
    add_executable(ChessAI_profile src/benchmark/HybridProfile.cpp src/benchmark/HybridProfileStages.cpp)
    target_link_libraries(ChessAI_profile PRIVATE ChessCore)
    target_include_directories(ChessAI_profile PRIVATE "${CHESSAI_V2_MODEL_DIR}")
    target_compile_definitions(ChessAI_profile PRIVATE CHESSAI_BUILD_TYPE="$<CONFIG>"
        CHESSAI_COMPILER="${CMAKE_CXX_COMPILER_ID}-${CMAKE_CXX_COMPILER_VERSION}")
    set_property(TARGET ChessAI_profile PROPERTY INTERPROCEDURAL_OPTIMIZATION FALSE)
    # Compile an unmodified reference solely for compiler/assembly inspection; never link it.
    add_library(ChessAI_profile_reference OBJECT src/engine/MLEvaluationV2.cpp)
    target_include_directories(ChessAI_profile_reference PRIVATE src/engine "${CHESSAI_V2_MODEL_DIR}")
    if(MSVC)
        foreach(profile_target ChessAI_profile ChessAI_profile_reference)
            file(MAKE_DIRECTORY "${CMAKE_CURRENT_BINARY_DIR}/profile-asm/${profile_target}")
            target_compile_options(${profile_target} PRIVATE /Qvec-report:2 /FAs
                "/Fa${CMAKE_CURRENT_BINARY_DIR}/profile-asm/${profile_target}/")
        endforeach()
    endif()
endif()
if(BUILD_TESTING)
    add_executable(tournament_tests tests/tournament_tests.cpp)
    target_link_libraries(tournament_tests PRIVATE TournamentCore)
    add_test(NAME tournament COMMAND tournament_tests)
    add_executable(opening_suite_tests tests/opening_suite_tests.cpp)
    target_link_libraries(opening_suite_tests PRIVATE TournamentCore)
    add_test(NAME opening_suites COMMAND opening_suite_tests)
endif()
