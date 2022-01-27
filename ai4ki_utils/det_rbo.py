import math
import numpy as np

def rbo(list1, list2, p=0.9):
    # Compare the ranking of the lists using Rank Biased Overlap (RBO)
    # The following code was taken from https://towardsdatascience.com/rbo-v-s-kendall-tau-to-compare-ranked-lists-of-items-8776c5182899
    # Define the RBO function:

    def helper(ret, i, d):
        l1 = set(list1[:i]) if i < len(list1) else set(list1)
        l2 = set(list2[:i]) if i < len(list2) else set(list2)
        a_d = len(l1.intersection(l2))/i
        term = math.pow(p, i) * a_d
        if d == i:
            return ret + term
        return helper(ret + term, i + 1, d)

    k = max(len(list1), len(list2))
    x_k = len(set(list1).intersection(set(list2)))
    summation = helper(0, 1, k)

    return ((float(x_k)/k) * math.pow(p, k)) + ((1-p)/p * summation)


def sum_series(p=0.9, d=10):

    def helper(ret, p, d, i):
        term = math.pow(p, i)/i
        if d == i:
           return ret + term
        return helper(ret + term, p, d, i+1)
    return helper(0, p, d, 1)

    wrbo1_d = 1 - math.pow(p, d-1) + (((1-p)/p) * d *(np.log(1/(1-p)) - sum_series(p, d-1)))

    return wrbo1_d