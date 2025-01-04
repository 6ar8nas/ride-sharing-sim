from typing import Optional

import pygame

from constants import Colors, Events
from entity import Driver, Rider
from entity_gen import EntityGenerator
from state import SimulationState

pygame.init()
screen_size = (1280, 720)
screen = pygame.display.set_mode(screen_size)
background: Optional[pygame.Surface] = None
clock = pygame.time.Clock()
running = True

state = SimulationState("Kaunas, Lithuania", screen_size)
eg = EntityGenerator(state)
drivers: set[Driver] = set()
idle_riders: set[Rider] = set()

while running:
    current_time = pygame.time.get_ticks()

    # Event processing
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            eg.stop()
        elif event.type == pygame.USEREVENT:
            event_type = event.dict['event_type']
            driver: Optional[Driver] = event.dict.get('driver')
            rider: Optional[Rider] = event.dict.get('rider')
            print(f"[LOG] {current_time}: {event_type:15}" + (f" D{driver.id}" if driver is not None else "") + (f" R{rider.id}" if rider is not None else ""))
            if event_type == Events.NewDriver:
                drivers.add(driver)
            elif event_type == Events.NewRider:
                idle_riders.add(rider)
            elif event_type == Events.DriverComplete:
                drivers.remove(driver)

    # Simulation logic
    for driver in drivers:
        driver.move(current_time)

    # Drawing
    if background is None:
        background = pygame.Surface(screen_size)
        background.fill(Colors.Background.value)
        for u, v in state.edges.keys():
            pygame.draw.line(background, Colors.Edge.value, state.nodes[u], state.nodes[v], 1)
        for coord in state.nodes.values():
            pygame.draw.circle(background, Colors.Building.value, coord, 2)
    screen.blit(background, (0, 0))
    for driver in drivers:
        pygame.draw.circle(screen, Colors.Driver.value, driver.position, 3)
    for rider in idle_riders:
        pygame.draw.circle(screen, Colors.IdleRider.value, rider.position, 3)

    pygame.display.update()
    clock.tick(30)

pygame.quit()