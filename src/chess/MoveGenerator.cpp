#include "MoveGenerator.h"

// ============================================================
// GENERATE PSEUDO-LEGAL MOVES
// ============================================================

std::vector<Move> MoveGenerator::generatePseudoLegalMoves(
    const Board& board
) const
{
    std::vector<Move> moves;

    const Color sideToMove = board.getSideToMove();

    for (int square = 0; square < 64; ++square)
    {
        const Piece piece = board.getPiece(square);

        // Skip empty squares and opponent pieces
        if (piece.isEmpty() || piece.color != sideToMove)
        {
            continue;
        }

        switch (piece.type)
        {
            case PieceType::Pawn:
                generatePawnMoves(
                    board,
                    square,
                    piece.color,
                    moves
                );
                break;

            case PieceType::Knight:
                generateKnightMoves(
                    board,
                    square,
                    piece.color,
                    moves
                );
                break;

            case PieceType::Bishop:
                generateBishopMoves(
                    board,
                    square,
                    piece.color,
                    moves
                );
                break;

            case PieceType::Rook:
                generateRookMoves(
                    board,
                    square,
                    piece.color,
                    moves
                );
                break;

            case PieceType::Queen:
                generateQueenMoves(
                    board,
                    square,
                    piece.color,
                    moves
                );
                break;

            case PieceType::King:
                generateKingMoves(
                    board,
                    square,
                    piece.color,
                    moves
                );
                break;

            case PieceType::None:
            default:
                break;
        }
    }

    return moves;
}


// ============================================================
// GENERATE LEGAL MOVES
// ============================================================

std::vector<Move> MoveGenerator::generateLegalMoves(
    const Board& board
) const
{
    std::vector<Move> legalMoves;

    const Color movingColor = board.getSideToMove();

    // Important:
    // Generate pseudo-legal moves here.
    const std::vector<Move> pseudoMoves =
        generatePseudoLegalMoves(board);

    for (const Move& move : pseudoMoves)
    {
        // Copy the board so the real position is not modified
        Board testBoard = board;

        // Make the candidate move
        testBoard.makeMove(move);

        // Legal only if our own king is not in check afterwards
        if (!isInCheck(testBoard, movingColor))
        {
            legalMoves.push_back(move);
        }
    }

    return legalMoves;
}


// ============================================================
// CHECK IF A KING IS IN CHECK
// ============================================================

bool MoveGenerator::isInCheck(
    const Board& board,
    Color color
) const
{
    int kingSquare = -1;

    // Find the king
    for (int square = 0; square < 64; ++square)
    {
        const Piece piece = board.getPiece(square);

        if (
            piece.type == PieceType::King &&
            piece.color == color
        )
        {
            kingSquare = square;
            break;
        }
    }

    // This should not happen in a normal chess position
    if (kingSquare == -1)
    {
        return false;
    }

    return isSquareAttacked(
        board,
        kingSquare,
        oppositeColor(color)
    );
}


// ============================================================
// CHECK IF A SQUARE IS ATTACKED
// ============================================================

