#include "Board.h"

#include <iostream>
#include <sstream>
#include <string>

// ============================================================
// CONSTRUCTOR
// ============================================================

Board::Board()
{
    reset();
}


// ============================================================
// RESET TO STANDARD START POSITION
// ============================================================

void Board::reset()
{
    for (Piece& piece : squares)
    {
        piece = {
            PieceType::None,
            Color::None
        };
    }

    // White pawns
    for (int square = 8; square < 16; ++square)
    {
        squares[square] = {
            PieceType::Pawn,
            Color::White
        };
    }

    // Black pawns
    for (int square = 48; square < 56; ++square)
    {
        squares[square] = {
            PieceType::Pawn,
            Color::Black
        };
    }

    // White pieces
    squares[0] = {PieceType::Rook,   Color::White};
    squares[1] = {PieceType::Knight, Color::White};
    squares[2] = {PieceType::Bishop, Color::White};
    squares[3] = {PieceType::Queen,  Color::White};
    squares[4] = {PieceType::King,   Color::White};
    squares[5] = {PieceType::Bishop, Color::White};
    squares[6] = {PieceType::Knight, Color::White};
    squares[7] = {PieceType::Rook,   Color::White};

    // Black pieces
    squares[56] = {PieceType::Rook,   Color::Black};
    squares[57] = {PieceType::Knight, Color::Black};
    squares[58] = {PieceType::Bishop, Color::Black};
    squares[59] = {PieceType::Queen,  Color::Black};
    squares[60] = {PieceType::King,   Color::Black};
    squares[61] = {PieceType::Bishop, Color::Black};
    squares[62] = {PieceType::Knight, Color::Black};
    squares[63] = {PieceType::Rook,   Color::Black};

    sideToMove = Color::White;

    whiteCanCastleKingside = true;
    whiteCanCastleQueenside = true;

    blackCanCastleKingside = true;
    blackCanCastleQueenside = true;

    enPassantSquare = -1;

    halfmoveClock = 0;
    fullmoveNumber = 1;
}

bool Board::loadFEN(const std::string& fen)
{
    std::istringstream stream(fen);

    std::string boardPart;
    std::string sidePart;
    std::string castlingPart;
    std::string enPassantPart;

    int parsedHalfmoveClock = 0;
    int parsedFullmoveNumber = 1;

    if (!(
        stream >>
        boardPart >>
        sidePart >>
        castlingPart >>
        enPassantPart >>
        parsedHalfmoveClock >>
        parsedFullmoveNumber
    ))
    {
        return false;
    }

    // ========================================================
    // CLEAR BOARD
    // ========================================================

    for (Piece& piece : squares)
    {
        piece = {
            PieceType::None,
            Color::None
        };
    }


    // ========================================================
    // PIECE PLACEMENT
    // FEN starts at rank 8 and works down to rank 1
    // ========================================================

    int rank = 7;
    int file = 0;

    for (char character : boardPart)
    {
        // New rank
        if (character == '/')
        {
            if (file != 8)
            {
                return false;
            }

            --rank;
            file = 0;

            if (rank < 0)
            {
                return false;
            }

            continue;
        }

        // Empty squares
        if (character >= '1' && character <= '8')
        {
            file += character - '0';

            if (file > 8)
            {
                return false;
            }

            continue;
        }

        if (file >= 8 || rank < 0)
        {
            return false;
        }

        Color color;

        if (character >= 'A' && character <= 'Z')
        {
            color = Color::White;
        }
        else
        {
            color = Color::Black;
        }

        PieceType type = PieceType::None;

        switch (character)
        {
            case 'P':
            case 'p':
                type = PieceType::Pawn;
                break;

            case 'N':
            case 'n':
                type = PieceType::Knight;
                break;

            case 'B':
            case 'b':
                type = PieceType::Bishop;
                break;

            case 'R':
            case 'r':
                type = PieceType::Rook;
                break;

            case 'Q':
            case 'q':
                type = PieceType::Queen;
                break;

            case 'K':
            case 'k':
                type = PieceType::King;
                break;

            default:
                return false;
        }

        const int square =
            rank * 8 + file;

        squares[square] = {
            type,
            color
        };

        ++file;
    }

    if (rank != 0 || file != 8)
    {
        return false;
    }


    // ========================================================
    // SIDE TO MOVE
    // ========================================================

    if (sidePart == "w")
    {
        sideToMove = Color::White;
    }
    else if (sidePart == "b")
    {
        sideToMove = Color::Black;
    }
    else
    {
        return false;
    }


    // ========================================================
    // CASTLING RIGHTS
    // ========================================================

    whiteCanCastleKingside = false;
    whiteCanCastleQueenside = false;
    blackCanCastleKingside = false;
    blackCanCastleQueenside = false;

    if (castlingPart != "-")
    {
        for (char character : castlingPart)
        {
            switch (character)
            {
                case 'K':
                    whiteCanCastleKingside = true;
                    break;

                case 'Q':
                    whiteCanCastleQueenside = true;
                    break;

                case 'k':
                    blackCanCastleKingside = true;
                    break;

                case 'q':
                    blackCanCastleQueenside = true;
                    break;

                default:
                    return false;
            }
        }
    }


    // ========================================================
    // EN PASSANT
    // ========================================================

    enPassantSquare = -1;

    if (enPassantPart != "-")
    {
        if (enPassantPart.length() != 2)
        {
            return false;
        }

        const char fileCharacter =
            enPassantPart[0];

        const char rankCharacter =
            enPassantPart[1];

        if (
            fileCharacter < 'a' ||
            fileCharacter > 'h' ||
            rankCharacter < '1' ||
            rankCharacter > '8'
        )
        {
            return false;
        }

        const int epFile =
            fileCharacter - 'a';

        const int epRank =
            rankCharacter - '1';

        enPassantSquare =
            epRank * 8 + epFile;
    }


    // ========================================================
    // MOVE CLOCKS
    // ========================================================

    if (
        parsedHalfmoveClock < 0 ||
        parsedFullmoveNumber < 1
    )
    {
        return false;
    }

    halfmoveClock =
        parsedHalfmoveClock;

    fullmoveNumber =
        parsedFullmoveNumber;

    return true;
}

