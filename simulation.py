import io
import math
import random
import numpy as np
from PIL import Image
from progress.bar import Bar
import matplotlib.pyplot as plt

from topology import SquareGridRoadTopology

UAV_RADIUS = 2.15
UAV_DISP_RANGE = (.0, .1)
UAV_REPOSITION_THRESH = .15
UAV_REPOSITION_STEP = .05
UAV_DISP_RANDOMNESS = .3

CAR_CONTACT_SEGMENT_RANGE = 2
CAR_CONTACT_RADIUS = 4.5

class City(object):
    CAR_COLORS = ["b", "g", "c", "m", "y", "k", "b"]

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

        self.uavs = dict()
        _uav_index = 0

        for i in range(1, 2*(topology_rank-1), 2):
            for j in range(1, 2*(topology_rank-1), 2):
                self.uavs[_uav_index] = UAV(_uav_index, (i, j), UAV_RADIUS, UAV_DISP_RANGE,
                    self.CAR_COLORS[i % len(self.CAR_COLORS)])
                _uav_index += 1

    def simulation_step(self):
        for uav in self.uavs.values():
            uav.simulation_step()

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

        for uav in self.uavs.values():
            contact_uavs = [k for k, v in self.uavs.items() if (v.uav_id != uav.uav_id) and (uav.distance_to(v.coord) <= uav.radius_of_operation)]
            contact_cars = [k for k, v in self.cars.items() if uav.distance_to(v.car_coord) <= uav.radius_of_operation]

            uav.update_contacts(contact_cars, contact_uavs)

        for car in self.cars.values():
            new_contacts = list()
            knn_segments = self.topology.knn_segments_of(car.segment, k=CAR_CONTACT_SEGMENT_RANGE)

            for _car_id, _car in self.cars.items():
                if (_car_id != car.car_id) and (_car.segment in knn_segments) and (car.distance_to(_car.car_coord) <= CAR_CONTACT_RADIUS):
                    new_contacts.append(_car_id)

            car.update_contacts(new_contacts)

    def plot(self):
        ax = plt.gca()

        self.topology.plot()

        car_plot_pairs = list()

        for car in self.cars.values():
            for car_id in car.cars_in_contact:
                if ((car_id, car.car_id) not in car_plot_pairs) and (((car.car_id, car_id) not in car_plot_pairs)):
                    _car = self.cars[car_id]
                    car_coord = _car.plot_coord
                    self_coord = car.plot_coord
                    plt.plot([self_coord[0], car_coord[0]], [self_coord[1], car_coord[1]], "g--")
                    car_plot_pairs.append((car.car_id, car_id))

        uav_plot_pairs = list()

        for uav in self.uavs.values():
            for car_id in uav.cars_in_contact:
                _car = self.cars[car_id]
                car_coord = _car.plot_coord
                plt.plot([uav.coord[0], car_coord[0]], [uav.coord[1], car_coord[1]], "r--")
            for uav_id in uav.uavs_in_contact:
                if ((uav_id, uav.uav_id) not in uav_plot_pairs) and (((uav.uav_id, uav_id) not in uav_plot_pairs)):
                    _uav = self.uavs[uav_id]
                    plt.plot([uav.coord[0], _uav.coord[0]], [uav.coord[1], _uav.coord[1]], "b--")
                    uav_plot_pairs.append((uav.uav_id, uav_id))

        for car in self.cars.values():
            car_coord = car.plot_coord

            ax.add_patch(plt.Circle(car_coord, radius=.17, color=car.car_color, zorder=1000))
            ax.annotate(car.car_id, xy=car_coord, fontsize=12, color="white", #ha="center")
                verticalalignment='center', horizontalalignment='center', zorder=1001)

            #plt.plot(car_coord[0], car_coord[1], car.car_color + "o")
            #plt.text(car_coord[0], car_coord[1], car.car_id, fontsize=10)

        for uav in self.uavs.values():
            ax.add_patch(plt.Circle(uav.coord, radius=.25, color=uav.uav_color, zorder=1000))
            ax.annotate(uav.uav_id, xy=uav.coord, fontsize=13, color="white", #ha="center")
                verticalalignment='center', horizontalalignment='center', zorder=1001)

    def show_plot(self):
        plt.show()

    def save_simualtion_gif(self, steps: int):
        with Bar("Processing", max=steps+1) as bar:
            images = list()

            for _ in range(steps):
                plt.clf()

                self.simulation_step()
                self.plot()

                buf = io.BytesIO()
                plt.savefig(buf, format="png")
                buf.seek(0)
                images.append(Image.open(buf))


                bar.next()

            images[0].save("out.gif", save_all=True, append_images=images)
            bar.next()

class UAV(object):
    def __init__(self, uav_id: int, coord: tuple, radius_of_operation: float, random_displacement_range: tuple, uav_color: str):
        self._origin_coord = coord
        self.uav_id = uav_id
        self.coord = list(coord)
        self.radius_of_operation = radius_of_operation
        self.random_displacement_range = random_displacement_range
        self.uav_color = uav_color

        self.state_reposition = False

        self.cars_in_contact = list()
        self.uavs_in_contact = list()

    def update_contacts(self, cars: list, uavs: list):
        self.cars_in_contact = cars
        self.uavs_in_contact = uavs

    def simulation_step(self):
        if self.state_reposition or (self.distance_to(self._origin_coord) >= UAV_REPOSITION_THRESH):
            self.state_reposition = True

            if self.coord[0] - self._origin_coord[0] < 0:
                self.coord[0] += UAV_REPOSITION_STEP
            else:
                self.coord[0] -= UAV_REPOSITION_STEP

            if self.coord[1] - self._origin_coord[1] < 0:
                self.coord[1] += UAV_REPOSITION_STEP
            else:
                self.coord[1] -= UAV_REPOSITION_STEP

            if self.distance_to(self._origin_coord) < UAV_REPOSITION_THRESH:
                self.state_reposition = False
        else:
            if (random.randint(0, 100) / 100) >= UAV_DISP_RANDOMNESS:
                random_angle = random.randint(0, 360)
                random_angle *= (math.pi / 180)
                random_disp = random.randint(int(self.random_displacement_range[0] * 1000), int(self.random_displacement_range[1] * 1000)) / 1000

                self.coord[0] += math.cos(random_angle) * random_disp
                self.coord[1] += math.sin(random_angle) * random_disp

    def distance_to(self, coord: tuple):
        return ((self.coord[0] - coord[0])**2 + (self.coord[1] - coord[1])**2)**.5

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

        self.cars_in_contact = list()

    @property
    def plot_coord(self):
        car_coord = self.car_coord[:]

        if self.car_direction_positive:
            _step = 0.1
        else:
            _step = -0.1

        if self.car_direction_horizontal:
            car_coord[1] += _step
        else:
            car_coord[0] += _step

        return car_coord

    def update_contacts(self, cars: list):
        self.cars_in_contact = cars

    def distance_to(self, coord: tuple):
        return ((self.car_coord[0] - coord[0])**2 + (self.car_coord[1] - coord[1])**2)**.5

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