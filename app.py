import os
from pprint import pprint
import random
from typing import Optional

import pygame

from constants import Colors, Events
from entity import Driver, Rider
from pso import RideSharingPSOInstance
from simulation_gen import SimulationGenerator
from state import SimulationState
from stats import calculate_statistics

os.environ["SDL_VIDEO_CENTERED"] = "1"

# Set this for deterministic simulation results
random_seed: Optional[int] = None
random.seed(random_seed)

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
frame_rate = 30
simulation_speed = 4

state = SimulationState("Vilnius, Lithuania", screen_size, frame_rate, simulation_speed)
sg = SimulationGenerator(state)
drivers: set[Driver] = set()
idle_riders: set[Rider] = set()
waiting_riders: set[Rider] = set()
driver_archive: set[Driver] = set()
rider_archive: set[Rider] = set()
sg.start()  # starts recurring new driver and new rider events generation
pso_matcher = RideSharingPSOInstance(state)

while running:
    current_time = state.get_time()

    # Event processing
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
            sg.stop()
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
            elif event_type == Events.RiderCancel:
                idle_riders.discard(rider)
                waiting_riders.discard(rider)
                rider_archive.add(rider)
            elif event_type == Events.DriverComplete:
                drivers.remove(driver)
                driver_archive.add(driver)
            elif event_type == Events.TrafficUpdate:
                state.update_traffic(current_time)
                for driver in drivers:
                    driver.recalculate_route()

    # Simulation logic
    for rider in idle_riders:
        if rider.cancel_time <= current_time and rider.matched_time is None:
            rider.cancel(current_time)

    pso_matcher.match_riders(idle_riders, drivers, current_time)

    for driver in drivers:
        driver.move(state.speed_ratio, current_time)

    # Drawing
    if background is None:
        background = pygame.Surface(screen_size)
        background.fill(Colors.Background.value)
        for loc in state.center_locations:
            pygame.draw.ellipse(background, Colors.CenterArea.value, loc.on_screen)
        for loc in state.residential_areas:
            pygame.draw.ellipse(background, Colors.ResidentialArea.value, loc.on_screen)
        for edge in state.graph.edges():
            pygame.draw.line(
                background,
                Colors.Edge.value,
                edge.starting_node_coords.on_screen,
                edge.ending_node_coords.on_screen,
                1,
            )
        for node in state.graph.nodes():
            pygame.draw.circle(
                background, Colors.Building.value, node.coords.on_screen, 2
            )
    screen.blit(background, (0, 0))
    screen.blit(font.render(str(current_time.day_time), 1, Colors.Text.value), (5, 5))
    for driver in drivers:
        if driver.route and driver.current_edge is not None:
            route = [
                driver.current_edge.on_screen,
                driver.current_edge.edge.ending_node_coords.on_screen,
            ] + [coord.ending_node_coords.on_screen for coord in driver.route]
            pygame.draw.lines(screen, Colors.Route.value, False, route, 2)
            pygame.draw.circle(
                screen, Colors.Driver.value, driver.current_edge.on_screen, 3
            )
        for rider in driver.riders:
            pygame.draw.circle(
                screen,
                Colors.DestinationPoint.value,
                state.graph.get_node_data(rider.end_node).coords.on_screen,
                3,
            )
        pygame.draw.circle(
            screen,
            Colors.DestinationPoint.value,
            state.graph.get_node_data(driver.end_node).coords.on_screen,
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
