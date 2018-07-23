# Imports for I/O processing

import json
import geopandas as gp
from networkx.readwrite import json_graph
import functools


# Imports for RunDMCMC components
# You can look at the list of available functions in each
# corresponding .py file.

from rundmcmc.accept import always_accept

from rundmcmc.chain import MarkovChain

from rundmcmc.make_graph import (add_data_to_graph, construct_graph)

from rundmcmc.partition import Partition

from rundmcmc.proposals import propose_random_flip_no_loops

from rundmcmc.updaters import (Tally, boundary_nodes, cut_edges,
                               cut_edges_by_part, exterior_boundaries,
                               perimeters, polsby_popper,
                               votes_updaters,
                               interior_boundaries)

from rundmcmc.validity import (L1_reciprocal_polsby_popper,
                               UpperBound,
                               Validator, no_vanishing_districts,
                               no_worse_L_minus_1_polsby_popper,
                               single_flip_contiguous,
                               within_percent_of_ideal_population)

from rundmcmc.scores import (efficiency_gap, mean_median,
                             mean_thirdian)

from rundmcmc.output import p_value_report, pipe_to_table, ChainOutputTable

from rundmcmc.output.vis_output import (hist_of_table_scores, trace_of_table_scores)

from graphmaker.graph import Graph

# Input the path to the graph (either JSON or shapefile) and the label column
# graph_path = "./testData/PA_graph_with_data.json"
# unique_label = "wes_id"

graph = Graph.load('C:/dev/gerrydb/pennsylvania/PA_rook.json').graph

# Names of graph columns go here
pop_col = "population"
area_col = "area"
district_col = "2011"


# This builds a graph
# graph = construct_graph(graph_path, "json")

# Write graph to file
# with open('graph_with_data.json', 'w') as outfile1:
# outfile1.write(json.dumps(json_graph.node_link_data(graph)))

# Put district on graph
assignment = dict(zip(graph.nodes(), [graph.node[x][district_col] for x in graph.nodes()]))


# Input the shapefile with vote data here
# vote_path = "./testData/wes_merged_data.shp"


# This inputs a shapefile with columns you want to add
# df = gp.read_file(vote_path)


# Names of shapefile data columns go here
vote_col1 = "T16SEND"
vote_col2 = "T16SENR"

# This adds the data to the graph
# data_list = [vote_col1, vote_col2]

# add_data_to_graph(df, graph, data_list, id_col=unique_label)


# Desired proposal method
proposal_method = propose_random_flip_no_loops


# Desired proposal method
acceptance_method = always_accept


# Number of steps to run
steps = 20000

print("loaded data")


# Necessary updaters go here
updaters = {
            **votes_updaters([vote_col1, vote_col2]),
            'population': Tally(pop_col, alias='population'),
            'perimeters': perimeters,
            'exterior_boundaries': exterior_boundaries,
            'interior_boundaries': interior_boundaries,
            'boundary_nodes': boundary_nodes,
            'cut_edges': cut_edges,
            'areas': Tally(area_col, alias='areas'),
            'polsby_popper': polsby_popper,
            'cut_edges_by_part': cut_edges_by_part}

# This builds the partition object
initial_partition = Partition(graph, assignment, updaters)


# Desired validators go here
pop_limit = .01
population_constraint = within_percent_of_ideal_population(initial_partition, pop_limit)

# compactness_limit = L1_reciprocal_polsby_popper(initial_partition)
# compactness_constraint = UpperBound(L1_reciprocal_polsby_popper, compactness_limit)
compactness_constraint = no_worse_L_minus_1_polsby_popper

validator = Validator([no_vanishing_districts,
                       single_flip_contiguous, population_constraint,
                       compactness_constraint])

# Add cyclic updaters :(
# updaters['metagraph_degree'] = MetagraphDegree(validator, "metagraph_degree")

# This builds the partition object (again) :(
# initial_partition = Partition(graph, assignment, updaters)

print("setup chain")

# This builds the chain object for us to iterate over
chain = MarkovChain(proposal_method, validator, acceptance_method,
                  initial_partition, total_steps=steps)

# Post processing commands go below:

scores = {
        'Mean-Median': functools.partial(mean_median, proportion_column_name=vote_col1 + "%"),
        'Mean-Thirdian': functools.partial(mean_thirdian, proportion_column_name=vote_col1 + "%"),
        'Efficiency Gap': functools.partial(efficiency_gap, col1=vote_col1, col2=vote_col2),
        'L1 Reciprocal Polsby-Popper': L1_reciprocal_polsby_popper}

initial_scores = {key: score(initial_partition) for key, score in scores.items()}

# table = pipe_to_table(chain, scores, display=True, number_to_display=100)

naive_p_value_report = []
original_score = initial_scores['Efficiency Gap']

table = ChainOutputTable()

counter = 0
for state in chain:
    higher = efficiency_gap(state, 'T16SEND', 'T16SENR') >= original_score
    naive_p_value_report.append(higher)

    row = {key: score(state) for key, score in scores.items()}

    table.append(row)

    if counter % 100 == 0:
        higher_in_last_100 = len([x for x in naive_p_value_report[-100:] if x == True])
        print(f"{higher_in_last_100} higher in last 100 steps")

    counter += 1


print(len([x for x in naive_p_value_report if x]), len(chain))
print(len([x for x in table['Efficiency Gap'] if x >= original_score]), len(chain))

print("ran chain")

# Histogram Plotting
hist_path = "chain_histogram31.png"

hist_of_table_scores(table, scores, outputFile=hist_path, num_bins=50)

print("plotted histograms")


# Trace Plotting
trace_path = "chain_traces31.png"

trace_of_table_scores(table, scores, outputFile=trace_path)

print("plotted traces")

# P-value reports
pv_dict = {key: p_value_report(key, table[key], initial_scores[key]) for key in scores}
print(pv_dict)
with open('pvals_report31.json', 'w') as fp:
    json.dump(pv_dict, fp)

print("computed p-values")


# Write flips to file

# allAssignments = {0: chain.state.assignment}

# for step in chain:
#     allAssignments[chain.counter + 1] = [step.flips]

# with open("chain_flips31.json", "w") as fp:
#     json.dump(allAssignments, fp)

# print("wrote flips")