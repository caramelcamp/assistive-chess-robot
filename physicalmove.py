import socket
import time
import chess
import chess.engine
import tkinter as tk
from tkinter import messagebox

# === Robot + Gripper Settings ===
ROBOT_IP = "192.168.1.100"
DASHBOARD_PORT = 29999
SECONDARY_PORT = 30002

# === Chessboard physical settings ===
square_spacing = 0.0474
hover_offset = 0.1
z_pick_low = 0.175
z_pick_medium = 0.20
z_pick_high = 0.225
z_grab_offset = 0.1
z_capture_drop_offset = 0.2
origin_x = 0.242
origin_y = -0.625
home_x = 0.3
home_y = -0.41
home_z = 0.5

# === Trash location
trash_x = origin_x - 0.1
trash_y = origin_y - 0.1

# === Wrist tilt
tilt_rx = 2.2
tilt_ry = 2.2
tilt_rz = 0.0

def connect_to_dashboard():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((ROBOT_IP, DASHBOARD_PORT))
    s.recv(1024)
    return s

def connect_to_secondary():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((ROBOT_IP, SECONDARY_PORT))
    return s

def send_urscript(script, s):
    s.send((script + "\n").encode('utf-8'))
    time.sleep(0.1)

def load_and_run_program(program_name):
    s = connect_to_dashboard()
    if not s:
        return False
    try:
        s.send(f"load {program_name}\n".encode())
        time.sleep(1.0)
        s.send(b"play\n")
        time.sleep(2.0)
        return True
    except Exception as e:
        print(f"❌ Dashboard error: {e}")
        return False
    finally:
        s.close()

def square_to_xy(square):
    file_index = ord(square[0]) - ord('a')
    rank_index = int(square[1]) - 1
    x = origin_x - (rank_index * square_spacing)
    y = origin_y + (file_index * square_spacing)
    return x, y

def move_robot(x, y, z, s):
    script = f"""
def move_to_point():
  movel(p[{x}, {y}, {z}, {tilt_rx}, {tilt_ry}, {tilt_rz}], a=1.2, v=0.25)
end
move_to_point()
"""
    send_urscript(script, s)
    time.sleep(2)

def determine_grab_height(piece_symbol):
    piece = piece_symbol.lower()
    if piece in ['q', 'k']:
        return z_pick_high
    elif piece == 'b':
        return z_pick_medium
    else:
        return z_pick_low

def capture_piece(square, piece_symbol):
    x, y = square_to_xy(square)
    z_pick = determine_grab_height(piece_symbol)

    s = connect_to_secondary()
    if not s:
        return

    move_robot(x, y, z_pick + hover_offset, s)
    time.sleep(0.3)
    move_robot(x, y, z_pick, s)
    load_and_run_program("GripperClose.urp")
    move_robot(x, y, z_pick + hover_offset + z_grab_offset, s)

    move_robot(trash_x, trash_y, z_pick + hover_offset + z_grab_offset, s)
    time.sleep(0.3)
    move_robot(trash_x, trash_y, z_pick + z_capture_drop_offset, s)
    load_and_run_program("GripperOpen.urp")
    move_robot(trash_x, trash_y, z_pick + hover_offset, s)
    s.close()

def pick_and_place(start_square, end_square, piece_symbol='p', capture=False, captured_piece_symbol=None):
    start_x, start_y = square_to_xy(start_square)
    end_x, end_y = square_to_xy(end_square)
    z_pick = determine_grab_height(piece_symbol)

    s = connect_to_secondary()
    if not s:
        return

    move_robot(home_x, home_y, home_z, s)

    if capture and captured_piece_symbol:
        s.close()
        capture_piece(end_square, captured_piece_symbol)
        s = connect_to_secondary()
    
    time.sleep(0.3)
    move_robot(start_x, start_y, z_pick + hover_offset, s)
    time.sleep(1)
    move_robot(start_x, start_y, z_pick, s)
    load_and_run_program("GripperClose.urp")
    move_robot(start_x, start_y, z_pick + hover_offset + z_grab_offset, s)
    time.sleep(0.3)
    move_robot(end_x, end_y, z_pick + hover_offset + z_grab_offset, s)
    time.sleep(0.3)
    move_robot(end_x, end_y, z_pick, s)
    load_and_run_program("GripperOpen.urp")
    move_robot(end_x, end_y, z_pick + hover_offset + z_grab_offset, s)
    move_robot(home_x, home_y, home_z, s)
    s.close()

current_board_window = None  # Global to track the window

