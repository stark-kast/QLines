import pygame
from config import BASE_GRID_SIZE, COLOR_LINE, COLOR_NODE, COLOR_MODAL_BORDER

def screen_to_world(sx, sy, pan_x, pan_y, zoom):
    return (sx - pan_x) / zoom, (pan_y - sy) / zoom

def world_to_screen(wx, wy, pan_x, pan_y, zoom):
    return wx * zoom + pan_x, pan_y - wy * zoom

def get_grid_node(sx, sy, pan_x, pan_y, zoom):
    wx, wy = screen_to_world(sx, sy, pan_x, pan_y, zoom)
    return (round(wx / BASE_GRID_SIZE), round(wy / BASE_GRID_SIZE))

def node_to_screen(node, pan_x, pan_y, zoom):
    return world_to_screen(node[0] * BASE_GRID_SIZE, node[1] * BASE_GRID_SIZE, pan_x, pan_y, zoom)

def point_to_segment_dist_sq(px, py, ax, ay, bx, by):
    vx, vy = bx - ax, by - ay
    if vx == 0 and vy == 0:
        return (px - ax)**2 + (py - ay)**2
    t = ((px - ax) * vx + (py - ay) * vy) / (vx * vx + vy * vy)
    t = max(0.0, min(1.0, t))
    return (px - (ax + t * vx))**2 + (py - (ay + t * vy))**2

def create_pattern_preview(pattern_lines, size=220, range_nodes=10):
    surf = pygame.Surface((size, size))
    surf.fill((18, 20, 26))
    center = size // 2
    step = size / (range_nodes * 2)

    for k in range(-range_nodes, range_nodes + 1):
        pos = center + k * step
        pygame.draw.line(surf, (30, 35, 45), (pos, 0), (pos, size), 1)
        pygame.draw.line(surf, (30, 35, 45), (0, pos), (size, pos), 1)

    pygame.draw.circle(surf, (255, 180, 0), (center, center), 3, 1)

    for (i1, j1), (i2, j2) in pattern_lines:
        ax = center + i1 * step
        ay = center - j1 * step
        bx = center + i2 * step
        by = center - j2 * step

        pygame.draw.line(surf, COLOR_LINE, (ax, ay), (bx, by), 2)
        pygame.draw.circle(surf, COLOR_NODE, (int(ax), int(ay)), 2)
        pygame.draw.circle(surf, COLOR_NODE, (int(bx), int(by)), 2)

    pygame.draw.rect(surf, COLOR_MODAL_BORDER, (0, 0, size, size), 1)
    return surf