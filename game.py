import pygame
import random
import sys
import os

# --- הגדרות בסיס ---
GRID_SIZE = 10
CELL_RADIUS = 30
MARGIN = 8
WIDTH = GRID_SIZE * (CELL_RADIUS * 2 + MARGIN) + MARGIN
HEIGHT = WIDTH + 60  # נוסיף 60 פיקסלים למעלה עבור HUD
FPS = 30

# צבעים בגווני חול-שמנת
PURPLE = (222, 203, 164)
BLOCKED_COLOR = (170, 140, 110)
BAIT_COLOR = (250, 230, 140)
BG_COLOR = (240, 230, 210)
TEXT_COLOR = (50, 30, 20)
BUTTON_COLOR = (120, 100, 90)

# --- אתחול ---
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Trap The Cat")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 48)

# --- טוענים ספרייטים ---
def load_sprite_series(subfolder, count, base_path="sprites/cat", size=None):
    path_prefix = os.path.join(base_path, subfolder)
    return [
        pygame.transform.scale(
            pygame.image.load(os.path.join(path_prefix, f"{subfolder}{i}.png")),
            size if size else (CELL_RADIUS * 2, CELL_RADIUS * 2)
        )
        for i in range(1, count + 1)
    ]

attack_images = load_sprite_series("attack", 4)
run_images_original = load_sprite_series("run", 6)
idle_images_original = load_sprite_series("idle", 4)
dead_images = load_sprite_series("dead", 4)
mouse_idle_images = load_sprite_series("idle", 4, base_path="sprites/mouse", size=(30, 30))

run_images_flipped = [pygame.transform.flip(img, True, False) for img in run_images_original]
idle_images_flipped = [pygame.transform.flip(img, True, False) for img in idle_images_original]

# --- משתנים גלובליים ---
attack_message_time = 0
cat_just_attacked = False
cat_attacked_once = False
cat_idle_index = 0
last_idle_update = 0
cat_facing_left = False
cat_dead_animation_done = False
dead_final_sprite = None
mouse_used = False

blocked = set()
bait = None
cat_pos = [GRID_SIZE // 2, GRID_SIZE // 2]
game_over = False
winner = None

# --- פונקציות עזר ---
def get_cell_pos(cell):
    row, col = cell
    x = MARGIN + col * (2 * CELL_RADIUS + MARGIN) + CELL_RADIUS
    y = MARGIN + row * (2 * CELL_RADIUS + MARGIN) + CELL_RADIUS + 60  # שורה זו עודכנה
    return x, y


def draw_circle_with_shadow(color, pos, radius, shadow_offset=(4, 4)):
    shadow_color = (10, 10, 10)
    pygame.draw.circle(screen, shadow_color, (pos[0] + shadow_offset[0], pos[1] + shadow_offset[1]), radius)
    pygame.draw.circle(screen, color, pos, radius)

def draw_restart_button():
    text = font.render("Restart", True, TEXT_COLOR)
    rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 80))
    pygame.draw.rect(screen, BUTTON_COLOR, rect.inflate(20, 10))
    screen.blit(text, rect)
    return rect

def draw_hud():
    pygame.draw.rect(screen, (80, 70, 60), (0, 0, WIDTH, 60))  # רקע כהה

    bait_text = "Bait used" if mouse_used else "Bait available"
    attack_text = "Cat attacked" if cat_attacked_once else "Cat passive"

    bait_surface = font.render(bait_text, True, TEXT_COLOR)
    attack_surface = font.render(attack_text, True, TEXT_COLOR)

    screen.blit(bait_surface, (20, 10))
    screen.blit(attack_surface, (WIDTH - attack_surface.get_width() - 20, 10))

    bait_text = "Bait used" if mouse_used else "Bait available"
    attack_text = "Cat attacked" if cat_attacked_once else "Cat passive"

    bait_surface = font.render(bait_text, True, TEXT_COLOR)
    attack_surface = font.render(attack_text, True, TEXT_COLOR)

    screen.blit(bait_surface, (20, 10))
    screen.blit(attack_surface, (WIDTH - attack_surface.get_width() - 20, 10))

