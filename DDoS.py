import simpy, random, pygame, matplotlib.pyplot as plt

# Simulation Parameters
REQUEST_PROCESSING_TIME = 1  # Time to process one request (in seconds)
NORMAL_REQUEST_RATE = 2      # Time between normal client requests
DDOS_REQUEST_RATE = 0.03     # Time between attacker requests
SERVER_CAPACITY = 10         # Maximum number of requests the server can process at once
SIMULATION_TIME = 300        # Total simulation time (seconds)
DDOS_ATTACK_START = 150      # Start the DDoS attack

# Tracking CPU load and dropped packets
cpu_load_over_time = []
dropped_packets_over_time = []

# Pygame visualization setup
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
FPS = 60  # Frame rate for smoothness

# Pygame Colors
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)  # Server under light load
RED = (255, 0, 0)    # Server under heavy attack (overload)
BLUE = (0, 0, 255)   # Normal clients
YELLOW = (255, 255, 0)  # Attackers (zombies)
BLACK = (0, 0, 0)    # Background
GRAY = (128, 128, 128)  # Server under moderate attack

class Server:
    def __init__(self, env, capacity):
        self.env = env
        self.capacity = capacity
        self.queue = simpy.Resource(env, capacity=capacity)
        self.cpu_load = 0
        self.dropped_packets = 0

    def handle_request(self, request_type, sprite):
        with self.queue.request() as req:
            if len(self.queue.users) >= self.capacity:  # Check if server is overloaded
                self.dropped_packets += 1
                sprite.icon_type = 'dropped'  # Change sprite to dropped state (error for normal clients)
                return
            yield req
            yield self.env.timeout(REQUEST_PROCESSING_TIME)
            self.cpu_load = min(100, (len(self.queue.users) / self.capacity) * 100)

    def get_stats(self):
        return self.cpu_load, self.dropped_packets

class ClientSprite(pygame.sprite.Sprite):
    """Represents a client, attacker, or dropped request in the 2D visualization."""
    def __init__(self, x, y, icon_type, server):
        super().__init__()
        self.icon_type = icon_type  # 'user', 'zombie', or 'dropped'
        self.server = server
        self.rect = pygame.Rect(x, y, 40, 40)

    def update(self):
        """Move towards the server to send a request."""
        target_x, target_y = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
        self.rect.x += (target_x - self.rect.x) * 0.02
        self.rect.y += (target_y - self.rect.y) * 0.02

    def draw(self, screen):
        """Draw the sprite."""
        if self.icon_type == 'user':  # Normal client
            pygame.draw.circle(screen, BLUE, self.rect.center, 12)  
            pygame.draw.circle(screen, BLUE, (self.rect.centerx, self.rect.centery + 15), 8)
        elif self.icon_type == 'zombie':  # Attacker (Zombie device)
            pygame.draw.rect(screen, YELLOW, self.rect)  
            pygame.draw.circle(screen, BLACK, (self.rect.centerx - 10, self.rect.centery - 10), 5)  # Eyes
            pygame.draw.circle(screen, BLACK, (self.rect.centerx + 10, self.rect.centery - 10), 5)
        elif self.icon_type == 'dropped':  # Dropped client (error)
            pygame.draw.line(screen, RED, self.rect.topleft, self.rect.bottomright, 5)
            pygame.draw.line(screen, RED, self.rect.topright, self.rect.bottomleft, 5)

