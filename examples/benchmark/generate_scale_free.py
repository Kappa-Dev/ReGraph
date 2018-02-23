import networkx as nx
import numpy as np

import pickle


# start at 44212
if __name__ == '__main__':
    # Generate graphs (Warning: takes some time, see below dumped graphs) + TODO: investigate more parameters
    scale_free_ns = [int(i) for i in np.logspace(5, 17, 200, base=2)]

    # logspaced_scale_free = []
    for n in scale_free_ns[173:]:
        print("Generating ", n)
        g = nx.scale_free_graph(n)
    #     logspaced_scale_free.append(g)
        with open("benchmark/scale_free/5_17_200_{}.pickle".format(n), "wb") as f:
            pickle.dump(g, f)