def draw_board(draw_cat=True):
    global cat_idle_index, last_idle_update, cat_dead_animation_done

    screen.fill(BG_COLOR)
    draw_hud()
    now = pygame.time.get_ticks()

    for row in range(GRID_SIZE):
        for col in range(GRID_SIZE):
            pos = get_cell_pos((row, col))
            draw_circle_with_shadow(PURPLE, pos, CELL_RADIUS)
            if (row, col) in blocked:
                draw_circle_with_shadow(BLOCKED_COLOR, pos, CELL_RADIUS)

    if bait:
        pos = get_cell_pos(bait)
        frame = (now // 300) % len(mouse_idle_images)
        screen.blit(mouse_idle_images[frame], mouse_idle_images[frame].get_rect(center=pos))

    if draw_cat:
        if winner == 'player':
            if not cat_dead_animation_done:
                for img in dead_images:
                    draw_board(draw_cat=False)
                    screen.blit(img, img.get_rect(center=get_cell_pos(cat_pos)))
                    pygame.display.flip()
                    pygame.time.delay(200)
                globals()['dead_final_sprite'] = dead_images[-1]
                cat_dead_animation_done = True
            if dead_final_sprite:
                screen.blit(dead_final_sprite, dead_final_sprite.get_rect(center=get_cell_pos(cat_pos)))
        elif not game_over:
            if now - last_idle_update > 300:
                cat_idle_index = (cat_idle_index + 1) % len(idle_images_original)
                last_idle_update = now
            img = idle_images_flipped[cat_idle_index] if cat_facing_left else idle_images_original[cat_idle_index]
            screen.blit(img, img.get_rect(center=get_cell_pos(cat_pos)))

    if cat_just_attacked and now - attack_message_time < 4000:
        text = font.render("Cat attacked!", True, (255, 100, 100))
        screen.blit(text, (WIDTH // 2 - text.get_width() // 2, HEIGHT - 60))

    if game_over:
        msg = "Cat escaped!" if winner == 'cat' else "You trapped the cat!"
        text = font.render(msg, True, TEXT_COLOR)
        screen.blit(text, text.get_rect(center=(WIDTH // 2, HEIGHT // 2)))
        restart_rect = draw_restart_button()
        pygame.display.flip()
        return restart_rect

    pygame.display.flip()
    return None

def get_neighbors(pos):
    r, c = pos
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]
    return [(r+dr, c+dc) for dr, dc in directions if 0 <= r+dr < GRID_SIZE and 0 <= c+dc < GRID_SIZE]

def animate_cat_move(start, end):
    global cat_facing_left
    sx, sy = get_cell_pos(start)
    ex, ey = get_cell_pos(end)
    steps = len(run_images_original)
    dx = end[1] - start[1]
    cat_facing_left = dx < 0 if dx != 0 else cat_facing_left
    run_images = run_images_flipped if cat_facing_left else run_images_original

    for i in range(steps):
        draw_board(draw_cat=False)
        ix = sx + (ex - sx) * i // steps
        iy = sy + (ey - sy) * i // steps
        img = run_images[i]
        screen.blit(img, img.get_rect(center=(ix, iy)))
        pygame.display.flip()
        pygame.time.delay(50)

def cat_move():
    global cat_pos, winner, game_over, bait
    options = [n for n in get_neighbors(cat_pos) if n not in blocked]
    if not options:
        game_over = True
        winner = 'player'
        return

    new_pos = bait if bait in options else random.choice(options)
    if bait == new_pos:
        bait = None

    animate_cat_move(tuple(cat_pos), new_pos)
    cat_pos[0], cat_pos[1] = new_pos

    if cat_pos[0] in [0, GRID_SIZE - 1] or cat_pos[1] in [0, GRID_SIZE - 1]:
        game_over = True
        winner = 'cat'

def cat_attack():
    global attack_message_time, cat_just_attacked, cat_attacked_once
    if cat_attacked_once:
        return
    neighbors = get_neighbors(cat_pos)
    attackable = [n for n in neighbors if n in blocked]
    if attackable and random.random() < 0.25:
        to_remove = random.choice(attackable)
        pos = get_cell_pos(cat_pos)
        for img in attack_images:
            draw_board(draw_cat=False)
            screen.blit(img, img.get_rect(center=pos))
            pygame.display.flip()
            pygame.time.delay(100)
        blocked.remove(to_remove)
        attack_message_time = pygame.time.get_ticks()
        cat_just_attacked = True
        cat_attacked_once = True

def reset_game():
    global blocked, bait, cat_pos, winner, game_over
    global cat_idle_index, last_idle_update, cat_facing_left
    global cat_just_attacked, cat_attacked_once, cat_dead_animation_done, dead_final_sprite
    global mouse_used
    mouse_used = False
    blocked = set()
    bait = None
    cat_pos = [GRID_SIZE // 2, GRID_SIZE // 2]
    winner = None
    game_over = False
    cat_idle_index = 0
    last_idle_update = 0
    cat_facing_left = False
    cat_just_attacked = False
    cat_attacked_once = False
    cat_dead_animation_done = False
    dead_final_sprite = None

# --- לולאת המשחק ---
running = True
player_turn = True

while running:
    restart_rect = draw_board()
    clock.tick(FPS)

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        if event.type == pygame.MOUSEBUTTONDOWN:
            x, y = pygame.mouse.get_pos()
            col = x // (2 * CELL_RADIUS + MARGIN)
            row = (y - 60) // (2 * CELL_RADIUS + MARGIN)
            if y >= 60 and 0 <= row < GRID_SIZE and 0 <= col < GRID_SIZE:

                if game_over and restart_rect and restart_rect.collidepoint(x, y):
                    reset_game()
                    continue
                if player_turn and not game_over:
                    if pygame.key.get_mods() & pygame.KMOD_SHIFT and not mouse_used:
                        bait = (row, col)
                        mouse_used = True
                    elif (row, col) != tuple(cat_pos) and (row, col) not in blocked:
                        blocked.add((row, col))
                        player_turn = False

    if not player_turn and not game_over:
        cat_attack()
        cat_move()
        cat_just_attacked = False
        player_turn = True

pygame.quit()
sys.exit()
