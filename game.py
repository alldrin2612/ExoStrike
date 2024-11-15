import pygame
import random
import math
import os
import sqlite3  # Import SQLite library
import cv2  # Import OpenCV for video playback

class Exostrike:
    def __init__(self, selected_ship, is_fullscreen=False, screen_width=800, screen_height=600):
        pygame.init()
        pygame.mixer.init()

        self.selected_ship = selected_ship
        
        # Display settings
        self.screen_width = screen_width
        self.screen_height = screen_height
        
        # Set initial display mode based on fullscreen state
        if is_fullscreen:
            self.screen = pygame.display.set_mode((self.screen_width, self.screen_height), pygame.FULLSCREEN)
        else:
            self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
            
        pygame.display.set_caption("Exostrike")
        
        # Colors
        self.BLACK = (0, 0, 0)
        self.WHITE = (255, 255, 255)
        self.RED = (255, 0, 0)
        self.GREEN = (0, 255, 0)
        self.YELLOW = (255, 255, 0)  # Added for enemy bullets
        
        # Game states
        self.running = True
        self.game_over = False
        self.score = 0
        self.lives = 3
        self.wave = 1
        
        # Enemy scaling
        self.MIN_ENEMIES = 5
        self.MAX_ENEMIES = 15
        self.ENEMY_INCREASE_RATE = 2  # How many enemies to add per wave
        
        # New attribute for shooters per wave
        self.shooters_per_wave = {1: 2, 2: 3, 3: 4, 4: 5}  # Example configuration
        
        # Clock and timing
        self.clock = pygame.time.Clock()
        self.FPS = 60
        
        # Wave patterns
        self.wave_patterns = [
            self.create_grid_formation,
            self.create_v_formation,
            self.create_circle_formation,
            self.create_diamond_formation,
            self.create_zigzag_formation
        ]
        
        # Load assets
        self.load_assets(selected_ship)
        
        # Initialize game objects
        self.init_game_objects()

        # Initialize database
        self.init_database()

        self.player_damage_particles = []  # List to hold player damage particles
        self.enemy_damage_particles = []  # List to hold enemy damage particles
        self.shake_intensity = 0  # Intensity of the shake effect

        # Initialize video
        self.video_capture = cv2.VideoCapture("BG/Background.mp4")
        self.frame = None

        # Adjust player attributes for new resolution
        self.player_pos = [self.screen_width // 2, self.screen_height - 60]  # Center player in new resolution
        self.player_speed = 12  # Adjust speed for new resolution
        self.player_friction = 0.92  # Keep friction the same

        # Adjust bullet attributes for new resolution
        self.bullet_speed = 20  # Adjust bullet speed for new resolution

        # Adjust enemy attributes for new resolution
        self.enemy_bullet_speed = 10  # Adjust enemy bullet speed for new resolution

        # Adjust HUD positions
        self.hud_offset_x = 10  # Keep HUD offset for new resolution
        self.hud_offset_y = 10  # Keep HUD offset for new resolution

        # Adjust shake effect
        self.shake_intensity = 10  # Increase shake intensity for new resolution

        # Add new attribute for player rotation
        self.player_rotation = 0
        self.max_tilt = 20  # Maximum rotation angle in degrees
        self.tilt_speed = 2  # How quickly the ship tilts

        # Power-up attributes
        self.powerups = []  # List to store active powerups
        self.POWERUP_SIZE = 20  # Size of the powerup circle
        self.POWERUP_SPEED = 2  # Slower fall speed for better visibility
        self.POWERUP_SPAWN_CHANCE = 10  # Changed from 6 to 10 (now 1 in 10 chance, or 10%)
        self.double_shot_active = False
        self.rapid_fire_active = False
        self.powerup_end_time = 0
        
        # Colors for powerups with higher visibility
        self.POWERUP_COLORS = {
            'double_shot': (0, 255, 255),  # Bright cyan
            'rapid_fire': (255, 165, 0)    # Bright orange
        }

    def init_database(self):
        # Create a new SQLite database or connect to an existing one
        self.conn = sqlite3.connect('highscores.db')
        self.cursor = self.conn.cursor()
        
        # Create a table for high scores if it doesn't exist
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS highscores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                score INTEGER NOT NULL
            )
        ''')
        self.conn.commit()

    def save_high_score(self, score):
        # Save a new high score to the database
        self.cursor.execute('INSERT INTO highscores (score) VALUES (?)', (score,))
        self.conn.commit()

    def get_high_scores(self):
        # Retrieve the top 5 high scores from the database
        self.cursor.execute('SELECT score FROM highscores ORDER BY score DESC LIMIT 5')
        return self.cursor.fetchall()

    def load_assets(self,selected_ship):
        # Load spaceship images
        ship_files = ["ship 1.png", "ship 2.png", "spaceship 1.png", "spaceship 2.png"]
        ship_path = os.path.join("BG", ship_files[selected_ship])
        self.player_ship = pygame.image.load(ship_path)
        self.enemy_ship_image = pygame.image.load("BG/enemyship.png").convert_alpha()  # Load enemy ship image
        
        # Resize images to fit the screen
        self.player_ship = pygame.transform.scale(self.player_ship, (50, 50))  # Resize player ship
        self.enemy_ship = pygame.transform.scale(self.enemy_ship_image, (40, 40))  # Resize enemy ship
        
        # Rotate the enemy ship 180 degrees
        self.enemy_ship = pygame.transform.rotate(self.enemy_ship, 180)  # Rotate enemy ship
        
        # Load bullet images
        self.bullet = pygame.Surface((4, 12), pygame.SRCALPHA)
        pygame.draw.rect(self.bullet, self.GREEN, (0, 0, 4, 12))
        
        # New enemy bullet asset
        self.enemy_bullet = pygame.Surface((4, 12), pygame.SRCALPHA)
        pygame.draw.rect(self.enemy_bullet, self.YELLOW, (0, 0, 4, 12))
        
        # Font
        self.font = pygame.font.Font(None, 36)
        
        # Load sound effects
        self.shoot_sound = pygame.mixer.Sound(os.path.join("BG", "gun_1.mp3"))
        self.damage_sound = pygame.mixer.Sound(os.path.join("BG", "damage.wav"))
        self.gameover_sound = pygame.mixer.Sound(os.path.join("BG", "gameover.wav"))  # Add game over sound
        
        # Adjust sound volumes
        self.shoot_sound.set_volume(0.3)
        self.damage_sound.set_volume(0.4)
        self.gameover_sound.set_volume(0.4)  # Set game over sound volume

    def init_game_objects(self):
        # Player attributes
        self.player_pos = [self.screen_width // 2, self.screen_height - 60]
        self.player_speed = 6
        self.player_velocity = [0, 0]
        self.player_acceleration = 0.5
        self.player_friction = 0.92
        
        # Enemy attributes
        self.enemies = []
        self.enemy_bullets = []  # Initialize enemy bullets
        self.enemy_bullet_speed = 5
        self.enemy_shot_delay = 2000  # 2 seconds between shots
        self.spawn_wave()
        
        # Bullet attributes
        self.bullets = []
        self.bullet_speed = 10
        self.last_shot_time = 0
        self.shot_delay = 250  # Milliseconds between shots

    def get_enemy_count_for_wave(self):
        # Calculate number of enemies for current wave
        enemy_count = self.MIN_ENEMIES + (self.wave - 1) * self.ENEMY_INCREASE_RATE
        return min(enemy_count, self.MAX_ENEMIES)

    def create_enemy(self, x, y, pattern_type):
        movement_patterns = {
            'linear': {'velocity': [2, 0], 'pattern_func': self.move_linear},
            'sine': {'velocity': [2, 0], 'pattern_func': self.move_sine},
            'circular': {'velocity': [2, 0], 'pattern_func': self.move_circular},
            'zigzag': {'velocity': [2, 0], 'pattern_func': self.move_zigzag}
        }
        
        pattern = random.choice(list(movement_patterns.keys()))
        
        return {
            'pos': [x, y],
            'velocity': movement_patterns[pattern]['velocity'].copy(),
            'health': 1,
            'pattern': pattern,
            'pattern_func': movement_patterns[pattern]['pattern_func'],
            'initial_pos': [x, y],
            'time': random.random() * math.pi * 2,  # Random start phase
            'can_shoot': False,  # New attribute for shooting ability
            'last_shot_time': 0  # New attribute for tracking shot timing
        }

    def create_grid_formation(self, num_enemies):
        enemies = []
        rows = min(3, (num_enemies + 5) // 6)
        cols = min(6, (num_enemies + rows - 1) // rows)
        spacing_x = 80
        spacing_y = 60
        
        count = 0
        for row in range(rows):
            for col in range(cols):
                if count >= num_enemies:
                    break
                x = col * spacing_x + (self.screen_width - (cols-1) * spacing_x) // 2
                y = row * spacing_y + 50
                enemies.append(self.create_enemy(x, y, 'grid'))
                count += 1
        return enemies

    def create_v_formation(self, num_enemies):
        enemies = []
        spacing = 40
        
        half_enemies = num_enemies // 2
        for i in range(num_enemies):
            if i < half_enemies:
                x = self.screen_width // 2 - (i + 1) * spacing
                y = 50 + i * spacing
            else:
                x = self.screen_width // 2 + (i - half_enemies) * spacing
                y = 50 + (num_enemies - i - 1) * spacing
            enemies.append(self.create_enemy(x, y, 'v'))
        return enemies

    def create_circle_formation(self, num_enemies):
        enemies = []
        radius = min(100, num_enemies * 10)
        center_x = self.screen_width // 2
        center_y = 150
        
        for i in range(num_enemies):
            angle = (2 * math.pi * i) / num_enemies
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
            enemies.append(self.create_enemy(x, y, 'circle'))
        return enemies

    def create_diamond_formation(self, num_enemies):
        enemies = []
        size = min(4, (num_enemies + 3) // 4)
        spacing = 40
        
        count = 0
        for i in range(size * 2 - 1):
            width = size - abs(size - 1 - i)
            for j in range(width):
                if count >= num_enemies:
                    break
                x = self.screen_width // 2 + (j - width // 2) * spacing
                y = 50 + i * spacing // 2
                enemies.append(self.create_enemy(x, y, 'diamond'))
                count += 1
        return enemies

    def create_zigzag_formation(self, num_enemies):
        enemies = []
        num_rows = min(3, (num_enemies + 4) // 5)
        enemies_per_row = (num_enemies + num_rows - 1) // num_rows
        spacing_x = 80
        spacing_y = 60
        
        count = 0
        for row in range(num_rows):
            offset = spacing_x // 2 if row % 2 else 0
            for col in range(enemies_per_row):
                if count >= num_enemies:
                    break
                x = col * spacing_x + offset + (self.screen_width - (enemies_per_row-1) * spacing_x) // 2
                y = row * spacing_y + 50
                enemies.append(self.create_enemy(x, y, 'zigzag'))
                count += 1
        return enemies

    def move_linear(self, enemy):
        enemy['pos'][0] += enemy['velocity'][0]
        if enemy['pos'][0] <= 0 or enemy['pos'][0] >= self.screen_width - 30:
            enemy['velocity'][0] *= -1
            enemy['pos'][1] += 20

    def move_sine(self, enemy):
        enemy['time'] += 0.05
        enemy['pos'][0] += enemy['velocity'][0]
        enemy['pos'][1] = enemy['initial_pos'][1] + math.sin(enemy['time']) * 30
        
        if enemy['pos'][0] <= 0 or enemy['pos'][0] >= self.screen_width - 30:
            enemy['velocity'][0] *= -1
            enemy['pos'][1] += 10

    def move_circular(self, enemy):
        enemy['time'] += 0.03
        radius = 30
        enemy['pos'][0] = enemy['initial_pos'][0] + math.cos(enemy['time']) * radius
        enemy['pos'][1] = enemy['initial_pos'][1] + math.sin(enemy['time']) * radius

    def move_zigzag(self, enemy):
        enemy['time'] += 0.1
        enemy['pos'][0] += enemy['velocity'][0]
        if enemy['pos'][0] <= 0 or enemy['pos'][0] >= self.screen_width - 30:
            enemy['velocity'][0] *= -1
            enemy['pos'][1] += 30

    def spawn_wave(self):
        self.enemies.clear()
        
        # Calculate number of enemies for this wave
        num_enemies = self.get_enemy_count_for_wave()
        
        # Choose formation pattern
        if self.wave <= len(self.wave_patterns):
            # Use sequential patterns for first few waves
            pattern_func = self.wave_patterns[self.wave - 1]
        else:
            # Use random patterns for later waves
            pattern_func = random.choice(self.wave_patterns)
        
        # Create enemies using the selected pattern
        self.enemies = pattern_func(num_enemies)
        
        # Assign shooting ability to random enemies
        num_shooters = min(self.shooters_per_wave.get(self.wave, 6), len(self.enemies))
        shooting_enemies = random.sample(self.enemies, num_shooters)
        for enemy in shooting_enemies:
            enemy['can_shoot'] = True
        
        # Increase difficulty with each wave
        speed_multiplier = 1 + (self.wave - 1) * 0.1
        for enemy in self.enemies:
            enemy['velocity'][0] *= speed_multiplier

        # Increase fire rate every 5 waves
        if self.wave % 5 == 0:
            self.enemy_shot_delay = max(100, self.enemy_shot_delay - 250)  # Decrease delay, ensuring it doesn't go below 100ms

    def handle_input(self):
        keys = pygame.key.get_pressed()
        
        # Update velocity based on input
        if keys[pygame.K_LEFT]:
            self.player_velocity[0] -= self.player_acceleration
            # Smoothly rotate left
            self.player_rotation = min(self.player_rotation + self.tilt_speed, self.max_tilt)
        elif keys[pygame.K_RIGHT]:
            self.player_velocity[0] += self.player_acceleration
            # Smoothly rotate right
            self.player_rotation = max(self.player_rotation - self.tilt_speed, -self.max_tilt)
        else:
            # Return to center when no input
            if self.player_rotation > 0:
                self.player_rotation = max(0, self.player_rotation - self.tilt_speed)
            elif self.player_rotation < 0:
                self.player_rotation = min(0, self.player_rotation + self.tilt_speed)
        
        self.player_velocity[0] *= self.player_friction
        self.player_pos[0] += self.player_velocity[0]
        
        self.player_pos[0] = max(0, min(self.player_pos[0], self.screen_width - 40))
        
        current_time = pygame.time.get_ticks()
        if keys[pygame.K_SPACE] and current_time - self.last_shot_time > self.shot_delay:
            self.shoot()
            self.last_shot_time = current_time

    def shoot(self):
        current_time = pygame.time.get_ticks()
        if current_time - self.last_shot_time > self.shot_delay:
            # Calculate bullet starting position from center of ship's tip
            ship_width = 50
            ship_height = 50
            
            # Center bullet position
            bullet_x = self.player_pos[0] + (ship_width / 2) - 2
            bullet_y = self.player_pos[1] - 10
            
            if self.double_shot_active:
                # Spawn two bullets side by side
                self.bullets.append([bullet_x - 8, bullet_y])
                self.bullets.append([bullet_x + 8, bullet_y])
            else:
                # Normal single bullet
                self.bullets.append([bullet_x, bullet_y])
            
            self.last_shot_time = current_time
            self.shoot_sound.play()

    def enemy_shoot(self, enemy):
        current_time = pygame.time.get_ticks()
        if enemy['can_shoot'] and current_time - enemy['last_shot_time'] > self.enemy_shot_delay:
            bullet_pos = [enemy['pos'][0] + 15, enemy['pos'][1] + 30]  # Shoot from bottom of enemy
            self.enemy_bullets.append(bullet_pos)
            enemy['last_shot_time'] = current_time

    def update_enemies(self):
        for enemy in self.enemies:
            enemy['pattern_func'](enemy)
            self.enemy_shoot(enemy)  # Try to shoot for each enemy (will only work for those that can_shoot)
            
            if enemy['pos'][1] + 30 >= self.player_pos[1]:
                self.game_over = True

    def update_bullets(self):
        for bullet in self.bullets[:]:
            bullet[1] -= self.bullet_speed
            if bullet[1] < -10:
                self.bullets.remove(bullet)
        
        # Update enemy bullets
        for bullet in self.enemy_bullets[:]:
            bullet[1] += self.enemy_bullet_speed
            if bullet[1] > self.screen_height:
                self.enemy_bullets.remove(bullet)

    def check_collisions(self):
        for bullet in self.bullets[:]:
            for enemy in self.enemies[:]:
                if (bullet[0] > enemy['pos'][0] and 
                    bullet[0] < enemy['pos'][0] + 30 and
                    bullet[1] > enemy['pos'][1] and 
                    bullet[1] < enemy['pos'][1] + 30):
                    
                    if bullet in self.bullets:
                        self.bullets.remove(bullet)
                    self.enemies.remove(enemy)
                    self.score += 100
                    self.damage_sound.play()  # Play sound when enemy is destroyed
                    
                    # Spawn powerup at enemy's position
                    self.spawn_powerup(enemy['pos'][0], enemy['pos'][1])
                    
                    # Create enemy damage particles
                    self.create_damage_particles(enemy['pos'][0] + 15, enemy['pos'][1] + 15, self.RED)
                    
                    if not self.enemies:
                        self.wave += 1
                        self.spawn_wave()
                    break

        # Check enemy bullets hitting player
        for bullet in self.enemy_bullets[:]:
            if (bullet[0] > self.player_pos[0] and 
                bullet[0] < self.player_pos[0] + 40 and
                bullet[1] > self.player_pos[1] and 
                bullet[1] < self.player_pos[1] + 40):
                
                self.enemy_bullets.remove(bullet)
                self.lives -= 1
                
                # Play appropriate sound based on remaining lives
                if self.lives <= 0:
                    self.gameover_sound.play()  # Play game over sound for final life lost
                    self.save_high_score(self.score)
                    self.game_over = True
                else:
                    self.damage_sound.play()  # Play damage sound for other hits
                
                self.shake_intensity = 5
                self.create_damage_particles(self.player_pos[0] + 20, self.player_pos[1] + 20, self.WHITE)

    def create_damage_particles(self, x, y, color, count=10):
        for _ in range(count):
            particle_velocity = [random.uniform(-2, 2), random.uniform(-2, 2)]
            self.player_damage_particles.append({'pos': [x, y], 'velocity': particle_velocity, 'lifetime': 30, 'color': color})

    def draw(self):
        # Read a frame from the video
        ret, self.frame = self.video_capture.read()
        if ret:
            # Convert the frame to a format suitable for Pygame
            frame = cv2.cvtColor(self.frame, cv2.COLOR_BGR2RGB)
            frame = pygame.surfarray.make_surface(frame)
            frame = pygame.transform.scale(frame, (self.screen_width, self.screen_height))
            self.screen.blit(frame, (0, 0))  # Draw the video frame as background
        else:
            # If the video ends, restart it
            self.video_capture.set(cv2.CAP_PROP_POS_FRAMES, 0)

        # Apply shake effect to player position
        shake_x = random.uniform(-self.shake_intensity, self.shake_intensity)
        shake_y = random.uniform(-self.shake_intensity, self.shake_intensity)
        self.player_pos[0] += shake_x
        self.player_pos[1] += shake_y

        # Draw player ship with rotation
        rotated_player = pygame.transform.rotate(self.player_ship, self.player_rotation)
        # Get the new rect to maintain center position
        player_rect = rotated_player.get_rect(center=(self.player_pos[0] + 25, self.player_pos[1] + 25))
        self.screen.blit(rotated_player, player_rect)
        
        # Draw enemies
        for enemy in self.enemies:
            self.screen.blit(self.enemy_ship, enemy['pos'])
        
        # Draw bullets
        for bullet in self.bullets:
            self.screen.blit(self.bullet, bullet)
        
        # Draw enemy bullets
        for bullet in self.enemy_bullets:
            self.screen.blit(self.enemy_bullet, bullet)

        # Draw player damage particles
        for particle in self.player_damage_particles[:]:
            particle['pos'][0] += particle['velocity'][0]
            particle['pos'][1] += particle['velocity'][1]
            particle['lifetime'] -= 1
            if particle['lifetime'] <= 0:
                self.player_damage_particles.remove(particle)
            else:
                pygame.draw.circle(self.screen, particle['color'], (int(particle['pos'][0]), int(particle['pos'][1])), 3)

        # Draw enemy damage particles
        for particle in self.enemy_damage_particles[:]:
            particle['pos'][0] += particle['velocity'][0]
            particle['pos'][1] += particle['velocity'][1]
            particle['lifetime'] -= 1
            if particle['lifetime'] <= 0:
                self.enemy_damage_particles.remove(particle)
            else:
                pygame.draw.circle(self.screen, particle['color'], (int(particle['pos'][0]), int(particle['pos'][1])), 3)

        # Draw HUD with adjusted positions
        score_text = self.font.render(f'Score: {self.score}', True, self.WHITE)
        wave_text = self.font.render(f'Wave: {self.wave}', True, self.WHITE)
        lives_text = self.font.render(f'Lives: {self.lives}', True, self.WHITE)
        enemies_text = self.font.render(f'Enemies: {len(self.enemies)}', True, self.WHITE)
        
        self.screen.blit(score_text, (self.hud_offset_x, self.hud_offset_y))
        self.screen.blit(wave_text, (self.hud_offset_x, self.hud_offset_y + 30))
        self.screen.blit(lives_text, (self.hud_offset_x, self.hud_offset_y + 60))
        self.screen.blit(enemies_text, (self.hud_offset_x, self.hud_offset_y + 90))
        
        if self.game_over:
            game_over_text = self.font.render('GAME OVER', True, self.RED)
            text_rect = game_over_text.get_rect(center=(self.screen_width/2, self.screen_height/2 - 30))
            self.screen.blit(game_over_text, text_rect)

            restart_text = self.font.render('Press R to Restart', True, self.WHITE)
            restart_rect = restart_text.get_rect(center=(self.screen_width/2, self.screen_height/2 + 10))
            self.screen.blit(restart_text, restart_rect)

            highscore_text = self.font.render('Press H to Check High Scores', True, self.WHITE)
            highscore_rect = highscore_text.get_rect(center=(self.screen_width/2, self.screen_height/2 + 40))
            self.screen.blit(highscore_text, highscore_rect)

            exit_text = self.font.render('Press Q to Quit', True, self.WHITE)
            exit_rect = exit_text.get_rect(center=(self.screen_width/2, self.screen_height/2 + 70))
            self.screen.blit(exit_text, exit_rect)

            # Display high scores
            high_scores = self.get_high_scores()
            high_score_text = self.font.render('High Scores:', True, self.WHITE)
            self.screen.blit(high_score_text, (self.screen_width / 2 - 50, self.screen_height / 2 + 100))
            for i, (score,) in enumerate(high_scores):
                score_text = self.font.render(f'{i + 1}. {score}', True, self.WHITE)
                self.screen.blit(score_text, (self.screen_width / 2 - 50, self.screen_height / 2 + 130 + i * 30))
        
        # Draw powerups as circles with icons
        for powerup in self.powerups:
            # Draw the outer circle
            pygame.draw.circle(self.screen, powerup['color'], 
                             (int(powerup['pos'][0]), int(powerup['pos'][1])), 
                             self.POWERUP_SIZE)
            
            # Draw inner circle for better visibility
            pygame.draw.circle(self.screen, self.WHITE,
                             (int(powerup['pos'][0]), int(powerup['pos'][1])), 
                             self.POWERUP_SIZE - 4)
            
            # Draw icon or text based on powerup type
            font = pygame.font.Font(None, 20)
            icon = "2X" if powerup['type'] == 'double_shot' else "RF"
            text = font.render(icon, True, powerup['color'])
            text_rect = text.get_rect(center=(powerup['pos'][0], powerup['pos'][1]))
            self.screen.blit(text, text_rect)
        
        pygame.display.flip()

    def run(self):
        while self.running:
            self.clock.tick(self.FPS)
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r and self.game_over:
                        self.game_over = False
                        self.score = 0
                        self.wave = 1
                        self.lives = 3
                        self.powerups.clear()  # Clear all powerups when restarting
                        self.init_game_objects()
                    if event.key == pygame.K_h and self.game_over:
                        self.show_high_scores()
                    if event.key == pygame.K_q and self.game_over:
                        self.running = False
                    if event.key == pygame.K_f:  # Toggle fullscreen
                        if self.screen.get_flags() & pygame.FULLSCREEN:
                            self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))  # Windowed mode
                        else:
                            # Get the maximum resolution of the user's device
                            info = pygame.display.Info()
                            max_width = info.current_w
                            max_height = info.current_h
                            self.screen = pygame.display.set_mode((max_width, max_height), pygame.FULLSCREEN)  # Fullscreen mode
                            # Adjust player attributes for new resolution
                            self.player_pos = [max_width // 2, max_height - 60]  # Center player in new resolution
                            self.player_speed = 12  # Adjust speed for new resolution
                            self.bullet_speed = 20  # Adjust bullet speed for new resolution
                            self.enemy_bullet_speed = 10  # Adjust enemy bullet speed for new resolution
                            self.hud_offset_x = 10  # Keep HUD offset for new resolution
                            self.hud_offset_y = 10  # Keep HUD offset for new resolution

            if not self.game_over:
                self.handle_input()
                self.update_enemies()
                self.update_bullets()
                self.update_powerups()
                self.check_collisions()
            
            # Reset shake intensity after applying it
            if self.shake_intensity > 0:
                self.shake_intensity -= 0.5  # Gradually reduce shake intensity

            self.draw()
        
        self.conn.close()  # Close the database connection
        pygame.quit()
        self.video_capture.release()  # Release the video capture object

    def show_high_scores(self):
        # Display high scores in a separate screen
        high_scores = self.get_high_scores()
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:  # Press ESC to return to the game
                        return
            
            self.screen.fill(self.BLACK)
            
            # Center the "High Scores:" title
            high_score_text = self.font.render('High Scores:', True, self.WHITE)
            title_rect = high_score_text.get_rect(center=(self.screen_width / 2, 50))
            self.screen.blit(high_score_text, title_rect)
            
            # Center each score entry
            for i, (score,) in enumerate(high_scores):
                score_text = self.font.render(f'{i + 1}. {score}', True, self.WHITE)
                score_rect = score_text.get_rect(center=(self.screen_width / 2, 100 + i * 30))
                self.screen.blit(score_text, score_rect)
            
            # Center the "Press ESC" text
            back_text = self.font.render('Press ESC to go back', True, self.WHITE)
            back_rect = back_text.get_rect(center=(self.screen_width / 2, 100 + len(high_scores) * 30 + 20))
            self.screen.blit(back_text, back_rect)
            
            pygame.display.flip()

    def spawn_powerup(self, x, y):
        if random.randint(1, self.POWERUP_SPAWN_CHANCE) == 1:
            powerup_type = random.choice(['double_shot', 'rapid_fire'])
            self.powerups.append({
                'type': powerup_type,
                'pos': [x + 15, y + 15],  # Center on the enemy's position
                'color': self.POWERUP_COLORS[powerup_type]
            })

    def update_powerups(self):
        # Update powerup positions and check collection
        for powerup in self.powerups[:]:
            powerup['pos'][1] += self.POWERUP_SPEED
            
            # Check if player collected the powerup (using circle collision)
            player_center = (self.player_pos[0] + 25, self.player_pos[1] + 25)
            powerup_center = (powerup['pos'][0], powerup['pos'][1])
            distance = math.sqrt((player_center[0] - powerup_center[0])**2 + 
                               (player_center[1] - powerup_center[1])**2)
            
            if distance < self.POWERUP_SIZE + 25:  # 25 is roughly half the player ship size
                self.activate_powerup(powerup['type'])
                self.powerups.remove(powerup)
            
            # Remove if off screen
            elif powerup['pos'][1] > self.screen_height:
                self.powerups.remove(powerup)
        
        # Check if powerups have expired
        current_time = pygame.time.get_ticks()
        if current_time > self.powerup_end_time:
            self.double_shot_active = False
            self.rapid_fire_active = False
            self.shot_delay = 250  # Reset to normal fire rate

    def activate_powerup(self, powerup_type):
        current_time = pygame.time.get_ticks()
        self.powerup_end_time = current_time + 5000  # 5 seconds duration
        
        if powerup_type == 'double_shot':
            self.double_shot_active = True
        elif powerup_type == 'rapid_fire':
            self.rapid_fire_active = True
            self.shot_delay = 125  # Half the normal delay

if __name__ == "__main__":
    game = Exostrike(selected_ship=0)  # Default to first ship when running directly
    game.run()