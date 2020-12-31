import random
#import numpy as np
import networkx as nx
import matplotlib.pyplot as plt

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
        nx.draw(self.G, self._G_pos, with_labels=True, connectionstyle='arc3, rad = 0.1', node_size=1000, font_size=20)
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