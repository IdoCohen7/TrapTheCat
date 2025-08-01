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
TILE_COLOR = (240, 225, 200)
BLOCKED_COLOR = (160, 130, 100)
BAIT_COLOR = (250, 230, 140)
BG_COLOR = (255, 0, 0)
TEXT_COLOR = (50, 30, 20)
BUTTON_COLOR = (120, 100, 90)

# --- Initialization ---
pygame.init()
pygame.mixer.init() # Initialize the mixer
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Trap The Cat - AI Version")
clock = pygame.time.Clock()
font = pygame.font.Font("assets/font/game-quotes.otf", 36)

# --- Load Assets ---
grass_bg = pygame.image.load("assets/images/grass.png").convert()
grass_bg = pygame.transform.scale(grass_bg, (WIDTH, HEIGHT))
cat_logo = pygame.image.load("assets/images/cat_logo.png").convert_alpha()
cat_logo = pygame.transform.scale(cat_logo, (50, 50))  
cat_laugh_image = pygame.image.load("assets/images/cat_win.png").convert_alpha()
cat_laugh_image = pygame.transform.scale(cat_laugh_image, (200, 200))  # אתה יכול לשנות את הגודל
cat_sad_image = pygame.image.load("assets/images/cat_lose.png").convert_alpha()
cat_sad_image = pygame.transform.scale(cat_sad_image, (200, 200))  # אתה יכול לשנות את הגודל
# --- Asset Loading ---
def load_sound(filename):
    path = os.path.join("assets/sounds", filename)
    if os.path.exists(path):
        return pygame.mixer.Sound(path)
    return None

# Load all sounds
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
cat_ignored_bait = False
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
        # Check if we reached the goal
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
            # Calculate tentative g_score
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

    # shadow
    pygame.draw.circle(surf, shadow_color, (radius + shadow_offset[0], radius + shadow_offset[1]), radius)

    # main circle
    tile_color = color + (230,)  
    pygame.draw.circle(surf, tile_color, (radius, radius), radius)

    screen.blit(surf, (pos[0]-radius, pos[1]-radius))


