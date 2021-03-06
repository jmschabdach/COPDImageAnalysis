import sys
import os
import numpy as np

# handling different types of data
import pandas as pd
import pickle as pk
import shelve
import h5py
from joblib import Parallel, delayed  # conda install -c anaconda joblib=0.9.4
from cyflann import *


def loadPickledData(useHarilick=False):     
    # pickleFn =  '%(pickleRootFolder)s/%(pickleSettingName)s/%(pickleSettingName)s.data.p'%\
        # {'pickleSettingName':pickleSettingName, 'pickleRootFolder':pickleRootFolder}
    # pickleFn =  '/pylon1/ms4s88p/jms565/COPDGene_pickleFiles/histFHOG_largeRange_setting1.data.p'
    # shelveFn = '/pylon1/ms4s88p/jms565/COPDGene_pickleFiles/histFHOG_largeRange_setting1.shelve'

    # desktop or laptop or home
    pickleFn = "COPDGene_pickleFiles/histFHOG_largeRange_setting1.data.p"
    shelveFn = 'COPDGene_pickleFiles/histFHOG_largeRange_setting1.shelve'
    print "pickleFn : ", pickleFn
    print "shelveFn :", shelveFn
    
    # reading pickle and shelve files
    print "Reading the shelve file ..."
    fid = shelve.open(shelveFn,'r')
    metaVoxelDict = fid['metaVoxelDict']
    subjList = fid['subjList']
    phenotypeDB_clean = fid['phenotypeDB_clean']
    fid.close()
    print "Done !"
    print "Sample of the metadata: "
    print "IDs of a few subjects : " , metaVoxelDict[0]['id']
    print "labelIndex of the meta data (a few elements): " , metaVoxelDict[0]['labelIndex'][1:10]   
    print "Reading pickle file ...."
    fid = open(pickleFn,'rb')
    data = pk.load(open(pickleFn,'rb'))
    fid.close()
    print "Done !"
    return metaVoxelDict,subjList, phenotypeDB_clean, data

# see data_looking.ipynb for structure information

# READ/PLAY WITH DATA FIRST

# for each subject, create an approximate NN graph using pyflann (cyflann)
#  *http://www.cs.ubc.ca/research/flann/
#  * install it using pip or conda
#  https://github.com/primetang/pyflann
#  https://github.com/dougalsutherland/cyflann

def buildSubjectGraphs(subjects, data, neighbors=5):
    """
    Find the numNodes nodes of each subject that are closest to N nodes
    in every other subject.

    Inputs:
    - subjects: included for size (hackish programming)
    - data: collection of data to be graph'ed
    - neighbors: the number of nearest nodes to save

    Returns:
    - subjDBs: list of lists of dictionaries of lists
        - first layer = first subject
        - second layer = second subject
        - third layer = dictionary accessed by keys
        - "nodes": list of 

    """
    flann = FLANNIndex()
    subjDBs = []
    # build the graph for each subject
    print "Now building subject-subject mini databases..."
    # for i in xrange(len(subjects)-1):
    for i in xrange(1):  # for testing only
        results = []
        flann.build_index(data[i]['I'])
        # for j in xrange(len(subjects[i+1:])):
        for j in xrange(len(subjects)):  # for testing only
            # nodes, dists = flann.nn(data[i]['I'], data[j]['I'], neighbors, algorithm='kmeans')
            nodes, dists = flann.nn_index(data[j]['I'], neighbors, algorithm='kmeans')
            # save the numNodes number of distances and nodes
            temp = {
                "nodes": nodes,
                "dists": dists
            }
            results.append(temp)
        subjDBs.append(results)
    print "Subject level databases complete!"
    # print subjDBs
    return subjDBs

#---------------------------------------------------------------------------------
# Attempt at Parallelization, v2
#---------------------------------------------------------------------------------

def buildSubjectGraphsParallel(data, jobs, neighbors=5):
    """
    Find the numNodes nodes of each subject that are closest to N nodes
    in every other subject.

    Inputs:
    - subjects: included for size (hackish programming)
    - data: collection of data to be graph'ed
    - jobs: number of jobs to run
    - neighbors: the number of nearest nodes to save

    Returns:
    - subjGraphs: list of lists of dictionaries of lists
        - first layer = first subject
        - second layer = second subject
        - third layer = dictionary accessed by keys
        - "nodes": list of 

    """
    subjGraphs = []
    # build the graph for each subject
    print "Now building subject-subject mini databases..."
    subjGraphs=Parallel(n_jobs=jobs, backend='threading')(
        delayed(buildSubjectGraph)(i, data, neighbors) for i in xrange(3)) # len(data[0])))
    print "Subject level databases complete!"
    # print subjDBs
    return subjGraphs

