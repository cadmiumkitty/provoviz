#!/usr/bin/env python

from SPARQLWrapper import SPARQLWrapper, JSON
from flask import render_template
import re
from urllib import unquote_plus
import networkx as nx
from networkx.readwrite import json_graph
import json
from rdflib import Graph, Namespace, RDF, RDFS, Literal, URIRef
from rdflib.serializer import Serializer
import rdfextras
from math import log
import time
from app import app, socketio
import pprint





concept_type_color_dict = {'popg': '#9edae5', 'inpo': '#ffbb78', 'elii': '#dbdb8d', 'idcn': '#9edae5', 'neop': '#2ca02c', 'vita': '#9467bd', 'inpr': '#c5b0d5', 'phsu': '#c5b0d5', 'blor': '#98df8a', 'hops': '#c7c7c7', 'menp': '#f7b6d2', 'phsf': '#d62728', 'ftcn': '#e377c2', 'anim': '#ff9896', 'food': '#bcbd22', 'grpa': '#ffbb78', 'geoa': '#2ca02c', 'hcpp': '#98df8a', 'lbtr': '#c7c7c7', 'ocdi': '#17becf', 'tisu': '#17becf', 'orch': '#7f7f7f', 'tmco': '#dbdb8d', 'clas': '#bcbd22', 'lipd': '#c49c94', 'dsyn': '#f7b6d2', 'horm': '#aec7e8', 'bact': '#2ca02c', 'grup': '#e377c2', 'bacs': '#ffbb78', 'enty': '#c5b0d5', 'resa': '#98df8a', 'medd': '#9467bd', 'cell': '#bcbd22', 'fndg': '#ff7f0e', 'sbst': '#ff9896', 'prog': '#ff9896', 'celf': '#aec7e8', 'chvf': '#1f77b4', 'diap': '#aec7e8', 'celc': '#8c564b', 'hcro': '#ff7f0e', 'inbe': '#9467bd', 'clna': '#ffbb78', 'acab': '#d62728', 'bodm': '#9467bd', 'patf': '#e377c2', 'carb': '#c7c7c7', 'bpoc': '#d62728', 'dora': '#8c564b', 'moft': '#7f7f7f', 'plnt': '#7f7f7f', 'ortf': '#f7b6d2', 'bmod': '#9edae5', 'sosy': '#dbdb8d', 'enzy': '#d62728', 'qnco': '#1f77b4', 'imft': '#7f7f7f', 'antb': '#1f77b4', 'bdsy': '#c5b0d5', 'nnon': '#9467bd', 'socb': '#c49c94', 'ocac': '#8c564b', 'bdsu': '#8c564b', 'rcpt': '#ff9896', 'nsba': '#c5b0d5', 'mnob': '#e377c2', 'orga': '#1f77b4', 'orgf': '#c7c7c7', 'lbpr': '#d62728', 'orgt': '#aec7e8', 'gngm': '#f7b6d2', 'virs': '#17becf', 'fngs': '#98df8a', 'aapp': '#17becf', 'opco': '#c49c94', 'irda': '#98df8a', 'famg': '#2ca02c', 'acty': '#ff7f0e', 'inch': '#bcbd22', 'cnce': '#9edae5', 'topp': '#ffbb78', 'spco': '#2ca02c', 'lang': '#dbdb8d', 'podg': '#aec7e8', 'mobd': '#ff9896', 'qlco': '#c49c94', 'npop': '#ff7f0e', 'hlca': '#1f77b4', 'phpr': '#ff7f0e', 'strd': '#8c564b'}


def uri_to_label(uri):
    if '#' in uri:
        (base,hash_sign,local_name) = uri.rpartition('#')
        base_uri = local_name.encode('utf-8')
    else :
        base_uri = re.sub("http://.*?/","",uri.encode('utf-8'))
        
    
    return shorten(unquote_plus(base_uri).replace('_',' ').lstrip('-').lstrip(' '))
    
