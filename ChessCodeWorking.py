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
square_spacing = 0.0486
hover_offset = 0.1
z_pick_low = 0.175
z_pick_medium = 0.20
z_pick_high = 0.225
z_grab_offset = 0.05
z_capture_drop_offset = 0.075
origin_x = 0.242
origin_y = -0.625
home_x = 0.3
home_y = -0.41
home_z = 0.5

# === Trash location
trash_x = origin_x + 0.1
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

def move_robot(x, y, z, s, mode="movel"):
    script = f"""
def move_to_point():
  {mode}(p[{x}, {y}, {z}, {tilt_rx}, {tilt_ry}, {tilt_rz}], a=1.2, v=0.25)
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

    move_robot(x, y, z_pick + hover_offset, s, mode="movel")
    move_robot(x, y, z_pick, s, mode="movel")
    load_and_run_program("GripperClose.urp")
    move_robot(x, y, z_pick + hover_offset + z_grab_offset, s, mode="movel")

    move_robot(trash_x, trash_y, z_pick + hover_offset + z_grab_offset, s, mode="movel")
    move_robot(trash_x, trash_y, z_pick + z_capture_drop_offset, s, mode="movel")
    load_and_run_program("GripperOpen.urp")
    move_robot(trash_x, trash_y, z_pick + hover_offset, s, mode="movel")
    #move_robot(home_x, home_y, home_z, s)
    s.close()

def pick_and_place(start_square, end_square, piece_symbol='p', capture=False, captured_piece_symbol=None):
    start_x, start_y = square_to_xy(start_square)
    end_x, end_y = square_to_xy(end_square)
    z_pick = determine_grab_height(piece_symbol)

    s = connect_to_secondary()
    if not s:
        return

    move_robot(home_x, home_y, home_z, s, mode="movel")

    if capture and captured_piece_symbol:
        s.close()
        capture_piece(end_square, captured_piece_symbol)
        s = connect_to_secondary()

    move_robot(start_x, start_y, z_pick + hover_offset, s, mode="movel")
    move_robot(start_x, start_y, z_pick, s, mode="movel")
    load_and_run_program("GripperClose.urp")
    move_robot(start_x, start_y, z_pick + hover_offset + z_grab_offset, s, mode="movel")

    move_robot(end_x, end_y, z_pick + hover_offset + z_grab_offset, s, mode="movel")
    move_robot(end_x, end_y, z_pick, s, mode="movel")
    load_and_run_program("GripperOpen.urp")
    move_robot(end_x, end_y, z_pick + hover_offset + z_grab_offset, s, mode="movel")
    move_robot(home_x, home_y, home_z, s, mode="movel")
    s.close()

def show_board_popup(board):
    board_window = tk.Toplevel()
    board_window.title("Chessboard Reference (Black's Perspective)")
    squares = [[None for _ in range(8)] for _ in range(8)]

    # Display file labels (a-h) from black's perspective
    for col in range(8):
        file_label = tk.Label(board_window, text=chr(ord('a') + col), bg="lightgray", width=4, height=1)
        file_label.grid(row=8, column=col)
    
    # Display rank labels (1-8) from black's perspective going up (bottom to top)
    for row in range(8):
        rank_label = tk.Label(board_window, text=str(8 - row), bg="lightgray", width=1, height=2)
        rank_label.grid(row=row, column=8)

    # Display board flipped for black's perspective
    for row in range(8):
        for col in range(8):
            # Convert from display position to actual board position
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
                    from_file = chr(ord('h') - (ord(move_input[0]) - ord('a')))
                    from_rank = 9 - int(move_input[1])  # Flip rank: 1->8, 2->7, etc.
                    to_file = chr(ord('h') - (ord(move_input[2]) - ord('a')))
                    to_rank = 9 - int(move_input[3])  # Flip rank: 1->8, 2->7, etc.
                    
                    standard_move = f"{from_file}{from_rank}{to_file}{to_rank}"
                    
                    try:
                        move = chess.Move.from_uci(standard_move)
                        if move in board.legal_moves:
                            # Standard notation worked
                            capture = board.is_capture(move)
                            moving_piece = board.piece_at(move.from_square)
                            captured_piece = board.piece_at(move.to_square)
                            piece_symbol = moving_piece.symbol() if moving_piece else 'p'
                            captured_symbol = captured_piece.symbol() if captured_piece else None

                            pick_and_place(str(move)[:2], str(move)[2:], piece_symbol, capture=capture, captured_piece_symbol=captured_symbol)
                            board.push(move)
                            move_history.append(standard_move)
                            valid_human_move = True
                            print(f"Your move a{move_input[0]}{move_input[1]}{move_input[2]}{move_input[3]} was executed as {standard_move} in standard notation")
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