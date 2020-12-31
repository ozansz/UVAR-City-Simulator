import io
import random
import numpy as np
from PIL import Image
import networkx as nx
from progress.bar import Bar
import matplotlib.pyplot as plt

class City(object):
    CAR_COLORS = ["b", "g", "r", "c", "m", "y", "k"]

    def __init__(self, num_cars: int, topology_rank: int):
        plt.rcParams["figure.figsize"] = (2 * topology_rank, 2 * topology_rank)

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

            plt.plot(car_coord[0], car_coord[1], car.car_color + "o")

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

class SquareGridRoadTopology(object):
    def __init__(self, num_nodes_side: int, random_weights: bool = False):
        self.num_nodes_side = num_nodes_side
        self.adj = self.generate_grid_adj(num_nodes_side, random_weights)
        
        #self.A = np.matrix(self.adj)
        #self.G = nx.from_numpy_matrix(self.A)

        self.G = nx.DiGraph()

        for i in range(num_nodes_side):
            for j in range(num_nodes_side):
                self.G.add_node(num_nodes_side * i + j, pos=(2 * j, 2 * i))

        for i in range(len(self.adj)):
            for j in range(len(self.adj)):
                if self.adj[i][j] > 0:
                    self.G.add_edge(i, j, weight=self.adj[i][j])

        self._G_pos = pos = nx.get_node_attributes(self.G,'pos')

    @property
    def joints(self):
        return [self.num_nodes_side * i + j for i in range(self.num_nodes_side) for j in range(self.num_nodes_side)]

    @property
    def road_segments(self):
        return list(nx.get_edge_attributes(self.G, 'weight').keys())

    def neighbor_segments_to(self, segment: tuple):
        return [elem for elem in self.road_segments if elem[0] == segment[1]]

    def is_segment_vertical(self, segment: tuple):
        return (self._G_pos[segment[1]][0] - self._G_pos[segment[0]][0]) == 0

    def is_segment_horizontal(self, segment: tuple):
        return (self._G_pos[segment[1]][1] - self._G_pos[segment[0]][1]) == 0

    def is_segment_positive(self, segment: tuple):
        if self.is_segment_horizontal(segment):
            return (self._G_pos[segment[1]][0] - self._G_pos[segment[0]][0]) > 0

        return (self._G_pos[segment[1]][1] - self._G_pos[segment[0]][1]) > 0

    def plot(self):
        #pos = nx.get_node_attributes(self.G,'pos')
        nx.draw(self.G, self._G_pos, with_labels=True, connectionstyle='arc3, rad = 0.1')
        labels = nx.get_edge_attributes(self.G, 'weight')
        nx.draw_networkx_edge_labels(self.G, self._G_pos, edge_labels=labels)
        #nx.draw_networkx(self.G, with_labels=True)
        #plt.plot(1, 3.8, "ro")
        plt.draw()
        #plt.show()

    @staticmethod
    def generate_grid_adj(num_nodes_side: int, random_weights: bool):
        weight_generator = lambda: 1

        if random_weights:
            weight_generator = lambda:  random.randint(1, 10)

        n = num_nodes_side**2
        M = [[0 for _ in range(n)] for _ in range(n)]

        for r in range(num_nodes_side):
            for c in range(num_nodes_side):
                i = r * num_nodes_side + c
                # Two inner diagonals
                if c > 0:
                    _w = weight_generator()
                    M[i-1][i] = _w
                    M[i][i-1] = _w
                # Two outer diagonals
                if r > 0:
                    _w = weight_generator()
                    M[i-num_nodes_side][i] = _w
                    M[i][i-num_nodes_side] = _w
        
        return M