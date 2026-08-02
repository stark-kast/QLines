import pygame

# --- Настройки окна ---
WIDTH, HEIGHT = 1200, 800
PATTERNS_FILE = "patterns.json"
BASE_GRID_SIZE = 50
PAN_SPEED = 8

# --- Цветовая палитра ---
COLOR_BG = (20, 22, 28)
COLOR_GRID = (35, 40, 52)
COLOR_GRID_DOTS = (55, 62, 78)
COLOR_LINE = (0, 210, 255)
COLOR_NODE = (255, 255, 255)
COLOR_HOVER_NODE = (255, 180, 0)
COLOR_SILHOUETTE = (255, 215, 0)
COLOR_SELECT_BOX = (255, 215, 0)
COLOR_MOVE_WHITE = (255, 255, 255)

# Модальные окна и ввод
COLOR_MODAL_BG = (28, 32, 42)
COLOR_MODAL_BORDER = (50, 58, 75)
COLOR_INPUT_BG = (20, 22, 28)
COLOR_INPUT_BORDER = (60, 70, 90)
COLOR_INPUT_FOCUS = (0, 210, 255)
COLOR_BTN = (45, 52, 68)
COLOR_BTN_HOVER = (60, 70, 92)
COLOR_BTN_ACCENT = (0, 160, 220)
COLOR_BTN_DANGER = (180, 45, 45)
COLOR_TEXT_NAME = (200, 200, 200)
COLOR_TEXT_AUTHOR = (120, 130, 150)
COLOR_ERROR = (255, 70, 70)

# Шрифты будут инициализированы после pygame.init()
font_sm = None
font_md = None
font_lg = None

def init_fonts():
    global font_sm, font_md, font_lg
    font_sm = pygame.font.SysFont("Consolas", 12)
    font_md = pygame.font.SysFont("Consolas", 14)
    font_lg = pygame.font.SysFont("Consolas", 18, bold=True)