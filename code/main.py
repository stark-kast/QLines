import pygame
import sys
import math

import config
from config import *
from widgets import InputField, set_clipboard_text
from storage import load_patterns, save_patterns_to_file, get_next_pattern_name
from geometry import (
    screen_to_world, world_to_screen, get_grid_node, node_to_screen,
    point_to_segment_dist_sq, create_pattern_preview
)

# --- Инициализация ---
pygame.init()
try:
    pygame.scrap.init()
except Exception:
    pass

screen = pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
pygame.display.set_caption("QLines v.1.0")
clock = pygame.time.Clock()
config.init_fonts()

# --- Состояние камеры ---
pan_x = WIDTH // 2
pan_y = HEIGHT // 2
zoom = 1.0

# --- Состояние данных и История (Undo/Redo) ---
lines = set()
undo_stack = []
redo_stack = []

def save_state():
    undo_stack.append(lines.copy())
    redo_stack.clear()

def undo():
    global lines
    if undo_stack:
        redo_stack.append(lines.copy())
        lines = undo_stack.pop()

def redo():
    global lines
    if redo_stack:
        undo_stack.append(lines.copy())
        lines = redo_stack.pop()

def center_camera_on_lines(target_lines):
    global pan_x, pan_y, zoom
    if not target_lines:
        pan_x = screen.get_width() // 2
        pan_y = screen.get_height() // 2
        zoom = 1.0
        return

    all_nodes = set()
    for n1, n2 in target_lines:
        all_nodes.add(n1)
        all_nodes.add(n2)

    min_i = min(n[0] for n in all_nodes)
    max_i = max(n[0] for n in all_nodes)
    min_j = min(n[1] for n in all_nodes)
    max_j = max(n[1] for n in all_nodes)

    center_i = (min_i + max_i) / 2.0
    center_j = (min_j + max_j) / 2.0

    pattern_w = max((max_i - min_i) * BASE_GRID_SIZE, BASE_GRID_SIZE)
    pattern_h = max((max_j - min_j) * BASE_GRID_SIZE, BASE_GRID_SIZE)

    W, H = screen.get_width(), screen.get_height()

    margin = 160
    zoom_x = (W - margin) / pattern_w if pattern_w > 0 else 1.0
    zoom_y = (H - margin) / pattern_h if pattern_h > 0 else 1.0
    zoom = max(0.4, min(min(zoom_x, zoom_y), 2.0))

    pan_x = W / 2.0 - center_i * BASE_GRID_SIZE * zoom
    pan_y = H / 2.0 - center_j * BASE_GRID_SIZE * zoom

# --- Состояния взаимодействия ---
is_panning = False
pan_start_mouse = (0, 0)
pan_start_pos = (0, 0)

drawing_start_node = None
current_hover_node = (0, 0)

select_mode = False
select_start_node = None
paste_mode = False
clipboard = []

move_mode = False
move_start_node = None
moving_active = False
moving_lines_rel = []
moving_origin_lines = []

# --- Модальные окна и Поля ввода ---
modal_state = None
save_error = ""
goto_error = ""
editing_pattern_idx = None

input_save_name = InputField((0, 0, 270, 32), config.font_md)
input_save_author = InputField((0, 0, 270, 32), config.font_md, placeholder="Неизвестен")
input_search = InputField((0, 0, 230, 30), config.font_sm, placeholder="Поиск...")

input_goto_x = InputField((0, 0, 100, 32), config.font_md, placeholder="0")
input_goto_y = InputField((0, 0, 100, 32), config.font_md, placeholder="0")

library_patterns = []
selected_pattern_idx = None
library_scroll_y = 0

def reset_all_modes():
    global select_mode, select_start_node, paste_mode, move_mode, move_start_node, moving_active, moving_origin_lines
    if moving_active:
        lines.update(moving_origin_lines)
    select_mode = False
    select_start_node = None
    paste_mode = False
    move_mode = False
    move_start_node = None
    moving_active = False
    moving_origin_lines = []

