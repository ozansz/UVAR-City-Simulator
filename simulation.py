import io
import math
import pickle
import random
import numpy as np
from PIL import Image
import networkx as nx
from progress.bar import Bar
import matplotlib.pyplot as plt
from datetime import datetime as dt

from topology import SquareGridRoadTopology

UAV_RADIUS = 2.15
UAV_DISP_RANGE = (.0, .1)
UAV_REPOSITION_THRESH = .15
UAV_REPOSITION_STEP = .05
UAV_DISP_RANDOMNESS = .3

CAR_CONTACT_SEGMENT_RANGE = 5 # Just for opposition check
CAR_CONTACT_RANGE_AS_ROAD_UNITS = 5
ROAD_SLICING_RANGE = 4
SEGMENT_LENS = 12
CAR_NEAR_INTERSECTION_THRESH = 1

SPARSE_INTERVAL_RECT_HEIGHT_WIDTH = .5

real_coord_to_plot_coord = lambda t: (t[0] * 2 / SEGMENT_LENS, t[1] * 2 / SEGMENT_LENS)
square_distance = lambda x1, y1, x2, y2: ((x1 - x2)**2 + (y1 - y2)**2)**.5

class City(object):
    CAR_COLORS = ["b", "g", "c", "m", "y", "k", "b"]

    def __init__(self, num_cars: int, topology_rank: int):
        plt.figure(figsize=(max(1.5 * topology_rank, 12), max(1.5 * topology_rank, 12)))
        #plt.rcParams["figure.figsize"] = (1.5 * topology_rank, 1.5 * topology_rank)

        self.num_cars = num_cars
        self.topology_rank = topology_rank

        self.topology = SquareGridRoadTopology(topology_rank, random_weights=False, constant_weight=SEGMENT_LENS)

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

            self.cars[i] = Car(self, car_id=i, segment=random_segment,
                segment_loc=random_segment_point, segment_len=segment_len,
                car_velocity=random.randint(2, 10) / 10, car_color=self.CAR_COLORS[i % len(self.CAR_COLORS)],
                car_coord=car_coord, car_direction_positive=car_direction_positive,
                car_direction_horizontal=car_direction_horizontal, segment_end_coord=segment_end_coord)

        self.uavs = dict()
        _uav_index = 0

        for i in range(1, 2*(topology_rank-1), 2):
            for j in range(1, 2*(topology_rank-1), 2):
                self.uavs[_uav_index] = UAV(self, _uav_index, (i, j), UAV_RADIUS, UAV_DISP_RANGE,
                    self.CAR_COLORS[i % len(self.CAR_COLORS)])
                _uav_index += 1

    def _real_coord_of_joint(self, joint_id: int):
        return (self.topology._G_pos[joint_id][0] * SEGMENT_LENS / 2, self.topology._G_pos[joint_id][1] * SEGMENT_LENS / 2)

    def _cars_in_segment(self, segment: tuple):
        car_ids = []

        for car_id, car in self.cars.items():
            if car.segment == segment or car.segment == (segment[1], segment[0]):
                car_ids.append(car_id)

        return car_ids

    def sorted_table_of_density(self, segment: tuple):
        assets = [
            (self._real_coord_of_joint(segment[0]), "i", segment[0]),
            (self._real_coord_of_joint(segment[1]), "i", segment[1]),
        ]

        assets += [(self.cars[car_id].real_coord, "c", car_id) for car_id in self._cars_in_segment(segment)]

        if self.topology.is_segment_horizontal(segment):
            assets = sorted(assets, key=lambda x: x[0][0])
        else:
            assets = sorted(assets, key=lambda x: x[0][1])

        return assets

    def segment_connectedness(self, segment):
        rv_over_dists = []
        tod = self.sorted_table_of_density(segment)

        for i in range(len(tod)-1):
            ent_i = tod[i]
            ent_i_plus_1 = tod[i+1]

            if ent_i[0][0] == ent_i_plus_1[0][0] and ent_i[0][1] == ent_i_plus_1[0][1]:
                sq_dist = CAR_CONTACT_RANGE_AS_ROAD_UNITS
            else:
                sq_dist = square_distance(ent_i[0][0], ent_i[0][1], ent_i_plus_1[0][0], ent_i_plus_1[0][1])

            rod = CAR_CONTACT_RANGE_AS_ROAD_UNITS / sq_dist
            rv_over_dists.append(math.floor(rod))
            #rv_over_dists.append(rod)

        mult = 1

        for x in rv_over_dists:
            mult *= x

        return abs(mult)

    def segment_sparse_intervals(self, segment: tuple):
        rv_over_dists = []
        tod = self.sorted_table_of_density(segment)

        for i in range(len(tod)-1):
            ent_i = tod[i]
            ent_i_plus_1 = tod[i+1]

            if ent_i[0][0] == ent_i_plus_1[0][0] and ent_i[0][1] == ent_i_plus_1[0][1]:
                sq_dist = CAR_CONTACT_RANGE_AS_ROAD_UNITS
            else:
                sq_dist = square_distance(ent_i[0][0], ent_i[0][1], ent_i_plus_1[0][0], ent_i_plus_1[0][1])

            rod = CAR_CONTACT_RANGE_AS_ROAD_UNITS / sq_dist
            rv_over_dists.append(math.floor(rod))

        ret = []

        for i in range(len(tod)-1):
            if rv_over_dists[i] == 0:
                ret.append((tod[i][0], tod[i+1][0]))

        return ret

    def _num_cars_in_segment_areas(self, segment: tuple):
        if segment[0] > segment[1]:
            segment = (segment[1], segment[0]) # Normalize

        car_ids = self._cars_in_segment(segment)
        area_freqs = dict()

        if self.topology.is_segment_horizontal(segment):
            lower_x_coord = self._real_coord_of_joint(segment[0])[0]
            upper_x_coord = lower_x_coord + ROAD_SLICING_RANGE
            upper_x_coord_max = self._real_coord_of_joint(segment[1])[0]

            area_index = 0
            added_ids = set()

            while upper_x_coord < (upper_x_coord_max + ROAD_SLICING_RANGE):
                area_freqs[area_index] = 0

                for car_id in car_ids:
                    if lower_x_coord <= self.cars[car_id].real_coord[0] <= upper_x_coord:
                        area_freqs[area_index] += 1

                        added_ids.add(car_id)
                
                for car_id in added_ids:
                    car_ids.remove(car_id)

                lower_x_coord = upper_x_coord
                upper_x_coord = lower_x_coord + ROAD_SLICING_RANGE

                added_ids = set()
                area_index += 1
        else:
            lower_y_coord = self._real_coord_of_joint(segment[0])[1]
            upper_y_coord = lower_y_coord + ROAD_SLICING_RANGE
            upper_y_coord_max = self._real_coord_of_joint(segment[1])[1]

            area_index = 0
            added_ids = set()

            while upper_y_coord < (upper_y_coord_max + ROAD_SLICING_RANGE):
                area_freqs[area_index] = 0

                for car_id in car_ids:
                    if lower_y_coord <= self.cars[car_id].real_coord[1] <= upper_y_coord:
                        area_freqs[area_index] += 1

                        added_ids.add(car_id)
                
                for car_id in added_ids:
                    car_ids.remove(car_id)

                lower_y_coord = upper_y_coord
                upper_y_coord = lower_y_coord + ROAD_SLICING_RANGE

                added_ids = set()
                area_index += 1

        return area_freqs

    def average_num_vehicles_per_area(self, segment: tuple):
        area_freq = self._num_cars_in_segment_areas(segment)
        return sum(area_freq.values()) / len(area_freq.keys())

    def std_area_densities(self, segment: tuple):
        mu = self.average_num_vehicles_per_area(segment)
        area_freq = self._num_cars_in_segment_areas(segment)

        return (sum([(f - mu)**2 for f in area_freq.values()]) / len(area_freq.keys()))**.5

    def score_g(self, segment: tuple, target_section: tuple):
        Dw1 = nx.shortest_path_length(self.topology.G, source=segment[0], target=target_section[0])
        Dw2 = nx.shortest_path_length(self.topology.G, source=segment[0], target=target_section[1])
        Dw3 = nx.shortest_path_length(self.topology.G, source=segment[1], target=target_section[0])
        Dw4 = nx.shortest_path_length(self.topology.G, source=segment[1], target=target_section[1])

        Dw = (Dw1 + Dw2 + Dw3 + Dw4) / 4

        return (self.segment_connectedness(segment) * CAR_CONTACT_RANGE_AS_ROAD_UNITS) / ((1 + self.std_area_densities(segment)) * Dw)

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
                if (_car_id != car.car_id) and (_car.segment in knn_segments) and (car.real_distance_to(_car) <= CAR_CONTACT_RANGE_AS_ROAD_UNITS):
                    new_contacts.append(_car_id)

            car.update_contacts(new_contacts)

        #for unique_segment in self.topology.unique_road_segments:
        #    print(unique_segment, self.segment_connectedness(unique_segment), self.sorted_table_of_density(unique_segment), self._num_cars_in_segment_areas(unique_segment))
        #    print()
        #
        #print()
        #print()

    def plot(self):
        ax = plt.gca()

        self.topology.plot()

        for unique_segment in self.topology.unique_road_segments:
            sparse_intervals = self.segment_sparse_intervals(unique_segment)

            for interval in sparse_intervals:
                if self.topology.is_segment_horizontal(unique_segment):
                    int0_coord = real_coord_to_plot_coord(interval[0])
                    int1_coord = real_coord_to_plot_coord(interval[1])
                    ax.add_patch(plt.Rectangle((int0_coord[0], int0_coord[1] - (SPARSE_INTERVAL_RECT_HEIGHT_WIDTH / 2)), width=int1_coord[0]-int0_coord[0], height=SPARSE_INTERVAL_RECT_HEIGHT_WIDTH, fc=(1,0,0,0.5), zorder=1000))
                else:
                    int0_coord = real_coord_to_plot_coord(interval[0])
                    int1_coord = real_coord_to_plot_coord(interval[1])
                    ax.add_patch(plt.Rectangle((int0_coord[0] - (SPARSE_INTERVAL_RECT_HEIGHT_WIDTH / 2), int0_coord[1]), width=SPARSE_INTERVAL_RECT_HEIGHT_WIDTH, height=int1_coord[1]-int0_coord[1], fc=(1,0,0,0.5), zorder=1000))

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

    def save_simlatioon_with_graphics(self, steps: int, filename: str = "out.gif"):
        with Bar("Processing", max=steps+2) as bar:
            images = list()
            topo_images = list()

            sim_iters = dict()

            for step_index in range(1, steps + 1):
                plt.clf()

                self.simulation_step()
                self.plot()

                buf = io.BytesIO()
                plt.savefig(buf, format="png")
                buf.seek(0)
                images.append(Image.open(buf))

                plt.clf()

                self.plot_network_topology()
                buf = io.BytesIO()
                plt.savefig(buf, format="png")
                buf.seek(0)
                topo_images.append(Image.open(buf))

                step_data = {
                    "network": self.current_network_topology,
                    "cars": self.cars,
                    "uavs": self.uavs,
                    "metrics": {segment: {
                        "stod": self.sorted_table_of_density(segment),
                        "connectedness": self.segment_connectedness(segment),
                        "anvpa": self.average_num_vehicles_per_area(segment),
                        "stdds": self.std_area_densities(segment)
                    } for segment in self.topology.unique_road_segments}
                }

                sim_iters[step_index] = step_data

                bar.next()

            images[0].save(filename, save_all=True, append_images=images)
            topo_images[0].save(f"topology_{filename}", save_all=True, append_images=topo_images)
            bar.next()

            with open(f"dump_{self.num_cars}_{self.topology_rank}_{str(dt.now().timestamp()).split('.')[0]}.pkl", "wb") as fp:
                pickle.dump(sim_iters, fp, protocol=pickle.HIGHEST_PROTOCOL)

            bar.next()

    def plot_network_topology(self):
        topology = self.current_network_topology
        pos = nx.circular_layout(topology)
        nx.draw(topology, pos, with_labels=True, node_size=1000, font_size=15)
        labels = nx.get_edge_attributes(topology, 'weight')
        nx.draw_networkx_edge_labels(topology, pos, edge_labels=labels)
        plt.draw()

    @property
    def current_network_topology(self):
        G = nx.Graph()

        for uav_id, uav in self.uavs.items():
            G.add_node(f"U{uav_id}")#, pos=uav._origin_coord)

        for car_id in self.cars.keys():
            G.add_node(f"C{car_id}")

        uav_edged_ctr = list()
        car_edged_ctr = list()

        for uav_id, uav in self.uavs.items():
            for other_uav_id in uav.uavs_in_contact:
                if ((uav_id, other_uav_id) not in uav_edged_ctr) and ((other_uav_id, uav_id) not in uav_edged_ctr):
                    G.add_edge(f"U{uav_id}", f"U{other_uav_id}", weight=uav.distance_to(self.uavs[other_uav_id].coord)*SEGMENT_LENS/2)
                    uav_edged_ctr.append((uav_id, other_uav_id))

            for car_id in uav.cars_in_contact:
                G.add_edge(f"U{uav_id}", f"C{car_id}", weight=uav.distance_to(self.cars[car_id].car_coord)*SEGMENT_LENS/2)

        for car_id, car in self.cars.items():
            for other_car_id in car.cars_in_contact:
                if ((car_id, other_car_id) not in car_edged_ctr) and ((other_car_id, car_id) not in car_edged_ctr):
                    G.add_edge(f"C{car_id}", f"C{other_car_id}", weight=car.real_distance_to(self.cars[other_car_id]))
                    car_edged_ctr.append((car_id, other_car_id))

        return G