def buildSubjectGraph(subj, data, neighbors=5):
    """
    Find the numNodes nodes of each subject that are closest to N nodes
    in every other subject.

    Inputs:
    - subj: index of the subject being database'd
    - data: collection of data to be graph'ed
    - neighbors: the number of nearest nodes to save

    Returns:
    - subjDBs: list of lists of dictionaries of lists
        - first layer = first subject
        - second layer = second subject
        - third layer = dictionary accessed by keys
        - "nodes": list of N nearest nodes
        - "dists": list of dists for N nearest nodes
    """
    flann = FLANNIndex()
    subjDB = []
    # vectorize data
    rowLengths = [ s['I'].shape[0] for s in data ]
    X = np.vstack( [ s['I'] for s in data] )
    # build the graph for a subject
    print "Now building subject-subject mini databases..."
    flann.build_index(data[subj]['I'])
    nodes, dists = flann.nn_index(X, neighbors)
    # decode the results
    idx = 0
    for i in rowLengths:
        # save the numNodes number of distances and nodes
        temp = {
            "nodes": nodes[idx:idx+i],
            "dists": dists[idx:idx+i]
        }
        idx = idx + i
        subjDB.append(temp)
    print "Subject level databases complete!"
    return subjDB

#--------------------------------------------------------------------------------
# Save and load database data
#--------------------------------------------------------------------------------

def saveSubjectGraphs(graphs, fn):
    """
    Save the subject graphs in an HDF5 file.

    Inputs:
    - graphs: subject graphs
    - fn: filename to save to

    Returns:
    nothing
    """
    print "Saving subject graphs to HDF5 file..."
    # print "len(graphs): " + str(len(graphs))
    fn = fn + ".h5"
    with h5py.File(fn, 'w') as hf:
        # metadata storage
        # print "dimensions of the table: " + str(len(graphs))
        hf.create_dataset("metadata", [len(graphs)], compression='gzip', compression_opts=7)
        for j in xrange(len(graphs)):
            # print "    current j: " + str(j)
            dsName = str(j).zfill(4)
            g = hf.create_group(dsName)
            g.create_dataset("nodes", data=graphs[j]['nodes'], compression='gzip', compression_opts=7)
            g.create_dataset("dists", data=graphs[j]['dists'], compression='gzip', compression_opts=7)
    print "Subject graph file saved!"


def loadSubjectGraph(fn):
    """
    Load the subject graphs from an HDF5 file.

    Inputs:
    - fn: filename to load from 

    Returns:
    - graphs: loaded subject graphs
    """
    print "Loading the subject graph..."
    fn = fn + ".h5"
    with h5py.File(fn, 'r') as hf:
        # print("List of arrays in this file: \n" + str(hf.keys()))
        metadata = hf.get('metadata').shape
        print metadata
        graph = []
        for j in xrange(metadata[0]):
            # get the name of the group
            dsName = str(j).zfill(4)
            # extract the group and the items from the groups
            g = hf.get(dsName)
            nodes = g.get("nodes")
            dists = g.get("dists")
            # put the items into the data structure
            temp = {
                "nodes": np.array(nodes),
                "dists": np.array(dists)
            }
            graph.append(temp)
    print "Graph loaded!"
    return graph

# digression : http://www.theverge.com/google-deepmind

#------------ NEXT STEP (WARNING: TAKE IT WITH HUGE GRAIN OF SALT)
#  I installed this package : https://github.com/dougalsutherland/skl-groups
# obs_knnObj_Kayhan = knnDiv.indices_[0]   # knn object for the observed data which is the first element in the list
# knnDiv_Kayhan.features_.make_stacked()
# X_feats_Jenna = knnDiv.features_.stacked_features
# obs_knnIdx = obs_knnObj_Kayhan.nn_index(X_feats_Jenna, 3)[0][:,2]
# obs_knnDist = obs_knnObj.nn_index(X_feats_Jenna, 3)[1][:,2]

# # interpretation
# # isolate a subject graph
# knnObj1 = subjGraphs[0]['results']
# # get its features
# knnObj1.featureus_.make_stacked()
# # collect features of all other graphs
# allSubjFeatures = subjGraphs.features_.stacked_features
# # not sure what this is
# indices = knnObj1.nn_index(allSubjFeatures, 3)[0][:, 2]
# distances = subjGraphs.nn_index(allSubjFeatures, 3)[1][:, 2]


# -------------------------------
# WE WILL BUILD SPARSE MATRIX representing the connectivity between nodes


# -----------------------
# We will try igraph to detect communities:
# http://igraph.org/redirect.html

# def main():
    # Main function
metaVoxelDict, subjList, phenotypeDB_clean, data = loadPickledData()
neighbors = 5
jobs = 2
subjGraphs = buildSubjectGraphsParallel(data, jobs, neighbors)
fn = "subjGraphs"
saveSubjectGraphs(subjGraphs, fn)
data2 = loadSubjectGraphs(fn)

# if __name__ == '__main__':
#     main()