# --- Отрисовка UI Окон ---
def draw_save_modal_ui():
    mw, mh = 560, 300
    mx0, my0 = (screen.get_width() - mw) // 2, (screen.get_height() - mh) // 2

    pygame.draw.rect(screen, COLOR_MODAL_BG, (mx0, my0, mw, mh), border_radius=8)
    pygame.draw.rect(screen, COLOR_MODAL_BORDER, (mx0, my0, mw, mh), 2, border_radius=8)

    title_str = "Редактировать узор" if editing_pattern_idx is not None else "Сохранить узор"
    screen.blit(config.font_lg.render(title_str, True, (240, 240, 240)), (mx0 + 20, my0 + 15))

    if editing_pattern_idx is not None and editing_pattern_idx < len(library_patterns):
        prev_lines = library_patterns[editing_pattern_idx]["lines"]
    else:
        prev_lines = lines

    preview_surf = create_pattern_preview(prev_lines, size=220, range_nodes=10)
    screen.blit(preview_surf, (mx0 + 20, my0 + 55))

    screen.blit(config.font_sm.render("Название узора:", True, COLOR_TEXT_NAME), (mx0 + 260, my0 + 55))
    input_save_name.rect = pygame.Rect(mx0 + 260, my0 + 75, 270, 32)
    input_save_name.draw(screen)

    if save_error:
        screen.blit(config.font_sm.render(save_error, True, COLOR_ERROR), (mx0 + 260, my0 + 110))

    screen.blit(config.font_sm.render("Автор (необязательно):", True, COLOR_TEXT_NAME), (mx0 + 260, my0 + 130))
    input_save_author.rect = pygame.Rect(mx0 + 260, my0 + 150, 270, 32)
    input_save_author.draw(screen)

    btn_cancel = pygame.Rect(mx0 + 330, my0 + 245, 90, 35)
    btn_save = pygame.Rect(mx0 + 430, my0 + 245, 100, 35)

    pygame.draw.rect(screen, COLOR_BTN, btn_cancel, border_radius=4)
    pygame.draw.rect(screen, COLOR_BTN_ACCENT, btn_save, border_radius=4)

    screen.blit(config.font_md.render("Отмена", True, (200, 200, 200)), (btn_cancel.x + 18, btn_cancel.y + 8))
    screen.blit(config.font_md.render("Сохранить", True, (255, 255, 255)), (btn_save.x + 14, btn_save.y + 8))

def draw_library_modal_ui():
    mw, mh = 820, 580
    mx0, my0 = (screen.get_width() - mw) // 2, (screen.get_height() - mh) // 2

    pygame.draw.rect(screen, COLOR_MODAL_BG, (mx0, my0, mw, mh), border_radius=8)
    pygame.draw.rect(screen, COLOR_MODAL_BORDER, (mx0, my0, mw, mh), 2, border_radius=8)

    screen.blit(config.font_lg.render("Хранилище узоров", True, (240, 240, 240)), (mx0 + 20, my0 + 18))

    input_search.rect = pygame.Rect(mx0 + 560, my0 + 15, 230, 30)
    input_search.draw(screen)

    grid_surf = pygame.Surface((780, 430))
    grid_surf.fill(COLOR_MODAL_BG)

    search_query = input_search.text.lower()
    filtered = [
        (idx, p) for idx, p in enumerate(library_patterns)
        if search_query in p["name"].lower() or search_query in p["author"].lower()
    ]

    for item_i, (orig_idx, p) in enumerate(filtered):
        col = item_i % 4
        row = item_i // 4
        tx = col * 190 + 5
        ty = row * 215 - library_scroll_y

        if -210 <= ty <= 430:
            tile_rect = pygame.Rect(tx, ty, 180, 205)
            is_sel = (selected_pattern_idx == orig_idx)
            
            pygame.draw.rect(grid_surf, (35, 40, 54) if is_sel else (22, 25, 33), tile_rect, border_radius=6)
            pygame.draw.rect(grid_surf, COLOR_INPUT_FOCUS if is_sel else COLOR_MODAL_BORDER, tile_rect, 2 if is_sel else 1, border_radius=6)

            p_surf = create_pattern_preview(p["lines"], size=135, range_nodes=10)
            grid_surf.blit(p_surf, (tx + 22, ty + 10))

            grid_surf.blit(config.font_md.render(p["name"], True, COLOR_TEXT_NAME), (tx + 10, ty + 152))
            grid_surf.blit(config.font_sm.render(p["author"], True, COLOR_TEXT_AUTHOR), (tx + 10, ty + 175))

    screen.blit(grid_surf, (mx0 + 20, my0 + 60))

    btn_delete = pygame.Rect(mx0 + 260, my0 + 525, 100, 35)
    btn_edit   = pygame.Rect(mx0 + 370, my0 + 525, 100, 35)
    btn_cancel = pygame.Rect(mx0 + 480, my0 + 525, 90, 35)
    btn_insert = pygame.Rect(mx0 + 580, my0 + 525, 100, 35)
    btn_load   = pygame.Rect(mx0 + 690, my0 + 525, 100, 35)

    is_has_selected = (selected_pattern_idx is not None and selected_pattern_idx < len(library_patterns))

    pygame.draw.rect(screen, COLOR_BTN_DANGER if is_has_selected else COLOR_BTN, btn_delete, border_radius=4)
    pygame.draw.rect(screen, COLOR_BTN_ACCENT if is_has_selected else COLOR_BTN, btn_edit, border_radius=4)
    pygame.draw.rect(screen, COLOR_BTN, btn_cancel, border_radius=4)
    pygame.draw.rect(screen, COLOR_BTN_ACCENT if is_has_selected else COLOR_BTN, btn_insert, border_radius=4)
    pygame.draw.rect(screen, COLOR_BTN_ACCENT if is_has_selected else COLOR_BTN, btn_load, border_radius=4)

    screen.blit(config.font_md.render("Удалить", True, (255, 255, 255) if is_has_selected else (100, 100, 100)), (btn_delete.x + 22, btn_delete.y + 8))
    screen.blit(config.font_md.render("Изменить", True, (255, 255, 255) if is_has_selected else (100, 100, 100)), (btn_edit.x + 18, btn_edit.y + 8))
    screen.blit(config.font_md.render("Отмена", True, (200, 200, 200)), (btn_cancel.x + 18, btn_cancel.y + 8))
    screen.blit(config.font_md.render("Вставить", True, (255, 255, 255) if is_has_selected else (100, 100, 100)), (btn_insert.x + 18, btn_insert.y + 8))
    screen.blit(config.font_md.render("Загрузить", True, (255, 255, 255) if is_has_selected else (100, 100, 100)), (btn_load.x + 14, btn_load.y + 8))