def shorten(text):
    if len(text)>32:
        return text[:15] + "..." + text[-15:]
    else :
        return text


def get_activities(store, graph_uri=None):
    emit('Retrieving activities...')
    q = render_template('activities.q', graph_uri=graph_uri)
    
    results = store.query(q)
    
    activities = []
    activity_uris = set()
    
    for result in results:
        activity_uri = result['activity']
        
        if activity_uri in activity_uris:
            continue
        else :
            activity_uris.add(activity_uri)
        
        emit('{}...'.format(activity_uri))
        
        try:
            
            activity_label = result['label']
            app.logger.debug("Found label {} in result".format(result['label']))
        except :
            app.logger.debug("No label for {}".format(activity_uri))
            activity_label = uri_to_label(activity_uri)
        
        emit("Found activity {}".format(activity_label))
         
        activities.append({'id': activity_uri, 'text': activity_label})
        
    return activities


def get_named_graphs(store):
    emit('Retrieving graphs...')
    q = render_template('named_graphs.q')

    results = store.query(q)

    graphs = []
    
    for result in results:
        graph_uri = result['graph']
        emit('{}...'.format(graph_uri))
        
        emit("Found graph {}".format(graph_uri))
        
        graphs.append({'uri': graph_uri, 'id': graph_uri, 'text': graph_uri})
        
    return graphs    
    








def build_graph(G, store, name=None, source=None, target=None, query=None, intermediate = None):
    emit('Building edges from {} to {}'.format(source, target))
    
    
    app.logger.debug(u"Query:\n{}".format(query))
    
    results = store.query(query)

    for result in results:
        app.logger.debug(u"Result:\n{}".format(result))
        
        if not intermediate :
            app.logger.debug("No intermediate node")
            
            if name and not source:
                source_binding = uri_to_label(name).replace("'","");
                source_uri = name
            elif not source :
                source_binding = "example"
                source_uri = "http://prov.data2semantics.org/resource/example"
            else :
                try :
                    source_binding = shorten(result[source+"_label"])
                    app.logger.debug("{}_label in result".format(source))
                except :
                    app.logger.debug("No {}_label in result!!".format(source))
                    source_binding = uri_to_label(result[source]).replace("'","")
            
            source_uri = result[source]
                
            try :
                target_binding = shorten(result[target+"_label"])
                app.logger.debug("{}_label in result".format(target))
            except :
                app.logger.debug("No {}_label in result!!".format(target))
                target_binding = uri_to_label(result[target]).replace("'","")
                app.logger.debug("Set to {}".format(target_binding))
            
            
            try  :
                source_type = result[source+"_type"]
                app.logger.debug("{}_type in result".format(source))
            except :
                source_type = re.sub('\d+$','',source)
                app.logger.debug("No {}_type in result!!".format(source))
            
            try :
                target_type = result[target+"_type"]
                app.logger.debug("{}_type in result".format(target))
            except:
                target_type = re.sub('\d+$','',target)
                app.logger.debug("No {}_type in result!!".format(target))
                
            target_uri = result[target]
            
            
            G.add_node(source_uri, label=source_binding, type=source_type, uri=source_uri)
            G.add_node(target_uri, label=target_binding, type=target_type, uri=result[target])
            G.add_edge(source_uri, target_uri, value=10)
            
            
            

        else :
            
            try :
                source_binding = shorten(result[source+"_label"])
            except :
                source_binding = uri_to_label(result[source]).replace("'","")
                
            try :
                intermediate_binding = shorten(result[intermediate+"_label"])
            except :
                intermediate_binding = uri_to_label(result[intermediate]).replace("'","")
                
            try :
                target_binding = shorten(result[target+"_label"])
            except :
                target_binding = uri_to_label(result[target]).replace("'","")
            
            G.add_node(result[source], label=source_binding, type=re.sub('\d+$','',source), uri=result[source])
            G.add_node(result[intermediate], label=intermediate_binding, type=re.sub('\d+$','',intermediate), uri=result[intermediate])
            G.add_node(result[target], label=target_binding, type=re.sub('\d+$','',target), uri=result[target])
            
            G.add_edge(result[source], result[intermediate], value=10)
            G.add_edge(result[intermediate], result[target], value=10)

    app.logger.debug('Query-based graph building complete...')
    emit('Query-based graph building complete...')


    return G


