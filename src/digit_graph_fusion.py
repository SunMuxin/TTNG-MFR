import copy
import build_cknn_graphs
import evaluate
import re
import time
from Queue import PriorityQueue

class TTNG_MFR:
    
    ########### Step 1: find the weighted ###########
    def Fusion_Weighted(self, graph_list, num_ranks, kNN, retri_amount):
        # merge all graphs
        initial_graph = copy.deepcopy(graph_list[0])
        for i in range(1, num_ranks):
            cur_graph = graph_list[i]
            cur_keys = cur_graph.keys()
            initial_keys = initial_graph.keys()
            for j in cur_keys:
                if j not in initial_keys:
                    initial_graph[j] = cur_graph[j]
                else:
                    nodes = cur_graph[j]
                    for k in nodes:
                        initial_graph[j].append(k)

        # compute the sum of weights for each vertex
        all_keys = initial_graph.keys()
        weight_sum = {}
        for cur_key in all_keys:
            if cur_key == -1:
                continue
            cur_weights = initial_graph[cur_key]
            for weight in cur_weights:
                if cur_key not in weight_sum.keys():
                    weight_sum[cur_key] = weight[1]
                else:
                    weight_sum[cur_key] += weight[1]
        selected_images = [];
        for vertex in sorted(weight_sum, key=weight_sum.get, reverse=True):
            selected_images.append(vertex)
        if len(selected_images) < retri_amount:
            voc_candidate = graph_list[0] # 0: hsv or 1000d. 1: voc
            voc_candidate = voc_candidate[-1]
            for i in voc_candidate:
                if i not in selected_images:
                    selected_images.append(i)
                    weight_sum[i] = 0
        weight_sum[-1] = 0
        for i in selected_images[1:kNN]:
            weight_sum[-1] = weight_sum[-1] + weight_sum[i]
        return weight_sum, selected_images
    
    ########### Step 2: find the maximum expectation rank ###########
    def Expectation_Rank(self, vectexS, graphs, fn_fusion_result, kNN, retri_amount, weights):
        fd_stdin_fusion = open(fn_fusion_result, 'w')
        rerank_result = {}
        for node in vectexS:
            rank = []
            weight_sum = {}
            weight_sum[node] = 0
            while len(rank) < retri_amount+2:
                for vertex in sorted(weight_sum, key=weight_sum.get, reverse=True):
                    if vertex not in rank:
                        rank.append(vertex)
                        del weight_sum[vertex]
                        for v in graphs[vertex]:
                            if v in rank:
                                continue
                            if v not in weight_sum:
                                weight_sum[v] = 0
                            weight_sum[v] += weights[vertex][v]
                            if vertex in graphs[v]:
                                weight_sum[v] += weights[v][vertex]
                        break
            rerank_result[node] = rank
                
        for i in range(len(vectexS)):
            selected_images = rerank_result[i]
            selected_images = selected_images[0: retri_amount];
            fd_stdin_fusion.write(str(i) + '.jpg ')
            for img_id in selected_images:
                fd_stdin_fusion.write(str(img_id) + ' ')
            fd_stdin_fusion.write('\n')
            graph_list = [] 
        fd_stdin_fusion.close()
                
#########################################################
    
if __name__ == "__main__":


    fn_fusion_result = 'data/digit_graph_fusion_results.txt'
    fn_label = 'data/digit_list_data_labels.txt'
    
    graphfusion = TTNG_MFR()
    
    fn_results = []
    fn_results.append('data/digit_rank_fourier.txt')
    fn_results.append('data/digit_rank_pixel.txt')
    
    fn_result_rerankings = []
    fn_result_rerankings.append('data/digit_rerank_fourier.txt')
    fn_result_rerankings.append('data/digit_rerank_pixel.txt')

    num_ranks = len(fn_results) # in this case, just 2 types of ranks, i.e., voc and hsv
    retri_amount = 20
    kNN = 20
    
    graph_list = []
    weights = []
    graphs = []
    result_length = 2000
    graph_lists = []
    vectexS = []   
    
    print '######################  Graph Build Step  ##########################'
    T = time.time()
    for line in range(result_length):
        graphs.append([]);
        weights.append({});
    for i in range(num_ranks):
        fn_result = fn_results[i]
        fn_result_reranking = fn_result_rerankings[i]
        search_region = 10
        lam = 1
        graph_lists.append(build_cknn_graphs.BuildKNNGraphs(fn_result, fn_result_reranking, fn_label, 25, 150, search_region, lam))
    print 'Graph Build Step; Total Time is ', time.time() - T, 's'
    
    print '######################  Graph Fusion Step  ##########################'
    T = time.time()
    for i in range(result_length):
        graph_list = [] 
        for j in range(num_ranks):
            graph_list.append(graph_lists[j][i])
            
        graph_list_copy = copy.deepcopy(graph_list)
        weight, graph = graphfusion.Fusion_Weighted(graph_list_copy, num_ranks, kNN, retri_amount)
        weights[graph[0]] = weight
        graphs[graph[0]] = graph
        vectexS.append(graph[0])
    
    print 'Graph Fusion Step; Total Time is ', time.time() - T, 's'
    
    print '######################  Re-Rank Step  ##########################'
    T = time.time()
    graphfusion.Expectation_Rank(vectexS, graphs, fn_fusion_result, kNN, retri_amount, weights)
    print 'Re-Rank Step; Each retrieval image time is ', (time.time() - T)/result_length*1000/retri_amount, 'ms'
    
    print "After graphs fusion:"
    evaluate.Evaluate(fn_label, fn_fusion_result, 20)
    

    

