import pygame
import random
import sys
import os
import heapq
import math

# --- Basic Settings ---
GRID_SIZE = 11 # Odd number is best for a central start
CELL_RADIUS = 30
MARGIN = 8
WIDTH = GRID_SIZE * (CELL_RADIUS * 2 + MARGIN) + MARGIN
HEIGHT = WIDTH + 60  # Add 60 pixels at the top for HUD
FPS = 30
MINIMAX_DEPTH = 3 # Adjust for difficulty/performance. 2-3 is a good balance.

# --- Colors (Sand/Cream Palette) ---
TILE_COLOR = (222, 203, 164)
BLOCKED_COLOR = (170, 140, 110)
BAIT_COLOR = (250, 230, 140)
BG_COLOR = (240, 230, 210)
TEXT_COLOR = (50, 30, 20)
BUTTON_COLOR = (120, 100, 90)

# --- Initialization ---
pygame.init()
pygame.mixer.init() # Initialize the mixer
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Trap The Cat - AI Version")
clock = pygame.time.Clock()
font = pygame.font.Font("assets/font/game-quotes.otf", 36)

# --- Asset Loading ---
def load_sound(filename):
    path = os.path.join("assets/sounds", filename)
    if os.path.exists(path):
        return pygame.mixer.Sound(path)
    return None


jump_sound = load_sound("cat_jump.wav")
mouse_dead_sound = load_sound("mouse_dead.wav")
place_block_sound = load_sound("place_block.wav")
place_mouse_sound = load_sound("place_mouse.wav")
cat_attack_sound = load_sound("cat_attack.wav")
background_music_sound = load_sound("background_music.wav")
victory_sound = load_sound("victory.wav")
defeat_sound = load_sound("defeat.wav")
cat_dead_sound = load_sound("cat_dead.wav")


# Loads a sequence of sprite images from a specific subfolder, optionally scaling them to a given size
def load_sprite_series(subfolder, count, base_path="assets/sprites/cat", size=None):
    images = []
    path_prefix = os.path.join(base_path, subfolder)
    if not os.path.exists(path_prefix):
        print(f"Warning: Sprite folder not found at {path_prefix}")
        return []
    for i in range(1, count + 1):
        img_path = os.path.join(path_prefix, f"{subfolder}{i}.png")
        if os.path.exists(img_path):
            img = pygame.image.load(img_path).convert_alpha()
            if size:
                images.append(pygame.transform.scale(img, size))
            else:
                images.append(pygame.transform.scale(img, (CELL_RADIUS * 2, CELL_RADIUS * 2)))
    return images

# Load all sprite series
attack_images = load_sprite_series("attack", 4)
run_images_original = load_sprite_series("run", 6)
idle_images_original = load_sprite_series("idle", 4)
dead_images = load_sprite_series("dead", 4)
mouse_idle_images = load_sprite_series("idle", 4, base_path="assets/sprites/mouse", size=(30, 30))

run_images_flipped = [pygame.transform.flip(img, True, False) for img in run_images_original]
idle_images_flipped = [pygame.transform.flip(img, True, False) for img in idle_images_original]

# --- Global Game State Variables ---
blocked = set()
bait = None
cat_pos = (GRID_SIZE // 2, GRID_SIZE // 2)
game_over = False
winner = None
bait_used = False
cat_attacked_this_turn = False
cat_has_attacked_in_game = False # New variable to track attack per game

# Animation variables
cat_idle_index = 0
last_idle_update = 0
cat_facing_left = False
cat_dead_animation_done = False
dead_final_sprite = None

# --- Helper Functions ---
def get_cell_center(cell):
    row, col = cell
    x = MARGIN + col * (2 * CELL_RADIUS + MARGIN) + CELL_RADIUS
    y = MARGIN + row * (2 * CELL_RADIUS + MARGIN) + CELL_RADIUS + 60
    return x, y

# --- Game Logic Functions ---
def get_cell_from_pos(pos):
    x, y = pos
    if y < 60: return None # Click was in HUD area
    col = (x - MARGIN) // (2 * CELL_RADIUS + MARGIN)
    row = (y - 60 - MARGIN) // (2 * CELL_RADIUS + MARGIN)
    if 0 <= row < GRID_SIZE and 0 <= col < GRID_SIZE:
        return (row, col)
    return None

# Returns the neighbors of a cell, ensuring they are within bounds
def get_neighbors(pos):
    r, c = pos
    directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]  # Up, Down, Left, Right
    return [(r + dr, c + dc) for dr, dc in directions if 0 <= r + dr < GRID_SIZE and 0 <= c + dc < GRID_SIZE]