bool MoveGenerator::isSquareAttacked(
    const Board& board,
    int square,
    Color attacker
) const
{
    const int file = fileOf(square);
    const int rank = rankOf(square);


    // ========================================================
    // PAWN ATTACKS
    // ========================================================

    // To find an attacking pawn, look backwards from
    // the target square relative to the pawn's movement.
    const int pawnRank =
        rank + ((attacker == Color::White) ? -1 : 1);

    if (pawnRank >= 0 && pawnRank < 8)
    {
        for (int fileOffset : {-1, 1})
        {
            const int pawnFile =
                file + fileOffset;

            if (pawnFile < 0 || pawnFile >= 8)
            {
                continue;
            }

            const int pawnSquare =
                pawnRank * 8 + pawnFile;

            const Piece piece =
                board.getPiece(pawnSquare);

            if (
                piece.type == PieceType::Pawn &&
                piece.color == attacker
            )
            {
                return true;
            }
        }
    }


    // ========================================================
    // KNIGHT ATTACKS
    // ========================================================

    const int knightOffsets[8][2] =
    {
        { 1,  2},
        { 2,  1},
        { 2, -1},
        { 1, -2},
        {-1, -2},
        {-2, -1},
        {-2,  1},
        {-1,  2}
    };

    for (const auto& offset : knightOffsets)
    {
        const int targetFile =
            file + offset[0];

        const int targetRank =
            rank + offset[1];

        if (
            targetFile < 0 ||
            targetFile >= 8 ||
            targetRank < 0 ||
            targetRank >= 8
        )
        {
            continue;
        }

        const int targetSquare =
            targetRank * 8 + targetFile;

        const Piece piece =
            board.getPiece(targetSquare);

        if (
            piece.type == PieceType::Knight &&
            piece.color == attacker
        )
        {
            return true;
        }
    }


    // ========================================================
    // BISHOP / QUEEN DIAGONAL ATTACKS
    // ========================================================

    const int diagonalDirections[4][2] =
    {
        { 1,  1},
        { 1, -1},
        {-1,  1},
        {-1, -1}
    };

    for (const auto& direction : diagonalDirections)
    {
        int currentFile =
            file + direction[0];

        int currentRank =
            rank + direction[1];

        while (
            currentFile >= 0 &&
            currentFile < 8 &&
            currentRank >= 0 &&
            currentRank < 8
        )
        {
            const int targetSquare =
                currentRank * 8 + currentFile;

            const Piece piece =
                board.getPiece(targetSquare);

            if (!piece.isEmpty())
            {
                if (
                    piece.color == attacker &&
                    (
                        piece.type == PieceType::Bishop ||
                        piece.type == PieceType::Queen
                    )
                )
                {
                    return true;
                }

                // First occupied square blocks the ray
                break;
            }

            currentFile += direction[0];
            currentRank += direction[1];
        }
    }


    // ========================================================
    // ROOK / QUEEN STRAIGHT ATTACKS
    // ========================================================

    const int straightDirections[4][2] =
    {
        { 1,  0},
        {-1,  0},
        { 0,  1},
        { 0, -1}
    };

    for (const auto& direction : straightDirections)
    {
        int currentFile =
            file + direction[0];

        int currentRank =
            rank + direction[1];

        while (
            currentFile >= 0 &&
            currentFile < 8 &&
            currentRank >= 0 &&
            currentRank < 8
        )
        {
            const int targetSquare =
                currentRank * 8 + currentFile;

            const Piece piece =
                board.getPiece(targetSquare);

            if (!piece.isEmpty())
            {
                if (
                    piece.color == attacker &&
                    (
                        piece.type == PieceType::Rook ||
                        piece.type == PieceType::Queen
                    )
                )
                {
                    return true;
                }

                // First occupied square blocks the ray
                break;
            }

            currentFile += direction[0];
            currentRank += direction[1];
        }
    }


    // ========================================================
    // KING ATTACKS
    // ========================================================

    for (int rankOffset = -1;
         rankOffset <= 1;
         ++rankOffset)
    {
        for (int fileOffset = -1;
             fileOffset <= 1;
             ++fileOffset)
        {
            if (
                fileOffset == 0 &&
                rankOffset == 0
            )
            {
                continue;
            }

            const int targetFile =
                file + fileOffset;

            const int targetRank =
                rank + rankOffset;

            if (
                targetFile < 0 ||
                targetFile >= 8 ||
                targetRank < 0 ||
                targetRank >= 8
            )
            {
                continue;
            }

            const int targetSquare =
                targetRank * 8 + targetFile;

            const Piece piece =
                board.getPiece(targetSquare);

            if (
                piece.type == PieceType::King &&
                piece.color == attacker
            )
            {
                return true;
            }
        }
    }

    return false;
}


// ============================================================
// PAWN MOVES
// ============================================================