def build_full_graph(store, graph_uri=None):
    app.logger.debug(u"Building full graph")
    emit("Building full provenance graph...")
    
    G = nx.DiGraph()
    
    q_activity_to_resource = render_template('activity_to_resource.q', graph_uri=graph_uri)
    app.logger.debug("Running activity_to_resource")
    emit("Running activity_to_resource")
    G = build_graph(G, store, source="activity", target="entity", query=q_activity_to_resource)
    
    q_resource_to_activity = render_template('resource_to_activity.q', graph_uri=graph_uri)
    app.logger.debug("Running resource to activity")
    emit("Running activity_to_resource")
    G = build_graph(G, store, source="entity", target="activity", query=q_resource_to_activity)
    
    q_derived_from = render_template('derived_from.q', graph_uri = graph_uri)
    app.logger.debug("Running derived from")
    emit("Running derived from")
    G = build_graph(G, store, source="entity1", target="entity2", query=q_derived_from)
    
    q_informed_by = render_template('informed_by.q', graph_uri = graph_uri)
    app.logger.debug("Running informed by")
    emit("Running informed by")
    G = build_graph(G, store, source="activity1", target="activity2", query=q_informed_by)
 

    
    emit("Building full provenance graph complete...")



    return G
    
    
def extract_ego_graph(G, activity_uri):
    sG = None
    inG = None
    outG = None
    
    app.logger.debug(u"Extracting ego graph (forward) {}".format(activity_uri))
    outG = nx.ego_graph(G,activity_uri,50)
    app.logger.debug(u"Extracting ego graph (backward) {}".format(activity_uri))
    inG = nx.ego_graph(G.reverse(),activity_uri,50)
    app.logger.debug(u"Reversing backward ego graph {}".format(activity_uri))
    inG = inG.reverse()
    app.logger.debug(u"Joining ego graphs {}".format(activity_uri))
    sG = nx.compose(outG,inG)
    
    return sG

def extract_activity_graph(G, activity_uri, activity_id):
    emit(u"Extracting ego graph for {}".format(activity_id))
    app.logger.debug(u"Extracting graph for {} ({})".format(activity_uri, activity_id))
    
    try:
        sG = extract_ego_graph(G, activity_uri)
    except:
        emit(u"Could not extract ego graph for {} (Bug in NetworkX?)".format(activity_id))
        app.logger(u"Could not extract ego graph for {} (Bug in NetworkX?)".format(activity_id))
        return
        
        
    app.logger.debug("Original graph: {} nodes\nEgo graph: {} nodes".format(len(G.nodes()),len(sG.nodes())))

    # Set node type for the activity_uri to 'origin'
    sG.node[activity_uri]['type'] = 'origin'
    
    app.logger.debug(u"Assigning weights to edges")
    emit("Assigning weights to edges")
    
    # Get start and end nodes (those without incoming or outgoing edges, respectively)
    start_nodes = [ n for n in sG.nodes() if sG.in_degree(n) == 0 ]
    end_nodes = [ n for n in sG.nodes() if sG.out_degree(n) == 0 ]
    
    edge_weights = {}
    try:
        # Walk all edges, and assign weights
        edge_weights = walk_weights(graph = sG, pending_nodes = start_nodes, edge_weights = {}, visited = [])
    except Exception as e:
        emit("ERROR: Provenance trace contains cycles: {}".format(e.message))
        raise e
    
    # Check to make sure that the edge weights dictionary has the same number of keys as edges in the ego graph
    app.logger.debug("Check {}/{}".format(len(edge_weights.keys()),len(sG.edges())))
    nx.set_edge_attributes(sG,'value',edge_weights)
    del(edge_weights)
    # nx.set_node_attributes(sG,'value',node_weights)

    
    
    # Convert to JSON
    g_json = json_graph.node_link_data(sG) # node-link format to serialize

    # Get number of start and end nodes to determine ideal width of the viewport
    start_nodes = len(start_nodes)
    end_nodes = len(end_nodes)
    max_degree = 1
    for n,d in sG.nodes(data=True):
        if sG.in_degree(n) > max_degree :
            max_degree = sG.in_degree(n)
        if sG.out_degree(n) > max_degree :
            max_degree = sG.out_degree(n)
            
    # Set width to the largest of # end nodes, # start nodes, or the maximum degree
    width = max([end_nodes,start_nodes,max_degree])      

    app.logger.debug(u"Computing graph diameter {} ({})".format(activity_uri, activity_id))
    try:
        diameter = nx.diameter(sG.to_undirected())
    except Exception:
        app.logger.warning("Could not determine diameter, setting to arbitrary value of 25")
        emit("Could not determine diameter, setting to arbitrary value of 25")
        diameter = 25
    
    types = len(set(nx.get_node_attributes(sG,'type').values()))
    
    if types > 11:
        types = 11
    elif types < 3 :
        types = 3
    
    app.logger.debug(u"Done extracting graph for {} ({})".format(activity_uri, activity_id))
    return g_json, width, types, diameter


