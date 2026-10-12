#include "Zobrist.h"

#include <array>
#include <cstdint>

namespace
{
    uint64_t splitmix64(uint64_t& state)
    {
        uint64_t z = (state += 0x9E3779B97F4A7C15ULL);

        z = (z ^ (z >> 30)) *
            0xBF58476D1CE4E5B9ULL;

        z = (z ^ (z >> 27)) *
            0x94D049BB133111EBULL;

        return z ^ (z >> 31);
    }


    int pieceIndex(const Piece& piece)
    {
        if (piece.isEmpty())
        {
            return -1;
        }

        int typeIndex = -1;

        switch (piece.type)
        {
            case PieceType::Pawn:
                typeIndex = 0;
                break;

            case PieceType::Knight:
                typeIndex = 1;
                break;

            case PieceType::Bishop:
                typeIndex = 2;
                break;

            case PieceType::Rook:
                typeIndex = 3;
                break;

            case PieceType::Queen:
                typeIndex = 4;
                break;

            case PieceType::King:
                typeIndex = 5;
                break;

            case PieceType::None:
            default:
                return -1;
        }

        if (piece.color == Color::Black)
        {
            typeIndex += 6;
        }

        return typeIndex;
    }


    struct ZobristTables
    {
        std::array<std::array<uint64_t, 64>, 12> pieces{};
        std::array<uint64_t, 16> castling{};
        std::array<uint64_t, 8> enPassantFiles{};

        uint64_t blackToMove = 0;

        ZobristTables()
        {
            // Fixed seed:
            // identical engine runs generate identical hashes.
            uint64_t seed =
                0x123456789ABCDEF0ULL;

            for (auto& pieceTable : pieces)
            {
                for (uint64_t& key : pieceTable)
                {
                    key = splitmix64(seed);
                }
            }

            for (uint64_t& key : castling)
            {
                key = splitmix64(seed);
            }

            for (uint64_t& key : enPassantFiles)
            {
                key = splitmix64(seed);
            }

            blackToMove =
                splitmix64(seed);
        }
    };


    const ZobristTables& getTables()
    {
        static const ZobristTables tables;

        return tables;
    }
}


// ============================================================
// CALCULATE ZOBRIST HASH
// ============================================================

uint64_t Zobrist::hash(const Board& board)
{
    const ZobristTables& tables =
        getTables();

    uint64_t key = 0;


    // ========================================================
    // PIECES
    // ========================================================

    for (int square = 0; square < 64; ++square)
    {
        const Piece piece =
            board.getPiece(square);

        const int index =
            pieceIndex(piece);

        if (index >= 0)
        {
            key ^=
                tables.pieces[index][square];
        }
    }


    // ========================================================
    // SIDE TO MOVE
    // ========================================================

    if (board.getSideToMove() == Color::Black)
    {
        key ^=
            tables.blackToMove;
    }


    // ========================================================
    // CASTLING RIGHTS
    //
    // Bit 0 = White king-side
    // Bit 1 = White queen-side
    // Bit 2 = Black king-side
    // Bit 3 = Black queen-side
    // ========================================================

    int castlingMask = 0;

    if (board.canCastleKingside(Color::White))
    {
        castlingMask |= 1;
    }

    if (board.canCastleQueenside(Color::White))
    {
        castlingMask |= 2;
    }

    if (board.canCastleKingside(Color::Black))
    {
        castlingMask |= 4;
    }

    if (board.canCastleQueenside(Color::Black))
    {
        castlingMask |= 8;
    }

    key ^=
        tables.castling[castlingMask];


    // ========================================================
    // EN PASSANT FILE
    // ========================================================

    const int enPassantSquare =
        board.getEnPassantSquare();

    if (enPassantSquare >= 0)
    {
        const int file =
            fileOf(enPassantSquare);

        key ^=
            tables.enPassantFiles[file];
    }

    return key;
}