# --- Edge Of Grid Detection ---
def is_at_edge(pos):
    r, c = pos
    return r == 0 or r == GRID_SIZE - 1 or c == 0 or c == GRID_SIZE - 1

# --- AI ALGORITHMS (A* and Minimax) ---

def a_star_search(start_pos, current_blocked, goal_pos=None):
    """
    Finds the shortest path using A*.
    If goal_pos is provided, it paths to that specific tile.
    If goal_pos is None, it paths to the nearest edge.
    """
    def h(pos):
        if goal_pos:
            # Manhattan distance to a specific goal tile
            return abs(pos[0] - goal_pos[0]) + abs(pos[1] - goal_pos[1])
        else:
            # Manhattan distance to the closest edge
            return min(pos[0], GRID_SIZE - 1 - pos[0], pos[1], GRID_SIZE - 1 - pos[1])

    if goal_pos is None and is_at_edge(start_pos):
        return [start_pos]

    open_set = [(h(start_pos), 0, start_pos)] # (f_score, g_score, pos)
    came_from = {}
    g_score = { (r,c): float('inf') for r in range(GRID_SIZE) for c in range(GRID_SIZE) }
    g_score[start_pos] = 0

    while open_set:
        _, current_g, current_pos = heapq.heappop(open_set)

        is_at_goal = (goal_pos and current_pos == goal_pos) or (goal_pos is None and is_at_edge(current_pos))
        if is_at_goal:
            path = []
            while current_pos in came_from:
                path.append(current_pos)
                current_pos = came_from[current_pos]
            path.append(start_pos)
            return path[::-1]

        for neighbor in get_neighbors(current_pos):
            if neighbor in current_blocked:
                continue
            
            tentative_g_score = current_g + 1
            if tentative_g_score < g_score[neighbor]:
                came_from[neighbor] = current_pos
                g_score[neighbor] = tentative_g_score
                f_score = tentative_g_score + h(neighbor)
                heapq.heappush(open_set, (f_score, tentative_g_score, neighbor))
    
    return None # No path found

def evaluate_board(current_cat_pos, current_blocked):
    """Evaluation function for Minimax. Always evaluates path to edge."""
    if is_at_edge(current_cat_pos):
        return 1000
    
    path = a_star_search(current_cat_pos, current_blocked, goal_pos=None) # Explicitly path to edge
    if path is None:
        return -1000
    
    return -len(path)

def minimax(depth, is_maximizing, cat_p, blocked_s, alpha, beta):
    """Minimax algorithm with alpha-beta pruning."""
    if depth == 0 or is_at_edge(cat_p) or a_star_search(cat_p, blocked_s, goal_pos=None) is None:
        return evaluate_board(cat_p, blocked_s)

    if is_maximizing: # Cat's turn
        max_eval = -math.inf
        for move in get_neighbors(cat_p):
            if move not in blocked_s:
                evaluation = minimax(depth - 1, False, move, blocked_s, alpha, beta)
                max_eval = max(max_eval, evaluation)
                alpha = max(alpha, evaluation)
                if beta <= alpha:
                    break
        return max_eval
    else: # Player's turn
        min_eval = math.inf
        possible_blocks = [n for n in get_neighbors(cat_p) if n not in blocked_s]
        if not possible_blocks:
             possible_blocks = [n for n in get_neighbors(get_neighbors(cat_p)[0]) if n not in blocked_s] if get_neighbors(cat_p) else []

        for block_pos in possible_blocks:
            new_blocked = blocked_s.copy()
            new_blocked.add(block_pos)
            evaluation = minimax(depth - 1, True, cat_p, new_blocked, alpha, beta)
            min_eval = min(min_eval, evaluation)
            beta = min(beta, evaluation)
            if beta <= alpha:
                break
        return min_eval if min_eval != math.inf else evaluate_board(cat_p, blocked_s)