void MoveGenerator::generatePawnMoves(
    const Board& board,
    int square,
    Color color,
    std::vector<Move>& moves
) const
{
    const int file = fileOf(square);
    const int rank = rankOf(square);

    const int direction =
        (color == Color::White) ? 1 : -1;

    const int startRank =
        (color == Color::White) ? 1 : 6;

    const int promotionRank =
        (color == Color::White) ? 7 : 0;

    const int nextRank =
        rank + direction;


    // ========================================================
    // MOVE FORWARD
    // ========================================================

    if (nextRank >= 0 && nextRank < 8)
    {
        const int forwardSquare =
            nextRank * 8 + file;

        if (board.getPiece(forwardSquare).isEmpty())
        {
            if (nextRank == promotionRank)
            {
                moves.emplace_back(
                    square,
                    forwardSquare,
                    MoveFlag::Promotion,
                    PieceType::Queen
                );

                moves.emplace_back(
                    square,
                    forwardSquare,
                    MoveFlag::Promotion,
                    PieceType::Rook
                );

                moves.emplace_back(
                    square,
                    forwardSquare,
                    MoveFlag::Promotion,
                    PieceType::Bishop
                );

                moves.emplace_back(
                    square,
                    forwardSquare,
                    MoveFlag::Promotion,
                    PieceType::Knight
                );
            }
            else
            {
                moves.emplace_back(
                    square,
                    forwardSquare,
                    MoveFlag::Quiet
                );

                // Double pawn push
                if (rank == startRank)
                {
                    const int doubleRank =
                        rank + 2 * direction;

                    const int doubleSquare =
                        doubleRank * 8 + file;

                    if (board.getPiece(doubleSquare).isEmpty())
                    {
                        moves.emplace_back(
                            square,
                            doubleSquare,
                            MoveFlag::DoublePawnPush
                        );
                    }
                }
            }
        }
    }


    // ========================================================
    // CAPTURES + EN PASSANT
    // ========================================================

    for (int fileOffset : {-1, 1})
    {
        const int captureFile =
            file + fileOffset;

        const int captureRank =
            rank + direction;

        if (
            captureFile < 0 ||
            captureFile >= 8 ||
            captureRank < 0 ||
            captureRank >= 8
        )
        {
            continue;
        }

        const int targetSquare =
            captureRank * 8 + captureFile;

        const Piece target =
            board.getPiece(targetSquare);


        // ----------------------------------------------------
        // Normal capture
        // ----------------------------------------------------

        if (
            !target.isEmpty() &&
            target.color != color
        )
        {
            if (captureRank == promotionRank)
            {
                moves.emplace_back(
                    square,
                    targetSquare,
                    MoveFlag::Promotion,
                    PieceType::Queen
                );

                moves.emplace_back(
                    square,
                    targetSquare,
                    MoveFlag::Promotion,
                    PieceType::Rook
                );

                moves.emplace_back(
                    square,
                    targetSquare,
                    MoveFlag::Promotion,
                    PieceType::Bishop
                );

                moves.emplace_back(
                    square,
                    targetSquare,
                    MoveFlag::Promotion,
                    PieceType::Knight
                );
            }
            else
            {
                moves.emplace_back(
                    square,
                    targetSquare,
                    MoveFlag::Capture
                );
            }
        }


        // ----------------------------------------------------
        // En passant
        // ----------------------------------------------------

        if (
            targetSquare ==
            board.getEnPassantSquare()
        )
        {
            const int capturedPawnSquare =
                (color == Color::White)
                    ? targetSquare - 8
                    : targetSquare + 8;

            const Piece capturedPawn =
                board.getPiece(capturedPawnSquare);

            if (
                capturedPawn.type == PieceType::Pawn &&
                capturedPawn.color == oppositeColor(color)
            )
            {
                moves.emplace_back(
                    square,
                    targetSquare,
                    MoveFlag::EnPassant
                );
            }
        }
    }
}


// ============================================================
// KNIGHT MOVES
// ============================================================