class UAV(object):
    def __init__(self, city: City, uav_id: int, coord: tuple, radius_of_operation: float, random_displacement_range: tuple, uav_color: str):
        self.__city = city
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

    def nearest_car_in_section_near_intersection(self, section: tuple, intersection_id: int):
        min_dist = float("inf")
        min_dist_car_id = None

        intersection_real_coord = self.__city._real_coord_of_joint(intersection_id)

        for car_id, car in self.cars_in_contact:
            dist = square_distance(intersection_real_coord[0], intersection_real_coord[1], car.real_coord[0], car.real_coord[1])

            if dist < min_dist:
                min_dist = dist
                min_dist_car_id = car_id

        return (min_dist_car_id, min_dist)

class Car(object):
    def __init__(self, city: City, car_id: int, segment: tuple, segment_loc: int, segment_len: int, car_velocity: int, car_color: str, car_coord: tuple, car_direction_positive: bool, car_direction_horizontal: bool, segment_end_coord: tuple):
        self.__city = city
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

        self.real_coord = [self.car_coord[0] * self.segment_len / 2, self.car_coord[1] * self.segment_len / 2]

        self.reached_segment_end = False

        if segment_loc >= segment_len:
            self.reached_segment_end = True

        self.cars_in_contact = list()

    def closest_neighbor_car_to_point2(self, coord: tuple):
        min_distance = float("inf")
        min_dist_car_id = None

        for car_id in self.cars_in_contact:
            car = self.__city.cars[car_id]
            dist = square_distance(coord[0], coord[1], car.real_coord[0], car.real_coord[1])

            if dist < min_distance:
                min_distance = dist
                min_dist_car_id = car_id

        return (min_dist_car_id, min_distance)

    def closest_neighbor_car_to_intersection_point(self, joint_id: int):
        joint_coord = self.__city._real_coord_of_joint(joint_id)

        min_distance = float("inf")
        min_dist_car_id = None

        for car_id in self.cars_in_contact:
            car = self.__city.cars[car_id]
            dist = square_distance(joint_coord[0], joint_coord[1], car.real_coord[0], car.real_coord[1])

            if dist < min_distance:
                min_distance = dist
                min_dist_car_id = car_id

        return (min_dist_car_id, min_distance)

    @property
    def near_intersection_point(self):
        joint1_coord = self.__city._real_coord_of_joint(self.segment[0])
        joint2_coord = self.__city._real_coord_of_joint(self.segment[1])

        if square_distance(self.real_coord[0], self.real_coord[1], joint1_coord[0], joint1_coord[1]) <= CAR_NEAR_INTERSECTION_THRESH:
            return True
        
        if square_distance(self.real_coord[0], self.real_coord[1], joint2_coord[0], joint2_coord[1]) <= CAR_NEAR_INTERSECTION_THRESH:
            return True

        return False

    @property
    def nearest_joint(self):
        joint1_coord = self.__city._real_coord_of_joint(self.segment[0])
        joint2_coord = self.__city._real_coord_of_joint(self.segment[1])

        dist1 = square_distance(self.real_coord[0], self.real_coord[1], joint1_coord[0], joint1_coord[1])
        dist2 = square_distance(self.real_coord[0], self.real_coord[1], joint2_coord[0], joint2_coord[1])

        if dist1 < dist2:
            return (self.segment[0], dist1)

        return (self.segment[1], dist2)

    def next_intersection_to_target_segment(self, target_section: tuple):
        _seg = self.segment

        if self.nearest_joint != _seg[1]:
            _seg = (_seg[1], _seg[0])

        next_possible_segments = [s for s in self.__city.topology.neighbor_segments_to(_seg) if s not in [self.segment, (self.segment[1], self.segment[0])]]
        score_gs = [{"score": self.__city.score_g(seg, target_section), "next_I": seg[1]} for seg in next_possible_segments]

        best_one = sorted(score_gs, key=lambda x: x["score"], reverse=True)[0]      

        if len(best_one) == 0 or best_one["score"] == 0:
            return None

        return best_one["next_I"] 

    def next_intersection_to_target_car(self, car_id: int):
        return self.next_intersection_to_target_segment(self.__city.cars[car_id].segment)

    def nearest_uav_near_intersection(self, intersection_id: int):
        min_distance = float("inf")
        min_dist_uav_id = None

        for uav_id, uav in self.__city.uavs.items():
            uav_real_coord_x = uav.coord[0] * self.segment_len / 2
            uav_real_coord_y = uav.coord[1] * self.segment_len / 2

            intersection_real_coord = self.__city._real_coord_of_joint(intersection_id)

            dist = square_distance(uav_real_coord_x, uav_real_coord_y, self.real_coord[0], self.real_coord[1]) + square_distance(uav_real_coord_x, uav_real_coord_y, intersection_real_coord[0], intersection_real_coord[1])

            if dist < min_distance:
                min_distance = dist
                min_dist_uav_id = uav_id

        return (min_dist_uav_id, min_distance)

    @property
    def plot_coord(self):
        car_coord = self.car_coord[:]

        if self.car_direction_positive:
            _step = 0.2
        else:
            _step = -0.2

        if self.car_direction_horizontal:
            car_coord[1] += _step
        else:
            car_coord[0] += _step

        return car_coord

    def update_contacts(self, cars: list):
        self.cars_in_contact = cars

    def real_distance_to(self, car):
        return ((self.real_coord[0] - car.real_coord[0])**2 + (self.real_coord[1] - car.real_coord[1])**2)**.5

    def update(self, next_segment, next_segment_point, new_segment_len, new_direction_positive, new_direction_horizontal, new_car_coord, new_segment_end_coord):
        self.segment = next_segment
        self.segment_loc = next_segment_point
        self.segment_len = new_segment_len
        self.car_direction_positive = new_direction_positive
        self.car_direction_horizontal = new_direction_horizontal
        self.car_coord = new_car_coord
        self.segment_end_coord = new_segment_end_coord

        self.real_coord = [self.car_coord[0] * self.segment_len / 2, self.car_coord[1] * self.segment_len / 2]

        self.reached_segment_end = False

        if self.segment_loc >= self.segment_len:
            self.reached_segment_end = True

    def simulation_step(self):
        if not self.reached_segment_end:
            self.segment_loc += self.car_velocity

            if self.segment_loc >= self.segment_len:
                self.reached_segment_end = True
                self.car_coord = self.segment_end_coord
                self.real_coord = [self.car_coord[0] * self.segment_len / 2, self.car_coord[1] * self.segment_len / 2]
            else:
                if self.car_direction_positive:
                    _step = 2 * self.car_velocity / self.segment_len
                else:
                    _step = -2 * self.car_velocity / self.segment_len
                
                if self.car_direction_horizontal:
                    self.car_coord[0] += _step
                else:
                    self.car_coord[1] += _step

                self.real_coord = [self.car_coord[0] * self.segment_len / 2, self.car_coord[1] * self.segment_len / 2]