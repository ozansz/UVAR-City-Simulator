import io
import random
import numpy as np
from PIL import Image
from progress.bar import Bar
import matplotlib.pyplot as plt

from topology import SquareGridRoadTopology

class City(object):
    CAR_COLORS = ["b", "g", "r", "c", "m", "y", "k"]

    def __init__(self, num_cars: int, topology_rank: int):
        plt.figure(figsize=(max(1.5 * topology_rank, 12), max(1.5 * topology_rank, 12)))
        #plt.rcParams["figure.figsize"] = (1.5 * topology_rank, 1.5 * topology_rank)

        self.topology = SquareGridRoadTopology(topology_rank, random_weights=True)

        self.cars = dict()
        _road_segments = self.topology.road_segments

        for i in range(num_cars):
            random_segment = random.choice(_road_segments)
            segment_len = self.topology.adj[random_segment[0]][random_segment[1]]
            random_segment_point = random.randint(0, segment_len)

            car_coord = list(self.topology._G_pos[random_segment[0]])
            segment_end_coord = list(self.topology._G_pos[random_segment[1]])
            car_direction_positive = self.topology.is_segment_positive(random_segment)
            car_direction_horizontal = self.topology.is_segment_horizontal(random_segment)

            if car_direction_positive:
                _step = 2 * random_segment_point / segment_len
            else:
                _step = -2 * random_segment_point / segment_len
            
            if car_direction_horizontal:
                car_coord[0] += _step
            else:
                car_coord[1] += _step

            self.cars[i] = Car(car_id=i, segment=random_segment,
                segment_loc=random_segment_point, segment_len=segment_len,
                car_velocity=random.randint(2, 10) / 10, car_color=self.CAR_COLORS[i % len(self.CAR_COLORS)],
                car_coord=car_coord, car_direction_positive=car_direction_positive,
                car_direction_horizontal=car_direction_horizontal, segment_end_coord=segment_end_coord)

    def simulation_step(self):
        for car in self.cars.values():
            if car.reached_segment_end:
                # No explicit looping
                different_segments = self.topology.neighbor_segments_to(car.segment)
                different_segments.remove((car.segment[1], car.segment[0]))

                next_random_segment = random.choice(different_segments)       
                new_segment_len = self.topology.adj[next_random_segment[0]][next_random_segment[1]]

                new_car_coord = list(self.topology._G_pos[next_random_segment[0]])      
                new_segment_end_coord = list(self.topology._G_pos[next_random_segment[1]])
                new_direction_positive = self.topology.is_segment_positive(next_random_segment)
                new_direction_horizontal = self.topology.is_segment_horizontal(next_random_segment)

                #print(f"Car #{car.car_id} {car.segment} => {next_random_segment}")

                car.update(next_random_segment, 0, new_segment_len, new_direction_positive, new_direction_horizontal, new_car_coord, new_segment_end_coord)
            else:
                car.simulation_step()
                #print(f"Car #{car.car_id} {car.segment} {100 * car.segment_loc/car.segment_len}% ({car.segment_loc}/{car.segment_len})")

    def plot(self):
        ax = plt.gca()

        self.topology.plot()

        for car in self.cars.values():
            car_coord = car.car_coord[:]

            if car.car_direction_positive:
                _step = 0.1
            else:
                _step = -0.1

            if car.car_direction_horizontal:
                car_coord[1] += _step
            else:
                car_coord[0] += _step

            ax.add_patch(plt.Circle(car_coord, radius=.17, color=car.car_color, zorder=1000))
            ax.annotate(car.car_id, xy=car_coord, fontsize=12, color="white", #ha="center")
                verticalalignment='center', horizontalalignment='center', zorder=1001)

            #plt.plot(car_coord[0], car_coord[1], car.car_color + "o")
            #plt.text(car_coord[0], car_coord[1], car.car_id, fontsize=10)

    def show_plot(self):
        plt.show()

    def save_simualtion_gif(self, steps: int):
        with Bar("Processing", max=steps+1) as bar:
            images = list()

            for _ in range(steps):
                plt.clf()

                self.plot()

                buf = io.BytesIO()
                plt.savefig(buf, format="png")
                buf.seek(0)
                images.append(Image.open(buf))

                self.simulation_step()

                bar.next()

            images[0].save("out.gif", save_all=True, append_images=images)
            bar.next()

class Car(object):
    def __init__(self, car_id: int, segment: tuple, segment_loc: int, segment_len: int, car_velocity: int, car_color: str, car_coord: tuple, car_direction_positive: bool, car_direction_horizontal: bool, segment_end_coord: tuple):
        self.car_id = car_id
        self.segment = segment
        self.segment_loc = segment_loc
        self.segment_len = segment_len
        self.car_velocity = car_velocity
        self.car_color = car_color
        self.car_coord = car_coord
        self.car_direction_positive = car_direction_positive
        self.car_direction_horizontal = car_direction_horizontal
        self.segment_end_coord = segment_end_coord

        self.reached_segment_end = False

        if segment_loc >= segment_len:
            self.reached_segment_end = True

    def update(self, next_segment, next_segment_point, new_segment_len, new_direction_positive, new_direction_horizontal, new_car_coord, new_segment_end_coord):
        self.segment = next_segment
        self.segment_loc = next_segment_point
        self.segment_len = new_segment_len
        self.car_direction_positive = new_direction_positive
        self.car_direction_horizontal = new_direction_horizontal
        self.car_coord = new_car_coord
        self.segment_end_coord = new_segment_end_coord

        self.reached_segment_end = False

        if self.segment_loc >= self.segment_len:
            self.reached_segment_end = True

    def simulation_step(self):
        if not self.reached_segment_end:
            self.segment_loc += self.car_velocity

            if self.segment_loc >= self.segment_len:
                self.reached_segment_end = True
                self.car_coord = self.segment_end_coord
            else:
                if self.car_direction_positive:
                    _step = 2 * self.car_velocity / self.segment_len
                else:
                    _step = -2 * self.car_velocity / self.segment_len
                
                if self.car_direction_horizontal:
                    self.car_coord[0] += _step
                else:
                    self.car_coord[1] += _step