def show_board_popup(board):
    global current_board_window

    # Close the previous popup if it exists
    if current_board_window is not None and current_board_window.winfo_exists():
        current_board_window.destroy()

    board_window = tk.Toplevel()
    current_board_window = board_window
    board_window.title("Chessboard Reference (Black's Perspective)")
    squares = [[None for _ in range(8)] for _ in range(8)]

    for col in range(8):
        file_label = tk.Label(board_window, text=chr(ord('a') + col), bg="lightgray", width=4, height=1)
        file_label.grid(row=8, column=col)
    
    for row in range(8):
        rank_label = tk.Label(board_window, text=str(8 - row), bg="lightgray", width=1, height=2)
        rank_label.grid(row=row, column=8)

    for row in range(8):
        for col in range(8):
            actual_file = chr(ord('h') - col)
            actual_rank = row + 1
            square_name = f"{actual_file}{actual_rank}"
            piece = board.piece_at(chess.parse_square(square_name))
            label = piece.symbol() if piece else ""
            color = "gray" if piece and piece.color == chess.BLACK else "white"
            bg = "#F0D9B5" if (row + col) % 2 == 0 else "#B58863"

            squares[row][col] = tk.Label(
                board_window, text=label, bg=bg, fg=color,
                font=("Arial", 12, "bold"), width=4, height=2, borderwidth=1, relief="solid"
            )
            squares[row][col].grid(row=row, column=col)


def print_coordinate_guide():
    print("\n=== COORDINATE REFERENCE GUIDE ===")
    print("Your perspective (Black's view):")
    print("  a b c d e f g h")
    for i in range(8, 0, -1):
        print(f"{i} . . . . . . . . {i}")
    print("  a b c d e f g h")
    
    print("\nStandard notation (White's view):")
    print("  h g f e d c b a")
    for i in range(8, 0, -1):
        print(f"{i} . . . . . . . . {i}")
    print("  h g f e d c b a")
    print("================================\n")

