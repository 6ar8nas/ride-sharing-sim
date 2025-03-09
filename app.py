import os
from pprint import pprint
from typing import Optional

import pygame

from constants import Colors, Events
from entity import Driver, Rider
from entity_gen import EntityGenerator
from matching import rider_matching
from state import SimulationState
from stats import calculate_statistics

os.environ["SDL_VIDEO_CENTERED"] = "1"

pygame.init()
screen_size = (1280, 720)
screen = pygame.display.set_mode(screen_size)
pygame.display.set_caption("Ride Sharing Simulator")
pygame.display.set_icon(pygame.image.load("assets/icon.png"))
pygame.event.set_allowed([pygame.QUIT, pygame.USEREVENT])
font = pygame.font.Font(None, 24)
background: Optional[pygame.Surface] = None
clock = pygame.time.Clock()
running = True

state = SimulationState("Vilnius, Lithuania", screen_size, 30)
eg = EntityGenerator(state)
drivers: set[Driver] = set()
idle_riders: set[Rider] = set()
waiting_riders: set[Rider] = set()
driver_archive: set[Driver] = set()
rider_archive: set[Rider] = set()
eg.start()  # starts recurring new driver and new rider events generation

while running:
    current_time = state.get_time()

    # Event processing
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            eg.stop()
        elif event.type == pygame.USEREVENT:
            event_type = event.dict["event_type"]
            driver: Optional[Driver] = event.dict.get("driver")
            rider: Optional[Rider] = event.dict.get("rider")
            pprint(
                f"[LOG] {current_time}: {event_type:15}"
                + (f" D{driver.id}" if driver is not None else "")
                + (f" R{rider.id}" if rider is not None else "")
            )
            if event_type == Events.NewDriver:
                drivers.add(driver)
            elif event_type == Events.NewRider:
                idle_riders.add(rider)
            elif event_type == Events.RiderMatch:
                idle_riders.remove(rider)
                waiting_riders.add(rider)
            elif event_type == Events.RiderPickup:
                waiting_riders.remove(rider)
            elif event_type == Events.RiderDropOff:
                rider_archive.add(rider)
            elif event_type == Events.RiderCancelled:
                idle_riders.discard(rider)
                waiting_riders.discard(rider)
                rider_archive.add(rider)
            elif event_type == Events.DriverComplete:
                drivers.remove(driver)
                driver_archive.add(driver)

    # Simulation logic
    for rider in idle_riders:
        if rider.cancel_time <= current_time and rider.matched_time is None:
            rider.cancel(current_time)
        else:
            rider_matching(rider, drivers, state, current_time)
    for driver in drivers:
        driver.move(current_time)

    # Drawing
    if background is None:
        background = pygame.Surface(screen_size)
        background.fill(Colors.Background.value)
        for loc in state.center_locations:
            pygame.draw.ellipse(background, Colors.CenterArea.value, loc.on_screen)
        for loc in state.residential_areas:
            pygame.draw.ellipse(background, Colors.ResidentialArea.value, loc.on_screen)
        for u, v in state.graph.edge_list():
            pygame.draw.line(
                background,
                Colors.Edge.value,
                state.graph.get_node_data(u).on_screen,
                state.graph.get_node_data(v).on_screen,
                1,
            )
        for coord in state.graph.nodes():
            pygame.draw.circle(background, Colors.Building.value, coord.on_screen, 2)
    screen.blit(background, (0, 0))
    screen.blit(font.render(str(current_time.day_time), 1, Colors.Text.value), (5, 5))
    for driver in drivers:
        pygame.draw.circle(screen, Colors.Driver.value, driver.position.on_screen, 3)
        if driver.route and len(driver.route) > 0:
            route = [driver.position.on_screen] + [
                coord.on_screen for _, coord in driver.route
            ]
            pygame.draw.lines(screen, Colors.Route.value, False, route, 2)
        for rider in driver.riders:
            pygame.draw.circle(
                screen,
                Colors.DestinationPoint.value,
                state.graph.get_node_data(rider.end_node).on_screen,
                3,
            )
        pygame.draw.circle(
            screen,
            Colors.DestinationPoint.value,
            state.graph.get_node_data(driver.end_node).on_screen,
            3,
        )
    for rider in idle_riders:
        pygame.draw.circle(screen, Colors.IdleRider.value, rider.position.on_screen, 3)
    for rider in waiting_riders:
        pygame.draw.circle(
            screen, Colors.WaitingRider.value, rider.position.on_screen, 3
        )

    pygame.display.update()
    clock.tick(state.frame_rate)

pygame.quit()

# Generate total statistics
stats = calculate_statistics(
    rider_archive | idle_riders | waiting_riders, driver_archive | drivers, current_time
)
pprint(stats)