# --- AI Decision Making ---
def find_best_move():
    """Determines the cat's best move using Minimax, returning the move and its score."""
    best_score = -math.inf
    best_moves = []
    
    for move in get_neighbors(cat_pos):
        if move not in blocked:
            score = minimax(MINIMAX_DEPTH, False, move, blocked, -math.inf, math.inf)
            if score > best_score:
                best_score = score
                best_moves = [move]
            elif score == best_score:
                best_moves.append(move)
    
    if best_moves:
        return random.choice(best_moves), best_score
    
    # Fallback if no moves are found
    return None, -1000


# --- Drawing and Animation ---

def draw_circle_with_shadow(color, pos, radius, shadow_offset=(3, 3)):
    shadow_color = (0, 0, 0, 50)
    surf = pygame.Surface((radius*2+shadow_offset[0], radius*2+shadow_offset[1]), pygame.SRCALPHA)
    pygame.draw.circle(surf, shadow_color, (radius + shadow_offset[0], radius + shadow_offset[1]), radius)
    pygame.draw.circle(surf, color, (radius, radius), radius)
    screen.blit(surf, (pos[0]-radius, pos[1]-radius))

# Draws the HUD at the top of the screen, showing bait and attack status
def draw_hud():
    pygame.draw.rect(screen, (100, 85, 70), (0, 0, WIDTH, 60))
    bait_text = "Bait: Used" if bait_used else "Bait: Available"
    attack_text = "Cat Attack: Used" if cat_has_attacked_in_game else "Cat Attack: Available"

    bait_surf = font.render(bait_text, True, TEXT_COLOR)
    attack_surf = font.render(attack_text, True, (200, 50, 50))
    
    screen.blit(bait_surf, (20, 15))
    screen.blit(attack_surf, (WIDTH - attack_surf.get_width() - 20, 15))


# Animates a sprite series at a given position with a delay between frames
def animate_sprite(images, pos, delay=150):
    for img in images:
        draw_board(draw_cat=False)
        screen.blit(img, img.get_rect(center=pos))
        pygame.display.flip()
        pygame.time.delay(delay)

# Animates the cat moving from start to end position, flipping images if needed
def animate_cat_move(start, end):
    global cat_facing_left
    sx, sy = get_cell_center(start)
    ex, ey = get_cell_center(end)
    
    dx = end[1] - start[1]
    if dx != 0:
        cat_facing_left = dx < 0

    # Determine which run images to use based on direction
    run_images = run_images_flipped if cat_facing_left else run_images_original
    if not run_images: return

    # Animate the cat running from start to end
    for i in range(len(run_images)):
        draw_board(draw_cat=False)
        ix = sx + (ex - sx) * i // len(run_images)
        iy = sy + (ey - sy) * i // len(run_images)
        screen.blit(run_images[i], run_images[i].get_rect(center=(ix, iy)))
        pygame.display.flip()
        pygame.time.delay(50)