void MoveGenerator::generateKnightMoves(
    const Board& board,
    int square,
    Color color,
    std::vector<Move>& moves
) const
{
    const int file = fileOf(square);
    const int rank = rankOf(square);

    const int offsets[8][2] =
    {
        { 1,  2},
        { 2,  1},
        { 2, -1},
        { 1, -2},
        {-1, -2},
        {-2, -1},
        {-2,  1},
        {-1,  2}
    };

    for (const auto& offset : offsets)
    {
        const int targetFile =
            file + offset[0];

        const int targetRank =
            rank + offset[1];

        if (
            targetFile < 0 ||
            targetFile >= 8 ||
            targetRank < 0 ||
            targetRank >= 8
        )
        {
            continue;
        }

        const int targetSquare =
            targetRank * 8 + targetFile;

        const Piece target =
            board.getPiece(targetSquare);

        if (target.isEmpty())
        {
            moves.emplace_back(
                square,
                targetSquare,
                MoveFlag::Quiet
            );
        }
        else if (target.color != color)
        {
            moves.emplace_back(
                square,
                targetSquare,
                MoveFlag::Capture
            );
        }
    }
}


// ============================================================
// BISHOP MOVES
// ============================================================

void MoveGenerator::generateBishopMoves(
    const Board& board,
    int square,
    Color color,
    std::vector<Move>& moves
) const
{
    const std::vector<std::pair<int, int>> directions =
    {
        { 1,  1},
        { 1, -1},
        {-1,  1},
        {-1, -1}
    };

    generateSlidingMoves(
        board,
        square,
        color,
        directions,
        moves
    );
}


// ============================================================
// ROOK MOVES
// ============================================================

void MoveGenerator::generateRookMoves(
    const Board& board,
    int square,
    Color color,
    std::vector<Move>& moves
) const
{
    const std::vector<std::pair<int, int>> directions =
    {
        { 1,  0},
        {-1,  0},
        { 0,  1},
        { 0, -1}
    };

    generateSlidingMoves(
        board,
        square,
        color,
        directions,
        moves
    );
}


// ============================================================
// QUEEN MOVES
// ============================================================

void MoveGenerator::generateQueenMoves(
    const Board& board,
    int square,
    Color color,
    std::vector<Move>& moves
) const
{
    const std::vector<std::pair<int, int>> directions =
    {
        { 1,  0},
        {-1,  0},
        { 0,  1},
        { 0, -1},

        { 1,  1},
        { 1, -1},
        {-1,  1},
        {-1, -1}
    };

    generateSlidingMoves(
        board,
        square,
        color,
        directions,
        moves
    );
}


// ============================================================
// KING MOVES
// ============================================================