def draw_goto_modal_ui():
    mw, mh = 360, 210
    mx0, my0 = (screen.get_width() - mw) // 2, (screen.get_height() - mh) // 2

    pygame.draw.rect(screen, COLOR_MODAL_BG, (mx0, my0, mw, mh), border_radius=8)
    pygame.draw.rect(screen, COLOR_MODAL_BORDER, (mx0, my0, mw, mh), 2, border_radius=8)

    screen.blit(config.font_lg.render("Перемещение", True, (240, 240, 240)), (mx0 + 20, my0 + 15))

    # X
    screen.blit(config.font_md.render("X:", True, COLOR_TEXT_NAME), (mx0 + 30, my0 + 65))
    input_goto_x.rect = pygame.Rect(mx0 + 60, my0 + 60, 100, 32)
    input_goto_x.draw(screen)

    # Y
    screen.blit(config.font_md.render("Y:", True, COLOR_TEXT_NAME), (mx0 + 180, my0 + 65))
    input_goto_y.rect = pygame.Rect(mx0 + 210, my0 + 60, 100, 32)
    input_goto_y.draw(screen)

    if goto_error:
        screen.blit(config.font_sm.render(goto_error, True, COLOR_ERROR), (mx0 + 30, my0 + 105))

    btn_cancel = pygame.Rect(mx0 + 80, my0 + 150, 90, 35)
    btn_move   = pygame.Rect(mx0 + 180, my0 + 150, 150, 35)

    pygame.draw.rect(screen, COLOR_BTN, btn_cancel, border_radius=4)
    pygame.draw.rect(screen, COLOR_BTN_ACCENT, btn_move, border_radius=4)

    screen.blit(config.font_md.render("Отмена", True, (200, 200, 200)), (btn_cancel.x + 18, btn_cancel.y + 8))
    screen.blit(config.font_md.render("Переместиться", True, (255, 255, 255)), (btn_move.x + 14, btn_move.y + 8))

def process_save_action():
    global modal_state, save_error, library_patterns, editing_pattern_idx
    existing = load_patterns()
    name_to_save = input_save_name.text.strip()
    
    if not name_to_save:
        save_error = "Имя не может быть пустым!"
        return

    if any(i != editing_pattern_idx and p["name"] == name_to_save for i, p in enumerate(existing)):
        save_error = "Узор с таким именем уже существует!"
        return

    if editing_pattern_idx is not None and editing_pattern_idx < len(existing):
        existing[editing_pattern_idx]["name"] = name_to_save
        existing[editing_pattern_idx]["author"] = input_save_author.text.strip() or "Неизвестен"
        save_patterns_to_file(existing)
        library_patterns = load_patterns()
        editing_pattern_idx = None
        modal_state = "LIBRARY"
    else:
        new_pattern = {
            "name": name_to_save,
            "author": input_save_author.text.strip() or "Неизвестен",
            "lines": [list(l) for l in lines]
        }
        existing.append(new_pattern)
        save_patterns_to_file(existing)
        modal_state = None