def walk_weights(graph, pending_nodes = [], edge_weights = {}, visited = []):
    # If we have no more nodes in the queue, return the computed edge weights
    app.logger.debug(pending_nodes)
    if pending_nodes == []:
        return edge_weights
        
    next_nodes = []
    for n in pending_nodes:
        # If a node has already been visited, just ignore it
        if n in visited:
            app.logger.debug("Already visited {}".format(n))
            continue
            
        # If the node does not have any incoming edges, 
        # set the edge weight of each outgoing edge to log(10) (why? search me! Looks nice)
        if graph.in_degree(n) == 0:
            out_edges = graph.out_edges([n])
            for (u,v) in out_edges:
                edge_weights[(u,v)] = log(10)
                next_nodes.append(v)
                
            # We can safely add the node to the visited list.
            visited.append(n)
            
        # Otherwise, the node *does* have outgoing edges
        else:
            # Get all incoming edges
            in_edges = graph.in_edges([n])
            
            # Make sure that all incoming edges already have a weight
            incomplete = [e for e in in_edges if e not in edge_weights.keys()]
            
            # If some of them don't, we add the current node to the end of the queue and stop treating it.
            # This is because we need all edge weights before we can redistribute the weight to the outgoing edges
            if incomplete != [] :
                app.logger.debug("Node `{}` has unvisited incoming edges, adding to end of queue".format(n))
                next_nodes.append(n)
                continue
            
            # Otherwise, we'll just calculate the accumulated weight of all incoming edges
            accumulated_weight = sum([edge_weights[e] for e in in_edges])
            
            # Get the outgoing edges of the current node
            out_edges = graph.out_edges([n])
            
            # Get the out degree of the current node (actually just len(out_edges))
            out_degree = graph.out_degree(n)
                
            
            # And then we divide the accumulated weight by the out degree, 
            # assign it to each outgoing edge, and
            # add the target node to the next_nodes queue
            for (u,v) in out_edges:
                edge_weights[(u,v)] = accumulated_weight/out_degree
                next_nodes.append(v)
                
            # Only append node to visited if it is not in next_nodes
            visited.append(n)

    # Once we have visited all nodes, we call walk_weights recursively with the next_nodes list
    return walk_weights(graph, next_nodes, edge_weights, visited)
    

def emit(message):
    socketio.emit('message',
                  {'data': message },
                  namespace='/log')



        
    
    
    

