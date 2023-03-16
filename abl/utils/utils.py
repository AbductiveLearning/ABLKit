import numpy as np
from .plog import INFO
from collections import OrderedDict
from itertools import chain

def flatten(l):
    if not isinstance(l[0], (list, tuple)):
        return l
    return list(chain.from_iterable(l))
    
def reform_idx(flatten_pred_res, save_pred_res):
    if not isinstance(save_pred_res[0], (list, tuple)):
        return flatten_pred_res
    
    re = []
    i = 0
    for e in save_pred_res:
        re.append(flatten_pred_res[i:i + len(e)])
        i += len(e)
    return re

def hamming_dist(A, B):
    A = np.array(A, dtype='<U')
    B = np.array(B, dtype='<U')
    A = np.expand_dims(A, axis = 0).repeat(axis=0, repeats=(len(B)))
    return np.sum(A != B, axis = 1)

def confidence_dist(A, B):
    B = np.array(B)
    A = np.clip(A, 1e-9, 1)
    A = np.expand_dims(A, axis=0)
    A = A.repeat(axis=0, repeats=(len(B)))
    rows = np.array(range(len(B)))
    rows = np.expand_dims(rows, axis = 1).repeat(axis = 1, repeats = len(B[0]))
    cols = np.array(range(len(B[0])))
    cols = np.expand_dims(cols, axis = 0).repeat(axis = 0, repeats = len(B))
    return 1 - np.prod(A[rows, cols, B], axis = 1)

def block_sample(X, Z, Y, sample_num, epoch_idx):
    part_num = len(X) // sample_num
    if part_num == 0:
        part_num = 1
    seg_idx = epoch_idx % part_num
    INFO("seg_idx:", seg_idx, ", part num:", part_num, ", data num:", len(X))
    X = X[sample_num * seg_idx : sample_num * (seg_idx + 1)]
    Z = Z[sample_num * seg_idx : sample_num * (seg_idx + 1)]
    Y = Y[sample_num * seg_idx : sample_num * (seg_idx + 1)]

    return X, Z, Y

def gen_mappings(chars, symbs):
	n_char = len(chars)
	n_symbs = len(symbs)
	if n_char != n_symbs:
		print('Characters and symbols size dosen\'t match.')
		return
	from itertools import permutations
	mappings = []
	# returned mappings
	perms = permutations(symbs)
	for p in perms:
		mappings.append(dict(zip(chars, list(p))))
	return mappings

def mapping_res(original_pred_res, m):
    return [[m[symbol] for symbol in formula] for formula in original_pred_res]

def remapping_res(pred_res, m):
    remapping = {}
    for key, value in m.items():
        remapping[value] = key
    return [[remapping[symbol] for symbol in formula] for formula in pred_res]

def check_equal(a, b, max_err=0):
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) <= max_err
    
    if isinstance(a, list) and isinstance(b, list):
        if len(a) != len(b):
            return False
        for i in range(len(a)):
            if not check_equal(a[i], b[i]):
                return False
        return True
    
    else:    
        return a == b        

def to_hashable(l):
    if type(l) is not list:
        return l
    if type(l[0]) is not list:
        return tuple(l)
    return tuple(tuple(sublist) for sublist in l)

def hashable_to_list(t):
    if type(t) is not tuple:
        return t
    if type(t[0]) is not tuple:
        return list(t)
    return [list(subtuple) for subtuple in t]