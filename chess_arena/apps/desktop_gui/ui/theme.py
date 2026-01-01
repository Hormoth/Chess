# theme.py - Premium Dark Chess Theme

APP_QSS = """
/* ============================================
   CHESS ARENA - PREMIUM DARK THEME
   ============================================ */

/* Base Application */
QWidget {
    background: #0a0e14;
    color: #c5cdd9;
    font-family: "Segoe UI", "SF Pro Display", sans-serif;
    font-size: 13px;
}

/* ============================================
   TYPOGRAPHY
   ============================================ */
QLabel#Title {
    font-size: 26px;
    font-weight: 700;
    color: #ffffff;
    letter-spacing: 1px;
}

QLabel#Subtitle {
    font-size: 13px;
    color: #6b7d99;
}

QLabel#SectionHeader {
    font-size: 14px;
    font-weight: 600;
    color: #8fa4bf;
    padding: 8px 0;
    border-bottom: 1px solid #1a2332;
}

QLabel#PlayerName {
    font-size: 15px;
    font-weight: 600;
    color: #e8ecf2;
}

QLabel#Rating {
    font-size: 12px;
    color: #d4af37;
    font-weight: 600;
}

/* ============================================
   CARDS & PANELS
   ============================================ */
QFrame#Card {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #12181f, stop:1 #0d1117);
    border: 1px solid #1f2a3a;
    border-radius: 12px;
}

QFrame#BoardFrame {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #2a1810, stop:0.5 #1a1008, stop:1 #2a1810);
    border: 8px solid #1a1008;
    border-radius: 8px;
    padding: 4px;
}

QFrame#BoardEdge {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #3d2817, stop:0.3 #2a1810, stop:0.7 #2a1810, stop:1 #3d2817);
    border: 2px solid #4a3020;
    border-radius: 10px;
    padding: 12px;
}

QFrame#ChatPanel {
    background: #0d1117;
    border: 1px solid #1f2a3a;
    border-radius: 10px;
}

QFrame#MovesPanel {
    background: #0d1117;
    border: 1px solid #1f2a3a;
    border-radius: 10px;
}

QFrame#LeaderboardPanel {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #14191f, stop:1 #0d1117);
    border: 1px solid #d4af37;
    border-radius: 10px;
}

QFrame#CapturedPanel {
    background: rgba(13, 17, 23, 0.8);
    border: 1px solid #1f2a3a;
    border-radius: 6px;
    padding: 4px 8px;
}

QFrame#WaitingPanel {
    background: #0d1117;
    border: 1px solid #1f2a3a;
    border-radius: 10px;
}

/* ============================================
   BUTTONS
   ============================================ */
QPushButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #2d6a4f, stop:1 #1b4332);
    border: 1px solid #40916c;
    padding: 12px 20px;
    border-radius: 8px;
    font-weight: 600;
    font-size: 13px;
    color: #ffffff;
}

QPushButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #40916c, stop:1 #2d6a4f);
    border: 1px solid #52b788;
}

QPushButton:pressed {
    background: #1b4332;
}

QPushButton:disabled {
    background: #1a2332;
    border: 1px solid #2a3a4a;
    color: #4a5a6a;
}

QPushButton#PrimaryButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #d4af37, stop:1 #b8960c);
    border: 1px solid #e6c55a;
    color: #0a0e14;
}

QPushButton#PrimaryButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #e6c55a, stop:1 #d4af37);
}

QPushButton#DangerButton {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #9b2c2c, stop:1 #742a2a);
    border: 1px solid #c53030;
}

QPushButton#DangerButton:hover {
    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #c53030, stop:1 #9b2c2c);
}

/* ============================================
   INPUTS
   ============================================ */
QLineEdit {
    background: #0a0e14;
    border: 2px solid #1f2a3a;
    padding: 10px 14px;
    border-radius: 8px;
    font-size: 13px;
    color: #e8ecf2;
    selection-background-color: #2d6a4f;
}

QLineEdit:focus {
    border: 2px solid #40916c;
}

QLineEdit:disabled {
    background: #12181f;
    color: #4a5a6a;
}

QTextEdit {
    background: #0a0e14;
    border: 1px solid #1f2a3a;
    border-radius: 8px;
    padding: 8px;
    color: #c5cdd9;
    font-size: 12px;
}

QTextEdit:focus {
    border: 1px solid #40916c;
}

/* ============================================
   CHECKBOXES
   ============================================ */
QCheckBox {
    padding: 8px 0;
    spacing: 8px;
}

QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 2px solid #3a4a5a;
    background: #0a0e14;
}

QCheckBox::indicator:checked {
    background: #2d6a4f;
    border: 2px solid #40916c;
}

QCheckBox::indicator:hover {
    border: 2px solid #52b788;
}

/* ============================================
   SCROLLBARS
   ============================================ */
QScrollBar:vertical {
    background: #0d1117;
    width: 10px;
    border-radius: 5px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background: #2a3a4a;
    border-radius: 5px;
    min-height: 30px;
}

QScrollBar::handle:vertical:hover {
    background: #3a4a5a;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar:horizontal {
    background: #0d1117;
    height: 10px;
    border-radius: 5px;
}

QScrollBar::handle:horizontal {
    background: #2a3a4a;
    border-radius: 5px;
    min-width: 30px;
}

/* ============================================
   LIST WIDGETS
   ============================================ */
QListWidget {
    background: transparent;
    border: none;
    outline: none;
}

QListWidget::item {
    background: #12181f;
    border: 1px solid #1f2a3a;
    border-radius: 6px;
    padding: 10px 12px;
    margin: 3px 0;
}

QListWidget::item:hover {
    background: #1a2332;
    border: 1px solid #2a3a4a;
}

QListWidget::item:selected {
    background: #1b4332;
    border: 1px solid #40916c;
}

/* ============================================
   SPECIAL ELEMENTS
   ============================================ */
QLabel#MoveNumber {
    color: #4a5a6a;
    font-size: 11px;
    font-weight: 600;
}

QLabel#WhiteMove {
    color: #ffffff;
    font-size: 13px;
    font-weight: 500;
    font-family: "Consolas", "SF Mono", monospace;
}

QLabel#BlackMove {
    color: #a0a8b0;
    font-size: 13px;
    font-weight: 500;
    font-family: "Consolas", "SF Mono", monospace;
}

QLabel#ChatMessage {
    font-size: 12px;
    padding: 4px 0;
}

QLabel#SystemMessage {
    font-size: 11px;
    color: #6b7d99;
    font-style: italic;
}

QLabel#OnlineIndicator {
    color: #40916c;
    font-size: 11px;
}

QLabel#RankGold {
    color: #d4af37;
    font-weight: 700;
}

QLabel#RankSilver {
    color: #a8a8a8;
    font-weight: 600;
}

QLabel#RankBronze {
    color: #cd7f32;
    font-weight: 600;
}

/* ============================================
   CHESS BOARD SPECIFIC
   ============================================ */
#ChessBoardWidget {
    background: transparent;
}

QLabel#CapturedPiece {
    font-size: 20px;
    padding: 0 2px;
}

QLabel#TurnIndicator {
    font-size: 13px;
    font-weight: 600;
    padding: 6px 12px;
    border-radius: 6px;
}

QLabel#YourTurn {
    background: #2d6a4f;
    color: #ffffff;
}

QLabel#OpponentTurn {
    background: #1f2a3a;
    color: #8fa4bf;
}

/* ============================================
   TOOLTIPS
   ============================================ */
QToolTip {
    background: #1a2332;
    border: 1px solid #2a3a4a;
    border-radius: 6px;
    padding: 6px 10px;
    color: #e8ecf2;
    font-size: 12px;
}
"""

# Chess piece unicode characters
PIECE_SYMBOLS = {
    'K': '♔', 'Q': '♕', 'R': '♖', 'B': '♗', 'N': '♘', 'P': '♙',
    'k': '♚', 'q': '♛', 'r': '♜', 'b': '♝', 'n': '♞', 'p': '♟'
}

# Board colors
BOARD_COLORS = {
    'light': '#e8dcc4',      # Cream/tan for light squares
    'dark': '#7d945d',       # Muted green for dark squares (classic style)
    'highlight': '#f6f669',  # Yellow highlight for selected
    'legal': '#90EE90',      # Light green for legal moves
    'last_move': '#cdd26a',  # Subtle yellow for last move
    'check': '#ff6b6b',      # Red tint for check
}

# Alternative classic brown theme
BOARD_COLORS_BROWN = {
    'light': '#f0d9b5',
    'dark': '#b58863',
    'highlight': '#829769',
    'legal': '#829769',
    'last_move': '#cdd26a',
    'check': '#ff6b6b',
}
