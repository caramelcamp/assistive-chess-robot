# assistive-chess-robot
A semi-autonomous chess-playing robot using a Universal Robot arm, Robotiq Hand-E gripper, and Stockfish AI to enable physical gameplay and accessible human-robot interaction.

## 📌 Features

- 🧠 **Stockfish AI Integration** (adjustable ELO difficulty)
- ♟️ **Physical piece movement using UR robot and Robotiq gripper**
- 📋 **User inputs supported via terminal with move conversion from Black's perspective**
- ♻️ **Captures handled and removed from the board**
- 🏠 **Robot home/reset position between actions**
- 🪫 **Pre-programmed grip control via URScript (`GripperOpen.urp`, `GripperClose.urp`)**

---

## 🛠️ Technologies Used

- **Hardware:**  
  - Universal Robots UR5/UR3 (tested in LSU Robotics Lab)  
  - Robotiq Hand-E adaptive gripper  
  - Logitech HD Webcam (for optional computer vision)
- **Software:**  
  - Python 3  
  - [`python-chess`](https://pypi.org/project/python-chess/)  
  - Stockfish chess engine (locally installed)  
  - Tkinter (popup interface)
  - URScript over TCP/IP for robot communication

---

## 📂 Project Structure
chess-playing-robot/
│
├── physicalmove.py # Main game loop, robot control
├── stockfish_integration.py (optional separation of logic)
├── cameravision.py # Vision-based detection (optional)
│
├── /docs/ # Final report, summary, results
├── /images/ # Setup images, board screenshots
├── README.md
├── requirements.txt
└── LICENSE


---

## 🚀 How to Run

1. Install required Python packages:
   ```bash
   pip install python-chess
2. Clone this repository and set your Stockfish path in physicalmove.py.
3. Connect your robot and gripper to the same network. Update the IP and ports if needed:
  ROBOT_IP = "192.168.1.100"
  DASHBOARD_PORT = 29999
  SECONDARY_PORT = 30002
4. Run the main script:
   python physicalmove.py