def process_goto_action():
    global modal_state, goto_error, pan_x, pan_y
    try:
        tx = float(input_goto_x.text.strip() or "0")
        ty = float(input_goto_y.text.strip() or "0")
        
        W, H = screen.get_width(), screen.get_height()
        pan_x = W / 2.0 - tx * BASE_GRID_SIZE * zoom
        pan_y = H / 2.0 + ty * BASE_GRID_SIZE * zoom
        modal_state = None
    except ValueError:
        goto_error = "Введите корректные числа!"

# --- Главный цикл ---
running = True

while running:
    mouse_pos = pygame.mouse.get_pos()
    current_hover_node = get_grid_node(*mouse_pos, pan_x, pan_y, zoom)

    if modal_state is None:
        keys = pygame.key.get_pressed()
        if keys[pygame.K_w]: pan_y += PAN_SPEED
        if keys[pygame.K_s]: pan_y -= PAN_SPEED
        if keys[pygame.K_a]: pan_x += PAN_SPEED
        if keys[pygame.K_d]: pan_x -= PAN_SPEED

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        # --- Сохранение ---
        elif modal_state == "SAVE":
            input_save_name.handle_event(event)
            input_save_author.handle_event(event)

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if editing_pattern_idx is not None:
                        modal_state = "LIBRARY"
                        editing_pattern_idx = None
                    else:
                        modal_state = None
                elif event.key == pygame.K_TAB:
                    if input_save_name.active:
                        input_save_name.unfocus()
                        input_save_author.focus()
                    else:
                        input_save_author.unfocus()
                        input_save_name.focus()
                elif event.key == pygame.K_RETURN:
                    process_save_action()

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                mw, mh = 560, 300
                mx0, my0 = (screen.get_width() - mw) // 2, (screen.get_height() - mh) // 2

                if pygame.Rect(mx0 + 330, my0 + 245, 90, 35).collidepoint(mx, my):
                    if editing_pattern_idx is not None:
                        modal_state = "LIBRARY"
                        editing_pattern_idx = None
                    else:
                        modal_state = None
                elif pygame.Rect(mx0 + 430, my0 + 245, 100, 35).collidepoint(mx, my):
                    process_save_action()

        # --- Перемещение ---
        elif modal_state == "GOTO":
            input_goto_x.handle_event(event)
            input_goto_y.handle_event(event)

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    modal_state = None
                elif event.key == pygame.K_TAB:
                    if input_goto_x.active:
                        input_goto_x.unfocus()
                        input_goto_y.focus()
                    else:
                        input_goto_y.unfocus()
                        input_goto_x.focus()
                elif event.key == pygame.K_RETURN:
                    process_goto_action()

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                mw, mh = 360, 210
                mx0, my0 = (screen.get_width() - mw) // 2, (screen.get_height() - mh) // 2

                btn_cancel = pygame.Rect(mx0 + 80, my0 + 150, 90, 35)
                btn_move   = pygame.Rect(mx0 + 180, my0 + 150, 150, 35)

                if btn_cancel.collidepoint(mx, my):
                    modal_state = None
                elif btn_move.collidepoint(mx, my):
                    process_goto_action()

        # --- Хранилище ---
        elif modal_state == "LIBRARY":
            input_search.handle_event(event)

            mw, mh = 820, 580
            mx0, my0 = (screen.get_width() - mw) // 2, (screen.get_height() - mh) // 2
            grid_rect = pygame.Rect(mx0 + 20, my0 + 60, 780, 430)

            search_query = input_search.text.lower()
            filtered = [
                (idx, p) for idx, p in enumerate(library_patterns)
                if search_query in p["name"].lower() or search_query in p["author"].lower()
            ]

            if event.type == pygame.MOUSEWHEEL:
                total_rows = math.ceil(len(filtered) / 4)
                max_scroll = max(0, total_rows * 215 - 430)
                library_scroll_y = max(0, min(library_scroll_y - event.y * 30, max_scroll))

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE and not input_search.active:
                    modal_state = None

            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos

                if grid_rect.collidepoint(mx, my):
                    for item_i, (orig_idx, p) in enumerate(filtered):
                        col = item_i % 4
                        row = item_i // 4
                        tile_x = mx0 + 25 + col * 190
                        tile_y = my0 + 60 + row * 215 - library_scroll_y
                        tile_rect = pygame.Rect(tile_x, tile_y, 180, 205)

                        if tile_rect.collidepoint(mx, my):
                            selected_pattern_idx = orig_idx
                            break

                else:
                    btn_delete = pygame.Rect(mx0 + 260, my0 + 525, 100, 35)
                    btn_edit   = pygame.Rect(mx0 + 370, my0 + 525, 100, 35)
                    btn_cancel = pygame.Rect(mx0 + 480, my0 + 525, 90, 35)
                    btn_insert = pygame.Rect(mx0 + 580, my0 + 525, 100, 35)
                    btn_load   = pygame.Rect(mx0 + 690, my0 + 525, 100, 35)

                    if btn_delete.collidepoint(mx, my):
                        if selected_pattern_idx is not None and selected_pattern_idx < len(library_patterns):
                            library_patterns.pop(selected_pattern_idx)
                            save_patterns_to_file(library_patterns)
                            library_patterns = load_patterns()
                            selected_pattern_idx = None

                    elif btn_edit.collidepoint(mx, my):
                        if selected_pattern_idx is not None and selected_pattern_idx < len(library_patterns):
                            p = library_patterns[selected_pattern_idx]
                            input_save_name.set_text(p["name"])
                            input_save_author.set_text(p["author"])
                            save_error = ""
                            editing_pattern_idx = selected_pattern_idx
                            input_save_name.focus()
                            modal_state = "SAVE"

                    elif btn_cancel.collidepoint(mx, my):
                        modal_state = None

                    elif btn_insert.collidepoint(mx, my):
                        if selected_pattern_idx is not None and selected_pattern_idx < len(library_patterns):
                            p = library_patterns[selected_pattern_idx]
                            raw_lines = p["lines"]
                            if raw_lines:
                                all_nodes = set()
                                for (i1, j1), (i2, j2) in raw_lines:
                                    all_nodes.add((i1, j1))
                                    all_nodes.add((i2, j2))
                                max_i = max(n[0] for n in all_nodes)
                                min_j = min(n[1] for n in all_nodes)

                                clipboard = [
                                    ((i1 - max_i, j1 - min_j), (i2 - max_i, j2 - min_j))
                                    for (i1, j1), (i2, j2) in raw_lines
                                ]
                                reset_all_modes()
                                paste_mode = True
                            modal_state = None

                    elif btn_load.collidepoint(mx, my):
                        if selected_pattern_idx is not None and selected_pattern_idx < len(library_patterns):
                            p = library_patterns[selected_pattern_idx]
                            save_state()
                            lines = set(tuple(sorted([tuple(l[0]), tuple(l[1])])) for l in p["lines"])
                            center_camera_on_lines(lines)
                            reset_all_modes()
                            modal_state = None

        # --- События основного холста ---
        else:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_z and (event.mod & pygame.KMOD_CTRL):
                    reset_all_modes()
                    undo()

                elif event.key == pygame.K_y and (event.mod & pygame.KMOD_CTRL):
                    reset_all_modes()
                    redo()

                elif event.key == pygame.K_s and (event.mod & pygame.KMOD_CTRL):
                    patterns_data = load_patterns()
                    input_save_name.set_text(get_next_pattern_name(patterns_data))
                    input_save_author.set_text("")
                    save_error = ""
                    editing_pattern_idx = None
                    input_save_name.focus()
                    modal_state = "SAVE"

                elif event.key == pygame.K_a and (event.mod & pygame.KMOD_CTRL):
                    library_patterns = load_patterns()
                    selected_pattern_idx = None
                    input_search.set_text("")
                    library_scroll_y = 0
                    modal_state = "LIBRARY"

                elif event.key == pygame.K_f and (event.mod & pygame.KMOD_CTRL):
                    input_goto_x.set_text("0")
                    input_goto_y.set_text("0")
                    goto_error = ""
                    input_goto_x.focus()
                    modal_state = "GOTO"

                elif event.key == pygame.K_m:
                    if move_mode or moving_active:
                        reset_all_modes()
                    else:
                        reset_all_modes()
                        move_mode = True

                elif event.key == pygame.K_c:
                    if select_mode or paste_mode:
                        reset_all_modes()
                    else:
                        reset_all_modes()
                        select_mode = True

                elif event.key == pygame.K_r:
                    save_state()
                    reset_all_modes()
                    lines.clear()

                elif event.key == pygame.K_ESCAPE:
                    reset_all_modes()

            elif event.type == pygame.MOUSEWHEEL:
                old_zoom = zoom
                zoom *= 1.15 if event.y > 0 else 1 / 1.15
                zoom = max(0.15, min(zoom, 10.0))
                mx, my = mouse_pos
                pan_x = mx - (mx - pan_x) * (zoom / old_zoom)
                pan_y = my - (my - pan_y) * (zoom / old_zoom)

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button in (2, 3):
                    if select_mode or paste_mode or move_mode or moving_active:
                        reset_all_modes()
                    else:
                        is_panning = True
                        pan_start_mouse = mouse_pos
                        pan_start_pos = (pan_x, pan_y)

                elif event.button == 1:
                    if select_mode:
                        select_start_node = current_hover_node
                    elif move_mode:
                        if not moving_active:
                            move_start_node = current_hover_node
                        else:
                            save_state()
                            t_i, t_j = current_hover_node
                            for (r1_i, r1_j), (r2_i, r2_j) in moving_lines_rel:
                                t1, t2 = (t_i + r1_i, t_j + r1_j), (t_i + r2_i, t_j + r2_j)
                                if t1 != t2:
                                    lines.add(tuple(sorted([t1, t2])))
                            moving_active = False
                            move_mode = False
                    elif paste_mode and clipboard:
                        save_state()
                        t_i, t_j = current_hover_node
                        for (r1_i, r1_j), (r2_i, r2_j) in clipboard:
                            t1, t2 = (t_i + r1_i, t_j + r1_j), (t_i + r2_i, t_j + r2_j)
                            if t1 != t2:
                                lines.add(tuple(sorted([t1, t2])))
                    else:
                        drawing_start_node = current_hover_node

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button in (2, 3):
                    is_panning = False

                elif event.button == 1:
                    if select_mode and select_start_node is not None:
                        sn, en = select_start_node, current_hover_node
                        min_i, max_i = min(sn[0], en[0]), max(sn[0], en[0])
                        min_j, max_j = min(sn[1], en[1]), max(sn[1], en[1])

                        selected = [
                            ((i1, j1), (i2, j2)) for (i1, j1), (i2, j2) in lines
                            if (min_i <= i1 <= max_i and min_j <= j1 <= max_j) and
                               (min_i <= i2 <= max_i and min_j <= j2 <= max_j)
                        ]

                        if selected:
                            clipboard = [
                                ((i1 - max_i, j1 - min_j), (i2 - max_i, j2 - min_j))
                                for (i1, j1), (i2, j2) in selected
                            ]
                            paste_mode = True
                        select_mode = False
                        select_start_node = None

                    elif move_mode and not moving_active and move_start_node is not None:
                        sn, en = move_start_node, current_hover_node
                        min_i, max_i = min(sn[0], en[0]), max(sn[0], en[0])
                        min_j, max_j = min(sn[1], en[1]), max(sn[1], en[1])

                        selected = [
                            ((i1, j1), (i2, j2)) for (i1, j1), (i2, j2) in lines
                            if (min_i <= i1 <= max_i and min_j <= j1 <= max_j) and
                               (min_i <= i2 <= max_i and min_j <= j2 <= max_j)
                        ]

                        if selected:
                            save_state()
                            moving_origin_lines = selected.copy()
                            for l in selected:
                                lines.remove(l)

                            moving_lines_rel = [
                                ((i1 - max_i, j1 - min_j), (i2 - max_i, j2 - min_j))
                                for (i1, j1), (i2, j2) in selected
                            ]
                            moving_active = True
                        else:
                            move_mode = False
                        move_start_node = None

                    elif not paste_mode and not move_mode and drawing_start_node is not None:
                        end_node = current_hover_node
                        if drawing_start_node != end_node:
                            save_state()
                            lines.add(tuple(sorted([drawing_start_node, end_node])))
                        else:
                            connected = [l for l in lines if drawing_start_node in l]
                            if connected:
                                save_state()
                                for l in connected:
                                    lines.remove(l)
                            else:
                                m_wx, m_wy = screen_to_world(*mouse_pos, pan_x, pan_y, zoom)
                                closest_line = None
                                min_dist_px = 12.0
                                for l in lines:
                                    (i1, j1), (i2, j2) = l
                                    ax, ay = i1 * BASE_GRID_SIZE, j1 * BASE_GRID_SIZE
                                    bx, by = i2 * BASE_GRID_SIZE, j2 * BASE_GRID_SIZE
                                    dist_px = math.sqrt(point_to_segment_dist_sq(m_wx, m_wy, ax, ay, bx, by)) * zoom
                                    if dist_px < min_dist_px:
                                        min_dist_px = dist_px
                                        closest_line = l
                                if closest_line:
                                    save_state()
                                    lines.remove(closest_line)
                        drawing_start_node = None

            elif event.type == pygame.MOUSEMOTION:
                if is_panning:
                    pan_x = pan_start_pos[0] + (mouse_pos[0] - pan_start_mouse[0])
                    pan_y = pan_start_pos[1] + (mouse_pos[1] - pan_start_mouse[1])

    # --- Отрисовка ---
    screen.fill(COLOR_BG)

    W, H = screen.get_width(), screen.get_height()
    min_wx, max_wy = screen_to_world(0, 0, pan_x, pan_y, zoom)
    max_wx, min_wy = screen_to_world(W, H, pan_x, pan_y, zoom)
    min_i, max_i = math.floor(min_wx / BASE_GRID_SIZE) - 1, math.ceil(max_wx / BASE_GRID_SIZE) + 1
    min_j, max_j = math.floor(min_wy / BASE_GRID_SIZE) - 1, math.ceil(max_wy / BASE_GRID_SIZE) + 1

    current_grid_px = BASE_GRID_SIZE * zoom

    if current_grid_px > 8:
        for i in range(min_i, max_i):
            sx, _ = world_to_screen(i * BASE_GRID_SIZE, 0, pan_x, pan_y, zoom)
            pygame.draw.line(screen, COLOR_GRID, (sx, 0), (sx, H), 1)
        for j in range(min_j, max_j):
            _, sy = world_to_screen(0, j * BASE_GRID_SIZE, pan_x, pan_y, zoom)
            pygame.draw.line(screen, COLOR_GRID, (0, sy), (W, sy), 1)

    if current_grid_px > 18:
        dot_r = max(1, int(2 * zoom))
        for i in range(min_i, max_i):
            for j in range(min_j, max_j):
                sx, sy = world_to_screen(i * BASE_GRID_SIZE, j * BASE_GRID_SIZE, pan_x, pan_y, zoom)
                pygame.draw.circle(screen, COLOR_GRID_DOTS, (int(sx), int(sy)), dot_r)

    node_r = max(3, int(4 * zoom))
    line_w = max(2, int(3 * zoom))

    for nodeA, nodeB in lines:
        ax, ay = node_to_screen(nodeA, pan_x, pan_y, zoom)
        bx, by = node_to_screen(nodeB, pan_x, pan_y, zoom)
        pygame.draw.line(screen, COLOR_LINE, (ax, ay), (bx, by), line_w)
        pygame.draw.circle(screen, COLOR_NODE, (int(ax), int(ay)), node_r)
        pygame.draw.circle(screen, COLOR_NODE, (int(bx), int(by)), node_r)

    if not paste_mode and not select_mode and not move_mode and drawing_start_node is not None:
        ax, ay = node_to_screen(drawing_start_node, pan_x, pan_y, zoom)
        bx, by = node_to_screen(current_hover_node, pan_x, pan_y, zoom)
        pygame.draw.line(screen, COLOR_LINE, (ax, ay), (bx, by), max(1, line_w - 1))
        pygame.draw.circle(screen, COLOR_HOVER_NODE, (int(ax), int(ay)), node_r + 1)
        pygame.draw.circle(screen, COLOR_HOVER_NODE, (int(bx), int(by)), node_r + 1)

    if select_mode and select_start_node is not None:
        ax, ay = node_to_screen(select_start_node, pan_x, pan_y, zoom)
        bx, by = node_to_screen(current_hover_node, pan_x, pan_y, zoom)
        pygame.draw.rect(screen, COLOR_SELECT_BOX, (min(ax, bx), min(ay, by), abs(ax - bx), abs(ay - by)), 1)

    if move_mode and not moving_active and move_start_node is not None:
        ax, ay = node_to_screen(move_start_node, pan_x, pan_y, zoom)
        bx, by = node_to_screen(current_hover_node, pan_x, pan_y, zoom)
        pygame.draw.rect(screen, COLOR_MOVE_WHITE, (min(ax, bx), min(ay, by), abs(ax - bx), abs(ay - by)), 1)

    if paste_mode and clipboard:
        t_i, t_j = current_hover_node
        for (r1_i, r1_j), (r2_i, r2_j) in clipboard:
            ax, ay = node_to_screen((t_i + r1_i, t_j + r1_j), pan_x, pan_y, zoom)
            bx, by = node_to_screen((t_i + r2_i, t_j + r2_j), pan_x, pan_y, zoom)
            pygame.draw.line(screen, COLOR_SILHOUETTE, (ax, ay), (bx, by), line_w)
            pygame.draw.circle(screen, COLOR_SILHOUETTE, (int(ax), int(ay)), node_r)
            pygame.draw.circle(screen, COLOR_SILHOUETTE, (int(bx), int(by)), node_r)

    if moving_active and moving_lines_rel:
        t_i, t_j = current_hover_node
        for (r1_i, r1_j), (r2_i, r2_j) in moving_lines_rel:
            ax, ay = node_to_screen((t_i + r1_i, t_j + r1_j), pan_x, pan_y, zoom)
            bx, by = node_to_screen((t_i + r2_i, t_j + r2_j), pan_x, pan_y, zoom)
            pygame.draw.line(screen, COLOR_MOVE_WHITE, (ax, ay), (bx, by), line_w)
            pygame.draw.circle(screen, COLOR_MOVE_WHITE, (int(ax), int(ay)), node_r)
            pygame.draw.circle(screen, COLOR_MOVE_WHITE, (int(bx), int(by)), node_r)

    hover_sx, hover_sy = node_to_screen(current_hover_node, pan_x, pan_y, zoom)
    h_color = COLOR_MOVE_WHITE if (move_mode or moving_active) else (COLOR_SILHOUETTE if paste_mode else COLOR_HOVER_NODE)
    pygame.draw.circle(screen, h_color, (int(hover_sx), int(hover_sy)), node_r + 2, 1)

    if moving_active:
        status_str = "ПЕРЕМЕЩЕНИЕ (Клик ЛКМ - поставить, Esc - отмена)"
    elif move_mode:
        status_str = "РЕЖИМ ПЕРЕМЕЩЕНИЯ (Зажмите ЛКМ и выделите)"
    elif paste_mode:
        status_str = "РЕЖИМ ВСТАВКИ (Клик ЛКМ - вставить)"
    elif select_mode:
        status_str = "РЕЖИМ ВЫДЕЛЕНИЯ (Зажмите ЛКМ и выделите)"
    else:
        status_str = "РЕЖИМ РИСОВАНИЯ"

    coords_str = f"X: {current_hover_node[0]}, Y: {current_hover_node[1]}"
    info_text = f"{coords_str} | Линий: {len(lines)} | Ctrl+Z: Отмена | Ctrl+Y: Повтор | {status_str}"
    controls_text = "WASD: Навигация | ЛКМ: Рисовать | M: Переместить | C: Выделить | Ctrl+S: Сохранить | Ctrl+A: Хранилище | Ctrl+F: Перейти"
    screen.blit(config.font_md.render(info_text, True, (200, 200, 200)), (10, 10))
    screen.blit(config.font_sm.render(controls_text, True, (120, 130, 150)), (10, 32))

    if modal_state is not None:
        if modal_state == "LIBRARY" or (modal_state == "SAVE" and editing_pattern_idx is not None):
            overlay1 = pygame.Surface((W, H), pygame.SRCALPHA)
            overlay1.fill((0, 0, 0, 160))
            screen.blit(overlay1, (0, 0))
            draw_library_modal_ui()

        if modal_state == "SAVE":
            overlay2 = pygame.Surface((W, H), pygame.SRCALPHA)
            overlay2.fill((0, 0, 0, 160))
            screen.blit(overlay2, (0, 0))
            draw_save_modal_ui()

        if modal_state == "GOTO":
            overlay3 = pygame.Surface((W, H), pygame.SRCALPHA)
            overlay3.fill((0, 0, 0, 160))
            screen.blit(overlay3, (0, 0))
            draw_goto_modal_ui()

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()
