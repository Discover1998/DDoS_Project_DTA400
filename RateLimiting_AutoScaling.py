import simpy, random, pygame, matplotlib.pyplot as plt

# --- Simulation Parameters ---
REQUEST_PROCESSING_TIME = 1  # Request handling duration in seconds
NORMAL_REQUEST_RATE = 2      # Interval between normal requests
DDOS_REQUEST_RATE = 0.03     # Interval between DDoS requests
INITIAL_SERVER_CAPACITY = 10 # Server's initial processing capacity
SCALING_THRESHOLD = 80       # CPU load percentage threshold to trigger scaling
SCALING_CAPACITY_INCREMENT = 5  # Capacity increment during scaling
SCALING_DELAY = 10           # Delay before scaling occurs
SIMULATION_TIME = 300        # Total duration for the simulation in seconds
DDOS_ATTACK_START = 150      # Time in seconds when the DDoS attack initiates

# --- Metrics Collection ---
cpu_load_over_time = []
dropped_packets_over_time = []
scaled_instances = 0  # Counter for instances when server scales

# --- Visualization Parameters ---
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 800
FPS = 60  # Frames per second for smooth rendering

# --- Color Definitions ---
WHITE = (255, 255, 255)
GREEN = (0, 255, 0)  # Server under light load
RED = (255, 0, 0)    # Server overload status
BLUE = (0, 0, 255)   # Normal client representation
YELLOW = (255, 255, 0)  # DDoS attacker representation
BLACK = (0, 0, 0)    # Background or general-purpose color
GRAY = (128, 128, 128)  # Moderate load server status

# --- Rate Limiter for Requests ---
class RateLimiter:
    def __init__(self, limit, window):
        self.limit = limit
        self.window = window
        self.client_requests = {}

    def allow_request(self, client_id, current_time):
        if client_id not in self.client_requests:
            self.client_requests[client_id] = []
        self.client_requests[client_id] = [
            timestamp for timestamp in self.client_requests[client_id]
            if timestamp > current_time - self.window
        ]
        if len(self.client_requests[client_id]) < self.limit:
            self.client_requests[client_id].append(current_time)
            return True
        else:
            return False

# --- Server Class to Handle Requests ---
class Server:
    def __init__(self, env, capacity):
        self.env = env
        self.capacity = capacity
        self.queue = simpy.Resource(env, capacity=capacity)
        self.cpu_load = 0
        self.dropped_packets = 0
        self.rate_limiter_normal = RateLimiter(limit=5, window=10)
        self.rate_limiter_attacker = RateLimiter(limit=2, window=10)

    def scale_server(self):
        global scaled_instances
        scaled_instances += 1
        self.capacity += SCALING_CAPACITY_INCREMENT
        print(f"Server scaled: New capacity = {self.capacity}")

    def handle_request(self, request_type, sprite, current_time):
        client_id = sprite.rect.x + sprite.rect.y
        if request_type == 'normal':
            allowed = self.rate_limiter_normal.allow_request(client_id, current_time)
        elif request_type == 'attack':
            allowed = self.rate_limiter_attacker.allow_request(client_id, current_time)
        if not allowed:
            self.dropped_packets += 1
            sprite.icon_type = 'dropped'
            return
        with self.queue.request() as req:
            if len(self.queue.users) >= self.capacity:
                self.dropped_packets += 1
                sprite.icon_type = 'dropped'
                return
            yield req
            yield self.env.timeout(REQUEST_PROCESSING_TIME)
            self.cpu_load = min(100, (len(self.queue.users) / self.capacity) * 100)
        if self.cpu_load >= SCALING_THRESHOLD and scaled_instances == 0:
            yield self.env.timeout(SCALING_DELAY)
            self.scale_server()

    def get_stats(self):
        return self.cpu_load, self.dropped_packets

# --- Client Representation for Simulation Visualization ---
class ClientSprite(pygame.sprite.Sprite):
    def __init__(self, x, y, icon_type, server):
        super().__init__()
        self.icon_type = icon_type
        self.server = server
        self.rect = pygame.Rect(x, y, 40, 40)

    def update(self):
        target_x, target_y = SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2
        self.rect.x += (target_x - self.rect.x) * 0.02
        self.rect.y += (target_y - self.rect.y) * 0.02

    def draw(self, screen):
        if self.icon_type == 'user':
            pygame.draw.circle(screen, BLUE, self.rect.center, 12)  

        elif self.icon_type == 'zombie':
            pygame.draw.rect(screen, YELLOW, self.rect)
            pygame.draw.circle(screen, BLACK, (self.rect.centerx - 10, self.rect.centery - 10), 5)
            pygame.draw.circle(screen, BLACK, (self.rect.centerx + 10, self.rect.centery - 10), 5)
        elif self.icon_type == 'dropped':
            pygame.draw.line(screen, RED, self.rect.topleft, self.rect.bottomright, 5)
            pygame.draw.line(screen, RED, self.rect.topright, self.rect.bottomleft, 5)