# Draws the game board, including the cat, bait, and blocked tiles
def draw_board(draw_cat=True):
    global cat_idle_index, last_idle_update, cat_dead_animation_done, dead_final_sprite
    screen.fill(BG_COLOR)
    draw_hud()
    now = pygame.time.get_ticks()

    for row in range(GRID_SIZE):
        for col in range(GRID_SIZE):
            pos = get_cell_center((row, col))
            color = BLOCKED_COLOR if (row, col) in blocked else TILE_COLOR
            draw_circle_with_shadow(color, pos, CELL_RADIUS)

    # Draw the bait if it exists
    if bait and mouse_idle_images:
        pos = get_cell_center(bait)
        frame = (now // 300) % len(mouse_idle_images)
        screen.blit(mouse_idle_images[frame], mouse_idle_images[frame].get_rect(center=pos))

    if draw_cat:
        cat_center = get_cell_center(cat_pos)
        # Draw the cat based on its state
        if winner == 'player' and dead_images:
            if not cat_dead_animation_done:
                if cat_dead_sound:
                    cat_dead_sound.play()
                animate_sprite(dead_images, cat_center)
                dead_final_sprite = dead_images[-1]
                cat_dead_animation_done = True
            if dead_final_sprite:
                screen.blit(dead_final_sprite, dead_final_sprite.get_rect(center=cat_center))
        elif not game_over and idle_images_original:
            if now - last_idle_update > 300:
                cat_idle_index = (cat_idle_index + 1) % len(idle_images_original)
                last_idle_update = now
            images = idle_images_flipped if cat_facing_left else idle_images_original
            screen.blit(images[cat_idle_index], images[cat_idle_index].get_rect(center=cat_center))
        elif not game_over:
            draw_circle_with_shadow((255, 165, 0), cat_center, CELL_RADIUS - 5)


# --- Game Over Sounds ---
def handle_game_over_sounds():
    if background_music_sound:
        background_music_sound.stop()

    if winner == 'cat' and defeat_sound:
        defeat_sound.play()
    elif winner == 'player' and victory_sound:
        victory_sound.play()


# --- Game Over Screen ---
def draw_game_over():
    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 150))
    screen.blit(overlay, (0, 0))
    
    msg = "Cat Escaped!" if winner == 'cat' else "You Trapped The Cat!"
    text = font.render(msg, True, (255, 255, 255))
    text_rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 40))
    screen.blit(text, text_rect)
    
    button_rect = pygame.Rect(0, 0, 180, 60)
    button_rect.center = (WIDTH // 2, HEIGHT // 2 + 40)
    pygame.draw.rect(screen, BUTTON_COLOR, button_rect, border_radius=10)
    restart_text = font.render("Restart", True, TEXT_COLOR)
    screen.blit(restart_text, restart_text.get_rect(center=button_rect.center))
    return button_rect

def animate_attack_with_tile_flash(images, cat_pos, attacked_tile):
    cat_center = get_cell_center(cat_pos)
    tile_center = get_cell_center(attacked_tile)
    flash_colors = [(255, 50, 50), TILE_COLOR]  # Red and normal

    # --- Attack animation (cat + flashing tile) ---
    for i, img in enumerate(images):
        draw_board(draw_cat=False)

        # Flash tile (alternate color)
        flash_color = flash_colors[i % len(flash_colors)]
        pygame.draw.circle(screen, flash_color, tile_center, CELL_RADIUS)

        # Draw cat attacking
        screen.blit(img, img.get_rect(center=cat_center))

        pygame.display.flip()
        pygame.time.delay(100)

    # --- Faster fade-out of tile ---
    final_img = images[-1]
    for alpha in [200, 120, 60, 0]:  # Fewer steps
        draw_board(draw_cat=False)

        # Draw fading red over attacked tile
        s = pygame.Surface((CELL_RADIUS * 2, CELL_RADIUS * 2), pygame.SRCALPHA)
        pygame.draw.circle(s, (255, 50, 50, alpha), (CELL_RADIUS, CELL_RADIUS), CELL_RADIUS)
        screen.blit(s, (tile_center[0] - CELL_RADIUS, tile_center[1] - CELL_RADIUS))

        # Hold final cat image
        screen.blit(final_img, final_img.get_rect(center=cat_center))

        pygame.display.flip()
        pygame.time.delay(80)  # Shorter delay per frame




# --- Game Flow ---
def cat_turn():
    global cat_pos, winner, game_over, bait, cat_attacked_this_turn, blocked, cat_has_attacked_in_game
    
    cat_attacked_this_turn = False

    # 1. Bait-Seeking Logic (Smart Check)
    if bait:
        path_to_bait = a_star_search(cat_pos, blocked, goal_pos=bait)
        if path_to_bait and len(path_to_bait) > 1:
            future_pos = path_to_bait[1]

            # Check if the cat can reach the bait without being blocked by the player
            temp_blocked = blocked.copy()
            temp_blocked_after_player = temp_blocked.copy()

            # Simulate the player blocking the best move
            if future_pos == bait:
                bait_removed = True
            else:
                bait_removed = False

            # Check if the cat can escape after the player blocks
            escape_path = a_star_search(future_pos, temp_blocked)
            if escape_path and len(escape_path) > 1:
                dangerous_block = escape_path[1]
                temp_blocked_after_player.add(dangerous_block)

                escape_after_block = a_star_search(future_pos, temp_blocked_after_player)
                # If the cat can escape after the player blocks, it will go for the bait
                if escape_after_block:
                    if jump_sound: jump_sound.play()
                    animate_cat_move(cat_pos, future_pos)
                    cat_pos = future_pos

                    # Move complete, handle bait if needed
                    if bait and cat_pos == bait:
                        if mouse_dead_sound: mouse_dead_sound.play()
                        bait = None

                    if is_at_edge(cat_pos):
                        game_over = True
                        winner = 'cat'
                        handle_game_over_sounds()
                    return

    # 2. Decision Phase: Compare best move vs. best attack
    best_regular_move, best_move_score = find_best_move()

    best_attack_score = -math.inf
    block_to_attack = None
    if not cat_has_attacked_in_game:
        attackable = [n for n in get_neighbors(cat_pos) if n in blocked]
        if attackable:
            for block in attackable:
                temp_blocked = blocked.copy()
                temp_blocked.remove(block)
                current_attack_score = evaluate_board(cat_pos, temp_blocked)
                if current_attack_score > best_attack_score: 
                    best_attack_score = current_attack_score
                    block_to_attack = block

    # 3. Action Phase
    if block_to_attack is not None and best_attack_score > best_move_score:
        # Attack first
        if cat_attack_sound:
            cat_attack_sound.play()
        if attack_images:
            animate_attack_with_tile_flash(attack_images, cat_pos, block_to_attack)
        blocked.remove(block_to_attack)
        cat_attacked_this_turn = True
        cat_has_attacked_in_game = True

        # Recalculate best move after the block was removed
        best_regular_move, _ = find_best_move()

    # Then move
    new_pos = best_regular_move
    if new_pos:
        if jump_sound:
            jump_sound.play()
        animate_cat_move(cat_pos, new_pos)
        cat_pos = new_pos
    else:
        game_over = True
        winner = 'player'
        handle_game_over_sounds()
        return

    # --- Final bait check (NEW!) ---
    if bait and cat_pos == bait:
        if mouse_dead_sound:
            mouse_dead_sound.play()
        bait = None

    # Final win check
    if is_at_edge(cat_pos):
        game_over = True
        winner = 'cat'
        handle_game_over_sounds()

# --- Reset Game Function ---
# Resets the game state to start a new game
def reset_game():
    global blocked, bait, cat_pos, winner, game_over, bait_used, cat_has_attacked_in_game
    global cat_idle_index, last_idle_update, cat_facing_left, cat_attacked_this_turn
    global cat_dead_animation_done, dead_final_sprite
    
    blocked = set()
    bait = None
    cat_pos = (GRID_SIZE // 2, GRID_SIZE // 2)
    winner = None
    game_over = False
    bait_used = False
    cat_has_attacked_in_game = False # Reset the per-game attack flag
    
    cat_idle_index = 0
    last_idle_update = 0
    cat_facing_left = False
    cat_attacked_this_turn = False
    cat_dead_animation_done = False
    dead_final_sprite = None
    
    # Randomly place 10 blocked tiles, ensuring they are not on the cat's position
    while len(blocked) < 10:
        r = random.randint(0, GRID_SIZE - 1)
        c = random.randint(0, GRID_SIZE - 1)
        cell = (r, c)
        if cell != cat_pos and cell not in blocked:
            blocked.add(cell)
    
    if background_music_sound:
        background_music_sound.set_volume(0.8)  # Set volume to 80% 
        background_music_sound.play(loops=-1)   # Loop the music indefinitely

# --- Main Game Loop ---
def main():
    global running, player_turn, bait, bait_used, blocked, game_over
    running = True
    player_turn = True
    reset_game()

    while running:
        draw_board()
        restart_rect = None
        if game_over:
            restart_rect = draw_game_over()

        # Handle animations and updates
        pygame.display.flip()
        clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # Handle mouse clicks for player actions
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if game_over and restart_rect and restart_rect.collidepoint(event.pos):
                    reset_game()
                    player_turn = True
                    continue

                # Handle player actions only if it's the player's turn and the game is not over
                if player_turn and not game_over:
                    cell = get_cell_from_pos(event.pos)
                    if cell and cell != cat_pos and cell not in blocked and cell != bait:
                        mods = pygame.key.get_mods()
                        if mods & pygame.KMOD_SHIFT and not bait_used:
                            bait = cell
                            bait_used = True
                            if place_mouse_sound: place_mouse_sound.play()
                            player_turn = False
                        elif not (mods & pygame.KMOD_SHIFT):
                            blocked.add(cell)
                            if place_block_sound: place_block_sound.play()
                            player_turn = False

        # Handle AI turn if it's not the player's turn and the game is not over
        if not player_turn and not game_over:
            pygame.time.delay(100)
            cat_turn()
            player_turn = True

    pygame.quit()
    sys.exit()

if __name__ == '__main__':
    main()
