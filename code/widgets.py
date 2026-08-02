import pygame
from config import COLOR_INPUT_BG, COLOR_INPUT_BORDER, COLOR_INPUT_FOCUS

def get_clipboard_text():
    try:
        if not pygame.scrap.get_init():
            pygame.scrap.init()
        data = pygame.scrap.get(pygame.SCRAP_TEXT)
        if data:
            return data.decode("utf-8", errors="ignore").replace("\x00", "")
    except Exception:
        pass
    return ""

def set_clipboard_text(text):
    try:
        if not pygame.scrap.get_init():
            pygame.scrap.init()
        pygame.scrap.put(pygame.SCRAP_TEXT, text.encode("utf-8"))
    except Exception:
        pass


class InputField:
    def __init__(self, rect, font, text="", placeholder=""):
        self.rect = pygame.Rect(rect)
        self.font = font
        self.text = text
        self.placeholder = placeholder
        self.cursor = len(text)
        self.select_anchor = None
        self.active = False
        self.is_dragging = False
        self.scroll_x = 0
        self.blink_timer = 0

    def set_text(self, text):
        self.text = text
        self.cursor = len(text)
        self.select_anchor = None
        self.scroll_x = 0

    def focus(self):
        self.active = True
        self.select_anchor = 0
        self.cursor = len(self.text)
        self.blink_timer = pygame.time.get_ticks()

    def unfocus(self):
        self.active = False
        self.select_anchor = None
        self.is_dragging = False

    def get_selection(self):
        if self.select_anchor is not None and self.select_anchor != self.cursor:
            start = min(self.select_anchor, self.cursor)
            end = max(self.select_anchor, self.cursor)
            return start, end
        return None

    def delete_selection(self):
        sel = self.get_selection()
        if sel:
            start, end = sel
            self.text = self.text[:start] + self.text[end:]
            self.cursor = start
            self.select_anchor = None
            return True
        return False

    def insert_text(self, new_str):
        self.delete_selection()
        self.text = self.text[:self.cursor] + new_str + self.text[self.cursor:]
        self.cursor += len(new_str)

    def get_index_from_x(self, mouse_x):
        rel_x = mouse_x - (self.rect.x + 8) + self.scroll_x
        if rel_x <= 0:
            return 0
        
        best_idx = 0
        min_diff = float("inf")
        for i in range(len(self.text) + 1):
            w = self.font.size(self.text[:i])[0]
            diff = abs(w - rel_x)
            if diff < min_diff:
                min_diff = diff
                best_idx = i
        return best_idx

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                self.active = True
                self.cursor = self.get_index_from_x(event.pos[0])
                if pygame.key.get_mods() & pygame.KMOD_SHIFT:
                    if self.select_anchor is None:
                        self.select_anchor = self.cursor
                else:
                    self.select_anchor = self.cursor
                self.is_dragging = True
                self.blink_timer = pygame.time.get_ticks()
                return True
            else:
                self.unfocus()

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.is_dragging:
                self.is_dragging = False
                if self.select_anchor == self.cursor:
                    self.select_anchor = None

        elif event.type == pygame.MOUSEMOTION:
            if self.active and self.is_dragging:
                self.cursor = self.get_index_from_x(event.pos[0])

        elif event.type == pygame.KEYDOWN and self.active:
            self.blink_timer = pygame.time.get_ticks()
            mods = pygame.key.get_mods()
            ctrl = bool(mods & pygame.KMOD_CTRL)
            shift = bool(mods & pygame.KMOD_SHIFT)

            if ctrl and event.key == pygame.K_a:
                self.select_anchor = 0
                self.cursor = len(self.text)
                return True

            elif ctrl and event.key == pygame.K_c:
                sel = self.get_selection()
                if sel:
                    set_clipboard_text(self.text[sel[0]:sel[1]])
                return True

            elif ctrl and event.key == pygame.K_x:
                sel = self.get_selection()
                if sel:
                    set_clipboard_text(self.text[sel[0]:sel[1]])
                    self.delete_selection()
                return True

            elif ctrl and event.key == pygame.K_v:
                clip = get_clipboard_text()
                if clip:
                    clip = clip.replace("\r", "").replace("\n", "")
                    self.insert_text(clip)
                return True

            elif event.key == pygame.K_LEFT:
                if shift:
                    if self.select_anchor is None:
                        self.select_anchor = self.cursor
                    self.cursor = max(0, self.cursor - 1)
                else:
                    sel = self.get_selection()
                    if sel:
                        self.cursor = sel[0]
                        self.select_anchor = None
                    else:
                        self.cursor = max(0, self.cursor - 1)
                return True

            elif event.key == pygame.K_RIGHT:
                if shift:
                    if self.select_anchor is None:
                        self.select_anchor = self.cursor
                    self.cursor = min(len(self.text), self.cursor + 1)
                else:
                    sel = self.get_selection()
                    if sel:
                        self.cursor = sel[1]
                        self.select_anchor = None
                    else:
                        self.cursor = min(len(self.text), self.cursor + 1)
                return True

            elif event.key == pygame.K_HOME:
                if shift:
                    if self.select_anchor is None:
                        self.select_anchor = self.cursor
                else:
                    self.select_anchor = None
                self.cursor = 0
                return True

            elif event.key == pygame.K_END:
                if shift:
                    if self.select_anchor is None:
                        self.select_anchor = self.cursor
                else:
                    self.select_anchor = None
                self.cursor = len(self.text)
                return True

            elif event.key == pygame.K_BACKSPACE:
                if not self.delete_selection():
                    if self.cursor > 0:
                        self.text = self.text[:self.cursor - 1] + self.text[self.cursor:]
                        self.cursor -= 1
                return True

            elif event.key == pygame.K_DELETE:
                if not self.delete_selection():
                    if self.cursor < len(self.text):
                        self.text = self.text[:self.cursor] + self.text[self.cursor + 1:]
                return True

            else:
                if event.unicode and event.unicode.isprintable() and not ctrl:
                    self.insert_text(event.unicode)
                    return True

        return False

    def update_scroll(self):
        padding = 8
        avail_w = self.rect.w - padding * 2
        cursor_x = self.font.size(self.text[:self.cursor])[0]

        if cursor_x - self.scroll_x > avail_w:
            self.scroll_x = cursor_x - avail_w
        elif cursor_x - self.scroll_x < 0:
            self.scroll_x = cursor_x

        max_scroll = max(0, self.font.size(self.text)[0] - avail_w)
        self.scroll_x = max(0, min(self.scroll_x, max_scroll))

    def draw(self, surface):
        self.update_scroll()

        pygame.draw.rect(surface, COLOR_INPUT_BG, self.rect, border_radius=4)
        border_color = COLOR_INPUT_FOCUS if self.active else COLOR_INPUT_BORDER
        pygame.draw.rect(surface, border_color, self.rect, 1, border_radius=4)

        clip_rect = surface.get_clip()
        inner_rect = self.rect.inflate(-4, -4)
        surface.set_clip(inner_rect)

        start_x = self.rect.x + 8 - self.scroll_x
        start_y = self.rect.y + (self.rect.h - self.font.get_height()) // 2

        sel = self.get_selection()
        if sel:
            s_start, s_end = sel
            x1 = start_x + self.font.size(self.text[:s_start])[0]
            x2 = start_x + self.font.size(self.text[:s_end])[0]
            sel_rect = pygame.Rect(x1, self.rect.y + 4, x2 - x1, self.rect.h - 8)
            pygame.draw.rect(surface, (0, 100, 180), sel_rect)

        if self.text:
            text_surf = self.font.render(self.text, True, (255, 255, 255))
            surface.blit(text_surf, (start_x, start_y))
        elif self.placeholder and not self.active:
            ph_surf = self.font.render(self.placeholder, True, (100, 110, 130))
            surface.blit(ph_surf, (start_x, start_y))

        if self.active:
            time_since_blink = pygame.time.get_ticks() - self.blink_timer
            if (time_since_blink // 500) % 2 == 0:
                cur_x = start_x + self.font.size(self.text[:self.cursor])[0]
                pygame.draw.line(surface, COLOR_INPUT_FOCUS, (cur_x, self.rect.y + 5), (cur_x, self.rect.bottom - 5), 2)

        surface.set_clip(clip_rect)