# --- Representation of DDoS Threat Actor ---
class ThreatActor(pygame.sprite.Sprite):
    def __init__(self):
        super().__init__()
        self.rect = pygame.Rect(SCREEN_WIDTH // 2 - 50, 30, 100, 100)

    def draw(self, screen, font):
        pygame.draw.polygon(screen, BLACK, [
            (self.rect.centerx - 30, self.rect.y + 22), 
            (self.rect.centerx + 30, self.rect.y + 22),
            (self.rect.centerx, self.rect.y - 8)        
        ])
        pygame.draw.circle(screen, BLACK, (self.rect.centerx, self.rect.centery - 10), 20)
        pygame.draw.polygon(screen, BLACK, [
            (self.rect.centerx - 35, self.rect.centery + 10),
            (self.rect.centerx + 35, self.rect.centery + 10),
            (self.rect.centerx + 20, self.rect.centery + 50),
            (self.rect.centerx - 20, self.rect.centery + 50)
        ], 3)
        pygame.draw.rect(screen, BLACK, (self.rect.centerx - 5, self.rect.centery + 5, 10, 25))
        pygame.draw.polygon(screen, BLACK, [
            (self.rect.centerx - 10, self.rect.centery + 30),
            (self.rect.centerx + 10, self.rect.centery + 30),
            (self.rect.centerx, self.rect.centery + 50)
        ])
        hacker_label = font.render('Hacker', True, BLACK)
        screen.blit(hacker_label, (self.rect.centerx - 40, self.rect.centery + 55))

# --- Normal Client Request Generation Process ---
def normal_client(env, server, all_sprites):
    while True:
        yield env.timeout(random.expovariate(1.0 / NORMAL_REQUEST_RATE))
        client = ClientSprite(random.randint(0, SCREEN_WIDTH), random.randint(0, SCREEN_HEIGHT), 'user', server)
        all_sprites.add(client)
        env.process(server.handle_request('normal', client, env.now))

# --- DDoS Attacker Request Generation Process ---
def ddos_attacker(env, server, all_sprites):
    while True:
        yield env.timeout(random.expovariate(1.0 / DDOS_REQUEST_RATE))
        attacker = ClientSprite(random.randint(0, SCREEN_WIDTH), random.randint(0, SCREEN_HEIGHT), 'zombie', server)
        all_sprites.add(attacker)
        env.process(server.handle_request('attack', attacker, env.now))

# --- Server Monitoring Process for Stats Collection ---
def monitor_server(env, server):
    while True:
        cpu_load, dropped_packets = server.get_stats()
        cpu_load_over_time.append((env.now, cpu_load))
        dropped_packets_over_time.append((env.now, dropped_packets))
        yield env.timeout(1)

# --- Draws Database Icon for Server Representation ---
def draw_database_icon(screen, rect, color):
    top_ellipse_rect = pygame.Rect(rect.x, rect.y, rect.width, rect.height // 4)
    bottom_ellipse_rect = pygame.Rect(rect.x, rect.y + (rect.height * 3 // 4), rect.width, rect.height // 4)
    pygame.draw.ellipse(screen, color, top_ellipse_rect)
    pygame.draw.ellipse(screen, color, bottom_ellipse_rect)
    pygame.draw.rect(screen, color, pygame.Rect(rect.x, rect.y + rect.height // 8, rect.width, rect.height * 3 // 4))
    pygame.draw.ellipse(screen, BLACK, top_ellipse_rect, 2)
    pygame.draw.ellipse(screen, BLACK, bottom_ellipse_rect, 2)
    pygame.draw.line(screen, BLACK, (rect.x, rect.y + rect.height // 8), (rect.x, rect.y + rect.height * 7 // 8), 2)
    pygame.draw.line(screen, BLACK, (rect.right, rect.y + rect.height // 8), (rect.right, rect.y + rect.height * 7 // 8), 2)

# --- Main Visualization Loop Using Pygame ---
def pygame_visualization(server, env):
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = pygame.time.Clock()
    font = pygame.font.SysFont('Arial', 28)
    server_sprite = pygame.Rect(SCREEN_WIDTH // 2 - 50, SCREEN_HEIGHT // 2 - 50, 100, 150)
    all_sprites = pygame.sprite.Group()
    threat_actor = ThreatActor()
    for i in range(3):
        env.process(normal_client(env, server, all_sprites))
    running = True
    attack_started = False
    while running and env.now < SIMULATION_TIME:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        all_sprites.update()
        screen.fill(WHITE)
        for sprite in all_sprites:
            sprite.draw(screen)
        threat_actor.draw(screen, font)
        cpu_load = server.cpu_load
        server_color = GRAY if cpu_load >= 80 else GREEN
        draw_database_icon(screen, server_sprite, server_color)
        server_status = "Under Attack" if attack_started else "Normal Status"
        server_status_text = font.render(server_status, True, BLACK)
        screen.blit(server_status_text, (SCREEN_WIDTH // 2 - 75, SCREEN_HEIGHT // 2 + 100))
        pygame.display.flip()
        clock.tick(FPS)
        env.run(until=env.now + 1)
        if env.now == DDOS_ATTACK_START:
            attack_started = True
            for _ in range(10):
                env.process(ddos_attacker(env, server, all_sprites))
    pygame.quit()

# --- Simulation Initialization and Execution ---
env = simpy.Environment()
server = Server(env, INITIAL_SERVER_CAPACITY)
env.process(monitor_server(env, server))
pygame_visualization(server, env)

# --- CPU Load Plot ---
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

# --- Dropped Packets Plot ---
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