// ============================================================
// PIECE ACCESS
// ============================================================

Piece Board::getPiece(int square) const
{
    if (!isValidSquare(square))
    {
        return {};
    }

    return squares[square];
}

void Board::setPiece(
    int square,
    Piece piece
)
{
    if (!isValidSquare(square))
    {
        return;
    }

    squares[square] = piece;
}


// ============================================================
// SIDE TO MOVE
// ============================================================

Color Board::getSideToMove() const
{
    return sideToMove;
}


// ============================================================
// CASTLING RIGHTS
// ============================================================

bool Board::canCastleKingside(Color color) const
{
    if (color == Color::White)
    {
        return whiteCanCastleKingside;
    }

    if (color == Color::Black)
    {
        return blackCanCastleKingside;
    }

    return false;
}

bool Board::canCastleQueenside(Color color) const
{
    if (color == Color::White)
    {
        return whiteCanCastleQueenside;
    }

    if (color == Color::Black)
    {
        return blackCanCastleQueenside;
    }

    return false;
}


// ============================================================
// EN PASSANT
// ============================================================

int Board::getEnPassantSquare() const
{
    return enPassantSquare;
}


// ============================================================
// MOVE CLOCKS
// ============================================================

int Board::getHalfmoveClock() const
{
    return halfmoveClock;
}

int Board::getFullmoveNumber() const
{
    return fullmoveNumber;
}


// ============================================================
// MAKE MOVE
// ============================================================