class ThreatActor(pygame.sprite.Sprite):
    """Represents the threat actor (hacker) drawn with shapes."""
    def __init__(self):
        super().__init__()
        # Position the hacker at the middle top of the screen
        self.rect = pygame.Rect(SCREEN_WIDTH // 2 - 50, 30, 100, 100)

    def draw(self, screen, font):
        """Draw the hacker using basic shapes to replicate the image you provided."""
        # Lower the hat slightly by 2 pixels
        pygame.draw.polygon(screen, BLACK, [
            (self.rect.centerx - 30, self.rect.y + 22),  # Left corner of the hat, lowered by 2 pixels
            (self.rect.centerx + 30, self.rect.y + 22),  # Right corner of the hat, lowered by 2 pixels
            (self.rect.centerx, self.rect.y - 8)         # Top point of the hat, lowered by 2 pixels
        ])
        
        # Draw the head (circle for face)
        pygame.draw.circle(screen, BLACK, (self.rect.centerx, self.rect.centery - 10), 20)

        # Draw the suit (jacket)
        pygame.draw.polygon(screen, BLACK, [
            (self.rect.centerx - 35, self.rect.centery + 10),   # Left side of the jacket
            (self.rect.centerx + 35, self.rect.centery + 10),   # Right side of the jacket
            (self.rect.centerx + 20, self.rect.centery + 50),   # Right bottom
            (self.rect.centerx - 20, self.rect.centery + 50)    # Left bottom
        ], 3)

        # Draw the tie (simple rectangle and triangle for tie)
        pygame.draw.rect(screen, BLACK, (self.rect.centerx - 5, self.rect.centery + 5, 10, 25))  # Tie base
        pygame.draw.polygon(screen, BLACK, [
            (self.rect.centerx - 10, self.rect.centery + 30),   # Left part of the triangle tie
            (self.rect.centerx + 10, self.rect.centery + 30),   # Right part
            (self.rect.centerx, self.rect.centery + 50)         # Bottom point
        ])

        # Draw "Hacker" label directly underneath the threat actor
        hacker_label = font.render('Hacker', True, BLACK)
        screen.blit(hacker_label, (self.rect.centerx - 40, self.rect.centery + 55))

def normal_client(env, server, all_sprites):
    """Simulate normal clients sending requests."""
    while True:
        yield env.timeout(random.expovariate(1.0 / NORMAL_REQUEST_RATE))
        client = ClientSprite(random.randint(0, SCREEN_WIDTH), random.randint(0, SCREEN_HEIGHT), 'user', server)
        all_sprites.add(client)
        env.process(server.handle_request('normal', client))

def ddos_attacker(env, server, all_sprites):
    """Simulate DDoS attackers originating from random positions on the screen."""
    while True:
        yield env.timeout(random.expovariate(1.0 / DDOS_REQUEST_RATE))
        attacker = ClientSprite(random.randint(0, SCREEN_WIDTH), random.randint(0, SCREEN_HEIGHT), 'zombie', server)
        all_sprites.add(attacker)
        env.process(server.handle_request('attack', attacker))

def monitor_server(env, server):
    """Monitor server CPU load and dropped packets."""
    while True:
        cpu_load, dropped_packets = server.get_stats()
        cpu_load_over_time.append((env.now, cpu_load))
        dropped_packets_over_time.append((env.now, dropped_packets))
        yield env.timeout(1)

def draw_database_icon(screen, rect, color):
    """Draw a database icon to represent the server."""
    top_ellipse_rect = pygame.Rect(rect.x, rect.y, rect.width, rect.height // 4)
    bottom_ellipse_rect = pygame.Rect(rect.x, rect.y + (rect.height * 3 // 4), rect.width, rect.height // 4)
    pygame.draw.ellipse(screen, color, top_ellipse_rect)
    pygame.draw.ellipse(screen, color, bottom_ellipse_rect)
    pygame.draw.rect(screen, color, pygame.Rect(rect.x, rect.y + rect.height // 8, rect.width, rect.height * 3 // 4))
    pygame.draw.ellipse(screen, BLACK, top_ellipse_rect, 2)
    pygame.draw.ellipse(screen, BLACK, bottom_ellipse_rect, 2)
    pygame.draw.line(screen, BLACK, (rect.x, rect.y + rect.height // 8), (rect.x, rect.y + rect.height * 7 // 8), 2)
    pygame.draw.line(screen, BLACK, (rect.right, rect.y + rect.height // 8), (rect.right, rect.y + rect.height * 7 // 8), 2)

def pygame_visualization(server, env):
    """Pygame visualization of DDoS simulation."""
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = pygame.time.Clock()
    font = pygame.font.SysFont('Arial', 28)
    server_sprite = pygame.Rect(SCREEN_WIDTH // 2 - 50, SCREEN_HEIGHT // 2 - 50, 100, 150)
    all_sprites = pygame.sprite.Group()

    # Instantiate the threat actor (hacker) drawing at the top center
    threat_actor = ThreatActor()

    # Start normal clients
    for i in range(3):
        env.process(normal_client(env, server, all_sprites))

    running = True
    attack_started = False
    while running and env.now < SIMULATION_TIME:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        all_sprites.update()
        screen.fill(WHITE)  # Change background to white
        for sprite in all_sprites:
            sprite.draw(screen)

        # Draw the threat actor who commands the zombies
        threat_actor.draw(screen, font)

        # Draw the server database icon
        cpu_load = server.cpu_load
        server_color = GRAY if cpu_load >= 80 else GREEN
        draw_database_icon(screen, server_sprite, server_color)

        # Show server status
        server_status = "Under Attack" if attack_started else "Normal Status"
        server_status_text = font.render(server_status, True, BLACK)
        screen.blit(server_status_text, (SCREEN_WIDTH // 2 - 75, SCREEN_HEIGHT // 2 + 100))

        pygame.display.flip()
        clock.tick(FPS)
        env.run(until=env.now + 1)

        # At attack start, zombies attack from random positions
        if env.now == DDOS_ATTACK_START:
            attack_started = True
            for _ in range(10):
                env.process(ddos_attacker(env, server, all_sprites))

    pygame.quit()

# Set up the simulation environment
env = simpy.Environment()
server = Server(env, SERVER_CAPACITY)
env.process(monitor_server(env, server))
pygame_visualization(server, env)

# Plot CPU Load Figure
times, cpu_loads = zip(*cpu_load_over_time)
plt.figure(figsize=(10, 5))
plt.plot(times, cpu_loads, label='CPU Load (%)', color='blue')
plt.axvline(x=DDOS_ATTACK_START, color='red', linestyle='--', label='DDoS Attack Start')
plt.xlabel('Time (s)')
plt.ylabel('CPU Load (%)')
plt.title('Server CPU Load Over Time')
plt.legend()
plt.grid(True)
plt.show()

# Plot Dropped Packets Figure
_, dropped_packets = zip(*dropped_packets_over_time)
plt.figure(figsize=(10, 5))
plt.plot(times, dropped_packets, label='Dropped Packets', color='orange')
plt.axvline(x=DDOS_ATTACK_START, color='red', linestyle='--', label='DDoS Attack Start')
plt.xlabel('Time (s)')
plt.ylabel('Dropped Packets')
plt.title('Dropped Packets Over Time')
plt.legend()
plt.grid(True)
plt.show()
