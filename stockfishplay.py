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

def main():
    print("\n=== CHESS ROBOT - STOCKFISH VS STOCKFISH ===")
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

        engine.configure({"UCI_LimitStrength": True, "UCI_Elo": difficulty})
        print(f"✅ Stockfish strength set to Elo {difficulty}")
    except Exception as e:
        print(f"❌ Could not open Stockfish: {e}")
        return

    move_history = []

    while not board.is_game_over():
        print("\n==============================")
        print("📋 Move History:", " ".join(move_history))
        print("==============================")
        print(board)

        print(f"\n🤖 Stockfish is thinking for {'White' if board.turn == chess.WHITE else 'Black'}...")
        stockfish_move = engine.play(board, chess.engine.Limit(time=1.0)).move
        print(f"🤖 Stockfish plays: {stockfish_move}")

        capture = board.is_capture(stockfish_move)
        moving_piece = board.piece_at(stockfish_move.from_square)
        captured_piece = board.piece_at(stockfish_move.to_square)
        piece_symbol = moving_piece.symbol() if moving_piece else 'p'
        captured_symbol = captured_piece.symbol() if captured_piece else None

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

    print("\n🏁 Game Over!")
    print(f"Result: {board.result()}")
    engine.quit()

if __name__ == "__main__":
    main()