void Board::makeMove(const Move& move)
{
    const int from = move.getFrom();
    const int to = move.getTo();

    if (
        !isValidSquare(from) ||
        !isValidSquare(to)
    )
    {
        return;
    }

    const Piece movingPiece = squares[from];
    const Piece capturedPiece = squares[to];

    if (movingPiece.isEmpty())
    {
        return;
    }

    const Color movingColor =
        movingPiece.color;

    const bool isPawnMove =
        movingPiece.type == PieceType::Pawn;

    const bool isCapture =
        !capturedPiece.isEmpty() ||
        move.getFlag() == MoveFlag::EnPassant;


    // ========================================================
    // UPDATE CASTLING RIGHTS FROM MOVING PIECE
    // ========================================================

    if (movingPiece.type == PieceType::King)
    {
        if (movingColor == Color::White)
        {
            whiteCanCastleKingside = false;
            whiteCanCastleQueenside = false;
        }
        else
        {
            blackCanCastleKingside = false;
            blackCanCastleQueenside = false;
        }
    }

    if (movingPiece.type == PieceType::Rook)
    {
        // White rooks
        if (from == 0)
        {
            whiteCanCastleQueenside = false;
        }
        else if (from == 7)
        {
            whiteCanCastleKingside = false;
        }

        // Black rooks
        else if (from == 56)
        {
            blackCanCastleQueenside = false;
        }
        else if (from == 63)
        {
            blackCanCastleKingside = false;
        }
    }


    // ========================================================
    // UPDATE CASTLING RIGHTS IF A ROOK IS CAPTURED
    // ========================================================

    if (capturedPiece.type == PieceType::Rook)
    {
        if (
            to == 0 &&
            capturedPiece.color == Color::White
        )
        {
            whiteCanCastleQueenside = false;
        }
        else if (
            to == 7 &&
            capturedPiece.color == Color::White
        )
        {
            whiteCanCastleKingside = false;
        }
        else if (
            to == 56 &&
            capturedPiece.color == Color::Black
        )
        {
            blackCanCastleQueenside = false;
        }
        else if (
            to == 63 &&
            capturedPiece.color == Color::Black
        )
        {
            blackCanCastleKingside = false;
        }
    }


    // ========================================================
    // RESET EN PASSANT
    // ========================================================

    enPassantSquare = -1;


    // ========================================================
    // HANDLE MOVE TYPE
    // ========================================================

    switch (move.getFlag())
    {
        // ----------------------------------------------------
        // KING-SIDE CASTLING
        // ----------------------------------------------------

        case MoveFlag::KingCastle:
        {
            squares[to] = movingPiece;
            squares[from] = {
                PieceType::None,
                Color::None
            };

            if (movingColor == Color::White)
            {
                // h1 -> f1
                squares[5] = squares[7];

                squares[7] = {
                    PieceType::None,
                    Color::None
                };
            }
            else
            {
                // h8 -> f8
                squares[61] = squares[63];

                squares[63] = {
                    PieceType::None,
                    Color::None
                };
            }

            break;
        }


        // ----------------------------------------------------
        // QUEEN-SIDE CASTLING
        // ----------------------------------------------------

        case MoveFlag::QueenCastle:
        {
            squares[to] = movingPiece;
            squares[from] = {
                PieceType::None,
                Color::None
            };

            if (movingColor == Color::White)
            {
                // a1 -> d1
                squares[3] = squares[0];

                squares[0] = {
                    PieceType::None,
                    Color::None
                };
            }
            else
            {
                // a8 -> d8
                squares[59] = squares[56];

                squares[56] = {
                    PieceType::None,
                    Color::None
                };
            }

            break;
        }


        // ----------------------------------------------------
        // EN PASSANT CAPTURE
        // ----------------------------------------------------

        case MoveFlag::EnPassant:
        {
            squares[to] = movingPiece;

            squares[from] = {
                PieceType::None,
                Color::None
            };

            int capturedPawnSquare;

            if (movingColor == Color::White)
            {
                capturedPawnSquare = to - 8;
            }
            else
            {
                capturedPawnSquare = to + 8;
            }

            squares[capturedPawnSquare] = {
                PieceType::None,
                Color::None
            };

            break;
        }


        // ----------------------------------------------------
        // PAWN PROMOTION
        // ----------------------------------------------------

        case MoveFlag::Promotion:
        {
            PieceType promotionPiece =
                move.getPromotionPiece();

            // Safety fallback
            if (
                promotionPiece != PieceType::Queen &&
                promotionPiece != PieceType::Rook &&
                promotionPiece != PieceType::Bishop &&
                promotionPiece != PieceType::Knight
            )
            {
                promotionPiece = PieceType::Queen;
            }

            squares[to] = {
                promotionPiece,
                movingColor
            };

            squares[from] = {
                PieceType::None,
                Color::None
            };

            break;
        }


        // ----------------------------------------------------
        // DOUBLE PAWN PUSH
        // ----------------------------------------------------

        case MoveFlag::DoublePawnPush:
        {
            squares[to] = movingPiece;

            squares[from] = {
                PieceType::None,
                Color::None
            };

            // The passed square becomes the en passant target.
            enPassantSquare =
                (from + to) / 2;

            break;
        }


        // ----------------------------------------------------
        // NORMAL MOVE / CAPTURE
        // ----------------------------------------------------

        case MoveFlag::Quiet:
        case MoveFlag::Capture:
        default:
        {
            squares[to] = movingPiece;

            squares[from] = {
                PieceType::None,
                Color::None
            };

            break;
        }
    }


    // ========================================================
    // 50-MOVE RULE CLOCK
    // ========================================================

    if (isPawnMove || isCapture)
    {
        halfmoveClock = 0;
    }
    else
    {
        ++halfmoveClock;
    }


    // ========================================================
    // FULL MOVE NUMBER
    // ========================================================

    if (movingColor == Color::Black)
    {
        ++fullmoveNumber;
    }


    // ========================================================
    // CHANGE TURN
    // ========================================================

    sideToMove =
        oppositeColor(sideToMove);
}


// ============================================================
// PRINT BOARD
// ============================================================

void Board::print() const
{
    std::cout << '\n';

    for (int rank = 7; rank >= 0; --rank)
    {
        std::cout << rank + 1 << "  ";

        for (int file = 0; file < 8; ++file)
        {
            const int square =
                rank * 8 + file;

            const Piece piece =
                squares[square];

            char symbol = '.';

            switch (piece.type)
            {
                case PieceType::Pawn:
                    symbol = 'P';
                    break;

                case PieceType::Knight:
                    symbol = 'N';
                    break;

                case PieceType::Bishop:
                    symbol = 'B';
                    break;

                case PieceType::Rook:
                    symbol = 'R';
                    break;

                case PieceType::Queen:
                    symbol = 'Q';
                    break;

                case PieceType::King:
                    symbol = 'K';
                    break;

                case PieceType::None:
                default:
                    symbol = '.';
                    break;
            }

            if (
                piece.color == Color::Black &&
                symbol != '.'
            )
            {
                symbol += ('a' - 'A');
            }

            std::cout << symbol << ' ';
        }

        std::cout << '\n';
    }

    std::cout << "\n   a b c d e f g h\n\n";
}