# Draws the HUD at the top of the screen, showing bait and attack status
def draw_hud():
    pygame.draw.rect(screen, (100, 85, 70), (0, 0, WIDTH, 60))
    
    bait_text = "Bait: Used" if bait_used else "Bait: Available"
    attack_text = "Attack: Used" if cat_has_attacked_in_game else "Attack: Available"

    bait_surf = font.render(bait_text, True, (220, 220, 220))    
    attack_surf = font.render(attack_text, True, (200, 40, 40))  

    # Draw bait and attack status
    screen.blit(bait_surf, (20, 15))
    screen.blit(attack_surf, (WIDTH - attack_surf.get_width() - 20, 15))

    # Draw cat logo
    if cat_logo:  
        logo_x = (WIDTH - cat_logo.get_width()) // 2
        logo_y = (60 - cat_logo.get_height()) // 2
        screen.blit(cat_logo, (logo_x, logo_y))



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
    screen.blit(grass_bg, (0, 0))
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
    
    # Draw the game over logo
    if winner == 'cat' and cat_laugh_image:
        image_rect = cat_laugh_image.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 100))
        screen.blit(cat_laugh_image, image_rect)
    elif winner == 'player' and cat_sad_image:
        image_rect = cat_sad_image.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 100))
        screen.blit(cat_sad_image, image_rect)

    # Draw the winner message
    msg = "Cat Escaped!" if winner == 'cat' else "You Trapped The Cat!"
    text = font.render(msg, True, (255, 255, 255))
    text_rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 60))
    screen.blit(text, text_rect)

    # Draw the restart button
    button_rect = pygame.Rect(0, 0, 180, 60)
    button_rect.center = (WIDTH // 2, HEIGHT // 2 + 130)
    mouse_pos = pygame.mouse.get_pos()
    hover = button_rect.collidepoint(mouse_pos)

    color = (150, 120, 110) if hover else BUTTON_COLOR
    pygame.draw.rect(screen, color, button_rect, border_radius=10)
    pygame.draw.rect(screen, (255, 255, 255), button_rect, 2, border_radius=10)

    restart_text = font.render("Restart", True, TEXT_COLOR)
    screen.blit(restart_text, restart_text.get_rect(center=button_rect.center))
    
    return button_rect

def bait_is_a_trap(cat_pos, bait_pos, blocked_set):
    """
    Simulates the path to the bait and checks if it leads to a trap.
    Returns True if bait appears dangerous (likely to trap the cat), else False.
    """
    path_to_bait = a_star_search(cat_pos, blocked_set, goal_pos=bait_pos)
    if not path_to_bait or len(path_to_bait) < 2:
        return False  # No path or already on bait – not enough info

    # Simulate the path step by step
    for step in path_to_bait[1:]:  # Skip current position
        temp_blocked = blocked_set.copy()

        # Try to simulate a "smart" player blocking the cat's next move
        escape_path = a_star_search(step, temp_blocked)
        if not escape_path or len(escape_path) < 2:
            return True  # Already trapped

        dangerous_step = escape_path[1]
        temp_blocked.add(dangerous_step)

        # Recheck escape options after hypothetical block
        escape_after_block = a_star_search(step, temp_blocked)
        if not escape_after_block:
            return True  # No way out after bait step

    return False  # Passed all checks – bait seems safe


def animate_attack_with_tile_flash(images, cat_pos, attacked_tile):
    cat_center = get_cell_center(cat_pos)
    tile_center = get_cell_center(attacked_tile)
    flash_colors = [(255, 50, 50), TILE_COLOR]  # Red and normal

    # --- Attack animation (cat + flashing tile) ---
    for i, img in enumerate(images):
    # --- Flash the screen white for a brief moment ---
        if i == 0:
            flash = pygame.Surface((WIDTH, HEIGHT))
            flash.fill((255, 255, 255))
            flash.set_alpha(100)
            screen.blit(flash, (0, 0))
            pygame.display.flip()
            pygame.time.delay(30)

        draw_board(draw_cat=False)

        # Flash tile
        flash_color = flash_colors[i % len(flash_colors)]
        pygame.draw.circle(screen, flash_color, tile_center, CELL_RADIUS)

        # Draw attacking cat
        dx = attacked_tile[1] - cat_pos[1]
        flip = dx < 0
        img_to_draw = pygame.transform.flip(img, True, False) if flip else img
        screen.blit(img_to_draw, img_to_draw.get_rect(center=cat_center))
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

def score_bait_path(cat_pos, bait_pos, blocked_set):
    """
    Returns a numeric score evaluating how safe/smart it is to go for the bait.
    Higher score = better opportunity, negative = risky trap.
    """
    path = a_star_search(cat_pos, blocked_set, goal_pos=bait_pos)
    if not path or len(path) < 2:
        return -1000  # Unreachable or too close to judge

    total_risk = 0
    total_escape = 0
    steps_checked = 0

    for step in path[1:]:
        temp_blocked = blocked_set.copy()
        escape_path = a_star_search(step, temp_blocked)
        if not escape_path or len(escape_path) < 2:
            total_risk += 1
            continue

        dangerous_block = escape_path[1]
        temp_blocked.add(dangerous_block)
        escape_after = a_star_search(step, temp_blocked)
        if not escape_after:
            total_risk += 1
        else:
            total_escape += 1

        steps_checked += 1

    if steps_checked == 0:
        return -1000  # No real info

    score = (total_escape - total_risk) * 10 - len(path)  # prefer short, safe paths
    return score



def cat_turn():
    global cat_pos, cat_ignored_bait, winner, game_over, bait, cat_attacked_this_turn, blocked, cat_has_attacked_in_game

    cat_attacked_this_turn = False

    # --- 0. Evaluate bait (trap check + scoring) ---
    bait_score = None
    path_to_bait = None
    future_pos = None
    if bait and not cat_ignored_bait:
        # Step 1: Check if bait is a definite trap
        if bait_is_a_trap(cat_pos, bait, blocked):
            cat_ignored_bait = True
        else:
            # Step 2: Score the bait opportunity
            bait_score = score_bait_path(cat_pos, bait, blocked)
            if bait_score > -1000:
                path_to_bait = a_star_search(cat_pos, blocked, goal_pos=bait)
                if path_to_bait and len(path_to_bait) > 1:
                    future_pos = path_to_bait[1]

    # --- 1. Find best regular move using Minimax ---
    best_regular_move, best_move_score = find_best_move()

    # --- 2. Check attack option ---
    best_attack_score = -math.inf
    block_to_attack = None
    if not cat_has_attacked_in_game:
        attackable = [n for n in get_neighbors(cat_pos) if n in blocked]
        for block in attackable:
            temp_blocked = blocked.copy()
            temp_blocked.remove(block)
            score = evaluate_board(cat_pos, temp_blocked)
            if score > best_attack_score:
                best_attack_score = score
                block_to_attack = block

    # --- 3. Choose the best option ---
    chosen_move = best_regular_move
    move_reason = "regular"

    if bait_score is not None and bait_score > best_move_score and future_pos:
        chosen_move = future_pos
        move_reason = "bait"

    if block_to_attack and best_attack_score > max(best_move_score, bait_score or -math.inf):
        # Perform attack first
        if cat_attack_sound:
            cat_attack_sound.play()
        if attack_images:
            animate_attack_with_tile_flash(attack_images, cat_pos, block_to_attack)
        blocked.remove(block_to_attack)
        cat_attacked_this_turn = True
        cat_has_attacked_in_game = True

        # Recalculate best move after attack
        best_regular_move, best_move_score = find_best_move()
        chosen_move = best_regular_move
        move_reason = "attack_then_move"

    # --- 4. Move to selected tile ---
    if chosen_move:
        if jump_sound:
            jump_sound.play()
        animate_cat_move(cat_pos, chosen_move)
        cat_pos = chosen_move
    else:
        game_over = True
        winner = 'player'
        handle_game_over_sounds()
        return

    # --- 5. Handle bait if reached ---
    if bait and cat_pos == bait:
        if mouse_dead_sound:
            mouse_dead_sound.play()
        bait = None

    # --- 6. Final win condition check ---
    if is_at_edge(cat_pos):
        game_over = True
        winner = 'cat'
        handle_game_over_sounds()



# --- Reset Game Function ---
# Resets the game state to start a new game
def reset_game():
    global blocked, cat_ignored_bait, bait, cat_pos, winner, game_over, bait_used, cat_has_attacked_in_game
    global cat_idle_index, last_idle_update, cat_facing_left, cat_attacked_this_turn
    global cat_dead_animation_done, dead_final_sprite
    
    blocked = set()
    bait = None
    cat_pos = (GRID_SIZE // 2, GRID_SIZE // 2)
    winner = None
    game_over = False
    cat_ignored_bait = False
    bait_used = False
    cat_has_attacked_in_game = False # Reset the per-game attack flag
    
    cat_idle_index = 0
    last_idle_update = 0
    cat_facing_left = False
    cat_attacked_this_turn = False
    cat_dead_animation_done = False
    dead_final_sprite = None
    
    # Randomly place 8 blocked tiles, ensuring they are not on the cat's position
    while len(blocked) < 8:
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