void MoveGenerator::generateKingMoves(
    const Board& board,
    int square,
    Color color,
    std::vector<Move>& moves
) const
{
    const int file = fileOf(square);
    const int rank = rankOf(square);


    // ========================================================
    // NORMAL KING MOVES
    // ========================================================

    for (int rankOffset = -1;
         rankOffset <= 1;
         ++rankOffset)
    {
        for (int fileOffset = -1;
             fileOffset <= 1;
             ++fileOffset)
        {
            if (
                fileOffset == 0 &&
                rankOffset == 0
            )
            {
                continue;
            }

            const int targetFile =
                file + fileOffset;

            const int targetRank =
                rank + rankOffset;

            if (
                targetFile < 0 ||
                targetFile >= 8 ||
                targetRank < 0 ||
                targetRank >= 8
            )
            {
                continue;
            }

            const int targetSquare =
                targetRank * 8 + targetFile;

            const Piece target =
                board.getPiece(targetSquare);

            if (target.isEmpty())
            {
                moves.emplace_back(
                    square,
                    targetSquare,
                    MoveFlag::Quiet
                );
            }
            else if (target.color != color)
            {
                moves.emplace_back(
                    square,
                    targetSquare,
                    MoveFlag::Capture
                );
            }
        }
    }


    // ========================================================
    // CASTLING
    // ========================================================

    const Color enemy =
        oppositeColor(color);


    // --------------------------------------------------------
    // WHITE CASTLING
    // --------------------------------------------------------

    if (
        color == Color::White &&
        square == 4
    )
    {
        // King-side: e1 -> g1
        if (board.canCastleKingside(Color::White))
        {
            const Piece rook =
                board.getPiece(7);

            if (
                rook.type == PieceType::Rook &&
                rook.color == Color::White &&
                board.getPiece(5).isEmpty() &&
                board.getPiece(6).isEmpty() &&
                !isSquareAttacked(board, 4, enemy) &&
                !isSquareAttacked(board, 5, enemy) &&
                !isSquareAttacked(board, 6, enemy)
            )
            {
                moves.emplace_back(
                    4,
                    6,
                    MoveFlag::KingCastle
                );
            }
        }


        // Queen-side: e1 -> c1
        if (board.canCastleQueenside(Color::White))
        {
            const Piece rook =
                board.getPiece(0);

            if (
                rook.type == PieceType::Rook &&
                rook.color == Color::White &&
                board.getPiece(1).isEmpty() &&
                board.getPiece(2).isEmpty() &&
                board.getPiece(3).isEmpty() &&
                !isSquareAttacked(board, 4, enemy) &&
                !isSquareAttacked(board, 3, enemy) &&
                !isSquareAttacked(board, 2, enemy)
            )
            {
                moves.emplace_back(
                    4,
                    2,
                    MoveFlag::QueenCastle
                );
            }
        }
    }


    // --------------------------------------------------------
    // BLACK CASTLING
    // --------------------------------------------------------

    if (
        color == Color::Black &&
        square == 60
    )
    {
        // King-side: e8 -> g8
        if (board.canCastleKingside(Color::Black))
        {
            const Piece rook =
                board.getPiece(63);

            if (
                rook.type == PieceType::Rook &&
                rook.color == Color::Black &&
                board.getPiece(61).isEmpty() &&
                board.getPiece(62).isEmpty() &&
                !isSquareAttacked(board, 60, enemy) &&
                !isSquareAttacked(board, 61, enemy) &&
                !isSquareAttacked(board, 62, enemy)
            )
            {
                moves.emplace_back(
                    60,
                    62,
                    MoveFlag::KingCastle
                );
            }
        }


        // Queen-side: e8 -> c8
        if (board.canCastleQueenside(Color::Black))
        {
            const Piece rook =
                board.getPiece(56);

            if (
                rook.type == PieceType::Rook &&
                rook.color == Color::Black &&
                board.getPiece(57).isEmpty() &&
                board.getPiece(58).isEmpty() &&
                board.getPiece(59).isEmpty() &&
                !isSquareAttacked(board, 60, enemy) &&
                !isSquareAttacked(board, 59, enemy) &&
                !isSquareAttacked(board, 58, enemy)
            )
            {
                moves.emplace_back(
                    60,
                    58,
                    MoveFlag::QueenCastle
                );
            }
        }
    }
}


// ============================================================
// SLIDING PIECES
// Used by bishop, rook and queen
// ============================================================

void MoveGenerator::generateSlidingMoves(
    const Board& board,
    int square,
    Color color,
    const std::vector<std::pair<int, int>>& directions,
    std::vector<Move>& moves
) const
{
    const int startFile =
        fileOf(square);

    const int startRank =
        rankOf(square);

    for (const auto& direction : directions)
    {
        int currentFile =
            startFile + direction.first;

        int currentRank =
            startRank + direction.second;

        while (
            currentFile >= 0 &&
            currentFile < 8 &&
            currentRank >= 0 &&
            currentRank < 8
        )
        {
            const int targetSquare =
                currentRank * 8 + currentFile;

            const Piece target =
                board.getPiece(targetSquare);

            // Empty square
            if (target.isEmpty())
            {
                moves.emplace_back(
                    square,
                    targetSquare,
                    MoveFlag::Quiet
                );
            }
            else
            {
                // Enemy piece can be captured
                if (target.color != color)
                {
                    moves.emplace_back(
                        square,
                        targetSquare,
                        MoveFlag::Capture
                    );
                }

                // Cannot move through any occupied square
                break;
            }

            currentFile += direction.first;
            currentRank += direction.second;
        }
    }
}