def main():
    print("\n=== CHESS ROBOT - PLAYING AS BLACK ===")
    print("When you enter moves, use YOUR perspective as if you're looking at the board from the BLACK side:")
    print("- Your pieces are at the bottom")
    print("- Files run a-h from left to right")
    print("- Ranks run 1-8 from bottom to top")
    print("- Example: When you type a2a4, it will move your pawn from what would be h7 to h5 in standard notation")
    print("============================================\n")
    
    print_coordinate_guide()
    
    stockfish_path = input("Enter the full path to your Stockfish executable: ").strip()
    board = chess.Board()

    try:
        engine = chess.engine.SimpleEngine.popen_uci(stockfish_path)

        print("\nChoose Stockfish difficulty (Elo 1350–2850):")
        print("Examples:")
        print(" - 1320 = Easy")
        print(" - 1600 = Intermediate")
        print(" - 2000 = Hard")
        print(" - 2500+ = Very Hard")

        while True:
            try:
                difficulty = int(input("Enter Elo rating (1320–2850): ").strip())
                if 1320 <= difficulty <= 2850:
                    break
                else:
                    print("❌ Please enter a number between 1320 and 2850.")
            except ValueError:
                print("❌ Invalid input. Please enter a number.")


        # Set difficulty level using UCI options
        engine.configure({"UCI_LimitStrength": True, "UCI_Elo": difficulty})
        print(f"✅ Stockfish strength set to Elo {difficulty}")

    except Exception as e:
        print(f"❌ Could not open Stockfish: {e}")
        return


    root = tk.Tk()
    root.withdraw()

    move_history = []

    while not board.is_game_over():
        print("\n==============================")
        print("📋 Move History:", " ".join(move_history))
        print("==============================")
        print(board)

        if board.turn == chess.WHITE:
            print("\n🤖 Stockfish is thinking...")
            stockfish_move = engine.play(board, chess.engine.Limit(time=1.0)).move
            print(f"🤖 Stockfish plays: {stockfish_move}")

            capture = board.is_capture(stockfish_move)
            moving_piece = board.piece_at(stockfish_move.from_square)
            captured_piece = board.piece_at(stockfish_move.to_square)
            piece_symbol = moving_piece.symbol() if moving_piece else 'p'
            captured_symbol = captured_piece.symbol() if captured_piece else None

            # Robot moves Stockfish's pieces
            if board.is_castling(stockfish_move):
                print("♜ Castling move detected!")
                if stockfish_move == chess.Move.from_uci("e1g1"):
                    pick_and_place("e1", "g1", "k")
                    pick_and_place("h1", "f1", "r")
                elif stockfish_move == chess.Move.from_uci("e1c1"):
                    pick_and_place("e1", "c1", "k")
                    pick_and_place("a1", "d1", "r")
                elif stockfish_move == chess.Move.from_uci("e8g8"):
                    pick_and_place("e8", "g8", "k")
                    pick_and_place("h8", "f8", "r")
                elif stockfish_move == chess.Move.from_uci("e8c8"):
                    pick_and_place("e8", "c8", "k")
                    pick_and_place("a8", "d8", "r")
            elif stockfish_move.promotion:
                print(f"👑 Promotion! Promoting pawn to {chess.piece_symbol(stockfish_move.promotion).upper()}")
                pick_and_place(str(stockfish_move)[:2], str(stockfish_move)[2:], piece_symbol, capture=capture, captured_piece_symbol=captured_symbol)
            else:
                pick_and_place(str(stockfish_move)[:2], str(stockfish_move)[2:], piece_symbol, capture=capture, captured_piece_symbol=captured_symbol)


            board.push(stockfish_move)
            move_history.append(str(stockfish_move))
        else:
            show_board_popup(board)
            print("\n🧠 Your Move (Black)")
            print("Enter your move from YOUR perspective (e.g., a2a4 to move your pawn forward two squares)")
            valid_human_move = False
            while not valid_human_move:
                move_input = input("Enter your move or 'q' to resign: ").strip().lower()
                if move_input == 'q':
                    print("🏳️ You resigned. Game Over.")
                    engine.quit()
                    return
                
                elif move_input == 'help':
                    print("\nYou can use either input method:")
                    print("1. Standard notation (board's internal coordinates)")
                    print("2. Visual board coordinates (as displayed in the popup)")
                    print("\nFor example, to move your queen's pawn forward two squares:")
                    print("- Standard notation: d7d5")
                    print("- Visual coordinates: e7e5")
                    
                    print("\nFrom your perspective (black):")
                    print("  a b c d e f g h")
                    print(" +-+-+-+-+-+-+-+-+")
                    for i in range(8, 0, -1):
                        print(f"{i}|{'|'.join(' ' for _ in range(8))}|{i}")
                        print(" +-+-+-+-+-+-+-+-+")
                    print("  a b c d e f g h\n")
                    
                    print("Maps to standard notation:")
                    print("  h g f e d c b a")
                    print(" +-+-+-+-+-+-+-+-+")
                    for i in range(8, 0, -1):
                        print(f"{i}|{'|'.join(' ' for _ in range(8))}|{i}")
                        print(" +-+-+-+-+-+-+-+-+")
                    print("  h g f e d c b a\n")
                    continue
                    
                # Handle input in either standard notation or display perspective
                elif len(move_input) == 4 and move_input[0] in 'abcdefgh' and move_input[2] in 'abcdefgh' and move_input[1] in '12345678' and move_input[3] in '12345678':
                    # Convert from player's perspective to standard notation
                    # For black perspective: a-h maps to h-a
                    # Flip file (a-h) and rank (1-8) from Black's perspective to standard
                    def black_to_standard(square):
                        file = chr(ord('h') - (ord(square[0]) - ord('a')))
                        rank = str(9 - int(square[1]))
                        return file + rank

                    from_square = move_input[:2]
                    to_square = move_input[2:4]
                    from_sq_std = black_to_standard(from_square)
                    to_sq_std = black_to_standard(to_square)

                    # Construct move string in standard notation
                    standard_move = from_sq_std + to_sq_std

                    # Check for pawn promotion after flipping coordinates
                    if board.piece_at(chess.parse_square(from_sq_std)) and \
                    board.piece_at(chess.parse_square(from_sq_std)).piece_type == chess.PAWN and \
                    (to_sq_std[1] == '1' or to_sq_std[1] == '8'):

                        print("🎉 Pawn promotion detected!")
                        print("Choose a piece to promote to: (q = Queen, r = Rook, b = Bishop, n = Knight)")
                        while True:
                            promo = input("Enter promotion piece (q/r/b/n): ").strip().lower()
                            if promo in ['q', 'r', 'b', 'n']:
                                standard_move += promo
                                break
                            else:
                                print("❌ Invalid choice. Please enter q, r, b, or n.")


                    try:
                        move = chess.Move.from_uci(standard_move)
                        if move in board.legal_moves:
                            print(f"Your move {move_input} was executed as {standard_move} in standard notation")
                            print("Please move the piece on the physical board.")

                            if board.is_castling(move):
                                print("♜ Castling detected! Please move both the king and the rook.")
                                if move == chess.Move.from_uci("d1f1"):
                                    print("➡️ Move king: e8 to f1")
                                    print("➡️ Move rook: a1 to e1")
                                elif move == chess.Move.from_uci("d1b1"):
                                    print("➡️ Move king: d1 to b1")
                                    print("➡️ Move rook: h1 to c1")

                            if move.promotion:
                                print(f"👑 You promoted to {chess.piece_symbol(move.promotion).upper()}. Swap the pawn physically.")

                            # ✅ Always push the move to update the turn
                            board.push(move)
                            move_history.append(str(move))
                            valid_human_move = True

                        else:
                            print(f"❌ Illegal move: {move_input} (converts to {standard_move} in standard notation)")
                    except Exception as e:
                        print(f"❌ Error processing move: {e}")
                else:
                    print("❌ Invalid input format. Please enter moves like 'a2a4' or 'e7e5' (type 'help' for more info)")

    print("\n🏋️ Game Over!")
    print(f"Result: {board.result()}")
    engine.quit()

if __name__ == "__main__":
    main()