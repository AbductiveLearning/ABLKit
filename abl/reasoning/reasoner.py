import numpy as np
from multiprocessing import Pool
from zoopt import Dimension, Objective, Parameter, Opt
from ..utils.utils import (
    confidence_dist,
    flatten,
    reform_idx,
    hamming_dist,
    float_parameter,
)


class ReasonerBase():
    def __init__(self, kb, dist_func="hamming", mapping=None, use_zoopt=False):
        """
        This class serves as 
        
        Parameter `dist_func` is used to specify the distance function to use.
        """
        
        if not (dist_func == "hamming" or dist_func == "confidence"):
            raise NotImplementedError # Only hamming or confidence distance is available.

        self.kb = kb
        self.dist_func = dist_func
        self.use_zoopt = use_zoopt
        if mapping is None:
            self.mapping = {index: label for index, label in enumerate(self.kb.pseudo_label_list)}
        else:
            self.mapping = mapping
        self.remapping = dict(zip(self.mapping.values(), self.mapping.keys()))

    def _get_cost_list(self, pseudo_label, pred_res_prob, candidates):
        """
        Get the list consisting of costs between each pseudo label and candidate.
        Parameter `pred_res_prob` is needed while using confidence distance.
        """
        if self.dist_func == "hamming":
            return hamming_dist(pseudo_label, candidates)

        elif self.dist_func == "confidence":
            candidates = [[self.remapping[x] for x in c] for c in candidates]
            return confidence_dist(pred_res_prob, candidates)

    def _get_one_candidate(self, pseudo_label, pred_res_prob, candidates):
        """
        Get one candidate. If multiple candidates exist, return the one with minimum cost.
        """
        if len(candidates) == 0:
            return []
        elif len(candidates) == 1:
            return candidates[0]
        else:
            cost_list = self._get_cost_list(pseudo_label, pred_res_prob, candidates)
            candidate = candidates[np.argmin(cost_list)]
            return candidate

    def zoopt_revision_score(self, pred_res, pseudo_label, pred_res_prob, y, sol):
        """
        Get the revision score for a single solution.

        Parameters
        ----------
        sol_x : array-like
            Solution to evaluate.
        pred_res : list
            List of predicted results.
        pseudo_label : list
            List of predicted pseudo labels.
        pred_res_prob : list
            List of probabilities for predicted results.
        y : str
            Ground truth for the predicted results.

        Returns
        -------
        float
            The revision score for the given solution.
        """
        revision_idx = np.where(sol.get_x() != 0)[0]
        candidates = self.revise_by_idx(pseudo_label, y, revision_idx)
        if len(candidates) > 0:
            return np.min(self._get_cost_list(pseudo_label, pred_res_prob, candidates))
        else:
            return len(pred_res)

    def _constrain_revision_num(self, solution, max_revision_num):
        x = solution.get_x()
        return max_revision_num - x.sum()

    def zoopt_get_solution(self, pred_res, pseudo_label, pred_res_prob, y, max_revision_num):
        """Get the optimal solution using the Zoopt library.

        Parameters
        ----------
        pred_res : list
            List of predicted results.
        pseudo_label : list
            List of predicted pseudo labels.
        pred_res_prob : list
            List of probabilities for predicted results.
        y : str
            Ground truth for the predicted results.
        max_revision_num : int
            Maximum number of revisions to use.

        Returns
        -------
        array-like
            The optimal solution.
        """
        length = len(flatten(pred_res))
        dimension = Dimension(size=length, regs=[[0, 1]] * length, tys=[False] * length)
        objective = Objective(
            lambda sol: self.zoopt_revision_score(pred_res, pseudo_label, pred_res_prob, y, sol),
            dim=dimension,
            constraint=lambda sol: self._constrain_revision_num(sol, max_revision_num),
        )
        parameter = Parameter(budget=100, intermediate_result=False, autoset=True)
        solution = Opt.min(objective, parameter).get_x()
        return solution

    def revise_by_idx(self, pseudo_label, y, revision_idx):
        """
        Get the revisions corresponding to the given indices.

        Parameters
        ----------
        pseudo_label : list
            List of predicted pseudo labels.
        y : str
            Ground truth for the predicted results.
        revision_idx : array-like
            Indices of the revisions to retrieve.

        Returns
        -------
        list
            The revisions corresponding to the given indices.
        """
        return self.kb.revise_by_idx(pseudo_label, y, revision_idx)

    def abduce(self, data, max_revision=-1, require_more_revision=0):
        """
        Perform abduction on the given data.

        Parameters
        ----------
        data : tuple
            Tuple containing the predicted results, predicted result probabilities, and y.
        max_revision : int or float, optional
            Maximum number of revisions to use. If float, represents the fraction of total revisions to use.
            If -1, use all revisions. Defaults to -1.
        require_more_revision : int, optional
            Number of additional revisions to require. Defaults to 0.

        Returns
        -------
        list
            The abduced revisions.
        """
        pred_label, pred_prob, pred_pseudo_label, y = data
        max_revision_num = float_parameter(max_revision, len(flatten(pred_label)))

        if self.use_zoopt:
            solution = self.zoopt_get_solution(pred_label, pred_pseudo_label, pred_prob, y, max_revision_num)
            revision_idx = np.where(solution != 0)[0]
            candidates = self.revise_by_idx(pred_pseudo_label, y, revision_idx)
        else:
            candidates = self.kb.abduce_candidates(pred_pseudo_label, y, max_revision_num, require_more_revision)

        candidate = self._get_one_candidate(pred_pseudo_label, pred_prob, candidates)
        return candidate

    def batch_abduce(self, pred_label, pred_prob, pred_pseudo_label, Y, max_revision=-1, require_more_revision=0):
        """Perform abduction on the given data in batches.

        Parameters
        ----------
        Z : list
            List of predicted results and result probablities.
        Y : list
            List of ground truths.
        max_revision : int or float, optional
            Maximum number of revisions to use. If float, represents the fraction of total revisions to use.
            If -1, use all revisions. Defaults to -1.
        require_more_revision : int, optional
            Number of additional revisions to require. Defaults to 0.

        Returns
        -------
        list
            The abduced revisions.
        """
        return [
            self.abduce(data, max_revision, require_more_revision)
            for data in zip(pred_label, pred_prob, pred_pseudo_label, Y)
        ]

    # def _batch_abduce_helper(self, args):
    #     z, prob, y, max_revision, require_more_revision = args
    #     return self.abduce((z, prob, y), max_revision, require_more_revision)

    # def batch_abduce(self, Z, Y, max_revision=-1, require_more_revision=0):
    #     with Pool(processes=os.cpu_count()) as pool:
    #         results = pool.map(self._batch_abduce_helper, [(z, prob, y, max_revision, require_more_revision) for z, prob, y in zip(Z['cls'], Z['prob'], Y)])
    #     return results

    def __call__(self, Z, Y, max_revision=-1, require_more_revision=0):
        return self.batch_abduce(Z, Y, max_revision, require_more_revision)


if __name__ == "__main__":
    from kb import KBBase, prolog_KB

    prob1 = [
        [
            [0, 0.99, 0.01, 0, 0, 0, 0, 0, 0, 0],
            [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1],
        ]
    ]
    prob2 = [
        [
            [0, 0, 0.01, 0, 0, 0, 0, 0.99, 0, 0],
            [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1],
        ]
    ]

    class add_KB(KBBase):
        def __init__(
            self,
            pseudo_label_list=list(range(10)),
            prebuild_GKB=False,
            GKB_len_list=[2],
            max_err=0,
            use_cache=True,
        ):
            super().__init__(pseudo_label_list, prebuild_GKB, GKB_len_list, max_err, use_cache)

        def logic_forward(self, nums):
            return sum(nums)

    print("add_KB with GKB:")
    kb = add_KB(prebuild_GKB=True)
    reasoner = ReasonerBase(kb, "confidence")
    res = reasoner.batch_abduce([[1, 1]], prob1, [[1, 1]], [8], max_revision=2, require_more_revision=0)
    print(res)
    res = reasoner.batch_abduce([[1, 1]], prob2, [[1, 1]], [8], max_revision=2, require_more_revision=0)
    print(res)
    res = reasoner.batch_abduce([[1, 1]], prob1, [[1, 1]], [17], max_revision=2, require_more_revision=0)
    print(res)
    res = reasoner.batch_abduce([[1, 1]], prob1, [[1, 1]], [17], max_revision=1, require_more_revision=0)
    print(res)
    res = reasoner.batch_abduce([[1, 1]], prob1, [[1, 1]], [20], max_revision=2, require_more_revision=0)
    print(res)
    print()

    print("add_KB without GKB:")
    kb = add_KB()
    reasoner = ReasonerBase(kb, "confidence")
    res = reasoner.batch_abduce([[1, 1]], prob1, [[1, 1]], [8], max_revision=2, require_more_revision=0)
    print(res)
    res = reasoner.batch_abduce([[1, 1]], prob2, [[1, 1]], [8], max_revision=2, require_more_revision=0)
    print(res)
    res = reasoner.batch_abduce([[1, 1]], prob1, [[1, 1]], [17], max_revision=2, require_more_revision=0)
    print(res)
    res = reasoner.batch_abduce([[1, 1]], prob1, [[1, 1]], [17], max_revision=1, require_more_revision=0)
    print(res)
    res = reasoner.batch_abduce([[1, 1]], prob1, [[1, 1]], [20], max_revision=2, require_more_revision=0)
    print(res)
    print()

    print("add_KB without GKB:, no cache")
    kb = add_KB(use_cache=False)
    reasoner = ReasonerBase(kb, "confidence")
    res = reasoner.batch_abduce([[1, 1]], prob1, [[1, 1]], [8], max_revision=2, require_more_revision=0)
    print(res)
    res = reasoner.batch_abduce([[1, 1]], prob2, [[1, 1]], [8], max_revision=2, require_more_revision=0)
    print(res)
    res = reasoner.batch_abduce([[1, 1]], prob1, [[1, 1]], [17], max_revision=2, require_more_revision=0)
    print(res)
    res = reasoner.batch_abduce([[1, 1]], prob1, [[1, 1]], [17], max_revision=1, require_more_revision=0)
    print(res)
    res = reasoner.batch_abduce([[1, 1]], prob1, [[1, 1]], [20], max_revision=2, require_more_revision=0)
    print(res)
    print()

    print("prolog_KB with add.pl:")
    kb = prolog_KB(
        pseudo_label_list=list(range(10)),
        pl_file="examples/mnist_add/datasets/add.pl",
    )
    reasoner = ReasonerBase(kb, "confidence")
    res = reasoner.batch_abduce([[1, 1]], prob1, [[1, 1]], [8], max_revision=2, require_more_revision=0)
    print(res)
    res = reasoner.batch_abduce([[1, 1]], prob2, [[1, 1]], [8], max_revision=2, require_more_revision=0)
    print(res)
    res = reasoner.batch_abduce([[1, 1]], prob1, [[1, 1]], [17], max_revision=2, require_more_revision=0)
    print(res)
    res = reasoner.batch_abduce([[1, 1]], prob1, [[1, 1]], [17], max_revision=1, require_more_revision=0)
    print(res)
    res = reasoner.batch_abduce([[1, 1]], prob1, [[1, 1]], [20], max_revision=2, require_more_revision=0)
    print(res)
    print()

    print("prolog_KB with add.pl using zoopt:")
    kb = prolog_KB(
        pseudo_label_list=list(range(10)),
        pl_file="examples/mnist_add/datasets/add.pl",
    )
    reasoner = ReasonerBase(kb, "confidence", use_zoopt=True)
    res = reasoner.batch_abduce([[1, 1]], prob1, [[1, 1]], [8], max_revision=2, require_more_revision=0)
    print(res)
    res = reasoner.batch_abduce([[1, 1]], prob2, [[1, 1]], [8], max_revision=2, require_more_revision=0)
    print(res)
    res = reasoner.batch_abduce([[1, 1]], prob1, [[1, 1]], [17], max_revision=2, require_more_revision=0)
    print(res)
    res = reasoner.batch_abduce([[1, 1]], prob1, [[1, 1]], [17], max_revision=1, require_more_revision=0)
    print(res)
    res = reasoner.batch_abduce([[1, 1]], prob1, [[1, 1]], [20], max_revision=2, require_more_revision=0)
    print(res)
    print()

    print("add_KB with multiple inputs at once:")
    multiple_prob = [
        [
            [0, 0.99, 0.01, 0, 0, 0, 0, 0, 0, 0],
            [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1],
        ],
        [
            [0, 0, 0.01, 0, 0, 0, 0, 0.99, 0, 0],
            [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.1],
        ],
    ]

    kb = add_KB()
    reasoner = ReasonerBase(kb, "confidence")
    res = reasoner.batch_abduce(
        [[1, 1], [1, 2]], multiple_prob, [[1, 1], [1, 2]], [4, 8],
        max_revision=2,
        require_more_revision=0,
    )
    print(res)
    res = reasoner.batch_abduce(
        [[1, 1], [1, 2]], multiple_prob, [[1, 1], [1, 2]], [4, 8],
        max_revision=2,
        require_more_revision=1,
    )
    print(res)
    print()

    class HWF_KB(KBBase):
        def __init__(
            self,
            pseudo_label_list=[
                "1",
                "2",
                "3",
                "4",
                "5",
                "6",
                "7",
                "8",
                "9",
                "+",
                "-",
                "times",
                "div",
            ],
            prebuild_GKB=False,
            GKB_len_list=[1, 3, 5, 7],
            max_err=1e-3,
            use_cache=True,
        ):
            super().__init__(pseudo_label_list, prebuild_GKB, GKB_len_list, max_err, use_cache)

        def _valid_candidate(self, formula):
            if len(formula) % 2 == 0:
                return False
            for i in range(len(formula)):
                if i % 2 == 0 and formula[i] not in [
                    "1",
                    "2",
                    "3",
                    "4",
                    "5",
                    "6",
                    "7",
                    "8",
                    "9",
                ]:
                    return False
                if i % 2 != 0 and formula[i] not in ["+", "-", "times", "div"]:
                    return False
            return True

        def logic_forward(self, formula):
            if not self._valid_candidate(formula):
                return np.inf
            mapping = {str(i): str(i) for i in range(1, 10)}
            mapping.update({"+": "+", "-": "-", "times": "*", "div": "/"})
            formula = [mapping[f] for f in formula]
            return eval("".join(formula))

    print("HWF_KB with GKB, max_err=0.1")
    kb = HWF_KB(prebuild_GKB=True, GKB_len_list=[1, 3, 5], max_err=0.1)
    reasoner = ReasonerBase(kb, "hamming")
    res = reasoner.batch_abduce(
        [["5", "+", "2"]], [None], [[5,10,2]], [3],
        max_revision=2,
        require_more_revision=0,
    )
    print(res)
    res = reasoner.batch_abduce(
        [["5", "+", "2"]], [None], [[5,10,9]], [65],
        max_revision=3,
        require_more_revision=0,
    )
    print(res)
    res = reasoner.batch_abduce(
        [["5", "8", "8", "8", "8"]], [None], [[5,8,8,8,8]], [3.17],
        max_revision=5,
        require_more_revision=3,
    )
    print(res)
    print()

    print("HWF_KB without GKB, max_err=0.1")
    kb = HWF_KB(GKB_len_list=[1, 3, 5], max_err=0.1)
    reasoner = ReasonerBase(kb, "hamming")
    res = reasoner.batch_abduce(
        [["5", "+", "2"]], [None], [[5,10,2]], [3],
        max_revision=2,
        require_more_revision=0,
    )
    print(res)
    res = reasoner.batch_abduce(
        [["5", "+", "2"]], [None], [[5,10,9]], [65],
        max_revision=3,
        require_more_revision=0,
    )
    print(res)
    res = reasoner.batch_abduce(
        [["5", "8", "8", "8", "8"]], [None], [[5,8,8,8,8]], [3.17],
        max_revision=5,
        require_more_revision=3,
    )
    print(res)
    print()

    print("HWF_KB with GKB, max_err=1")
    kb = HWF_KB(GKB_len_list=[1, 3, 5], prebuild_GKB=True, max_err=1)
    reasoner = ReasonerBase(kb, "hamming")
    res = reasoner.batch_abduce(
        [["5", "+", "2"]], [None], [[5,10,2]], [3],
        max_revision=2,
        require_more_revision=0,
    )
    print(res)
    res = reasoner.batch_abduce(
        [["5", "+", "2"]], [None], [[5,10,9]], [65],
        max_revision=3,
        require_more_revision=0,
    )
    print(res)
    res = reasoner.batch_abduce(
        [["5", "8", "8", "8", "8"]], [None], [[5,8,8,8,8]], [3.17],
        max_revision=5,
        require_more_revision=3,
    )
    print(res)
    print()

    print("HWF_KB without GKB, max_err=1")
    kb = HWF_KB(GKB_len_list=[1, 3, 5], max_err=1)
    reasoner = ReasonerBase(kb, "hamming")
    res = reasoner.batch_abduce(
        [["5", "+", "2"]], [None], [[5,10,2]], [3],
        max_revision=2,
        require_more_revision=0,
    )
    print(res)
    res = reasoner.batch_abduce(
        [["5", "+", "2"]], [None], [[5,10,9]], [65],
        max_revision=3,
        require_more_revision=0,
    )
    print(res)
    res = reasoner.batch_abduce(
        [["5", "8", "8", "8", "8"]], [None], [[5,8,8,8,8]], [3.17],
        max_revision=5,
        require_more_revision=3,
    )
    print(res)
    print()

    print("HWF_KB with multiple inputs at once:")
    kb = HWF_KB(GKB_len_list=[1, 3, 5], max_err=0.1)
    reasoner = ReasonerBase(kb, "hamming")
    res = reasoner.batch_abduce(
        [["5", "+", "2"], ["5", "+", "9"]], [None, None], [[5,10,2],[5,10,9]],
        [3, 64],
        max_revision=1,
        require_more_revision=0,
    )
    print(res)
    res = reasoner.batch_abduce(
        [["5", "+", "2"], ["5", "+", "9"]], [None, None], [[5,10,2],[5,10,9]],
        [3, 64],
        max_revision=3,
        require_more_revision=0,
    )
    print(res)
    res = reasoner.batch_abduce(
        [["5", "+", "2"], ["5", "+", "9"]], [None, None], [[5,10,2],[5,10,9]],
        [3, 65],
        max_revision=3,
        require_more_revision=0,
    )
    print(res)
    print()
    print("max_revision is float")
    res = reasoner.batch_abduce(
        [["5", "+", "2"], ["5", "+", "9"]], [None, None], [[5,10,2],[5,10,9]],
        [3, 64],
        max_revision=0.5,
        require_more_revision=0,
    )
    print(res)
    res = reasoner.batch_abduce(
        [["5", "+", "2"], ["5", "+", "9"]], [None, None], [[5,10,2],[5,10,9]],
        [3, 64],
        max_revision=0.9,
        require_more_revision=0,
    )
    print(res)
    print()

    class HED_prolog_KB(prolog_KB):
        def __init__(self, pseudo_label_list, pl_file):
            super().__init__(pseudo_label_list, pl_file)

        def consist_rule(self, exs, rules):
            rules = str(rules).replace("'", "")
            pl_query = "eval_inst_feature(%s, %s)." % (exs, rules)
            return len(list(self.prolog.query(pl_query))) != 0

        def abduce_rules(self, pred_res):
            pl_query = "consistent_inst_feature(%s, X)." % pred_res
            prolog_result = list(self.prolog.query(pl_query))
            if len(prolog_result) == 0:
                return None
            prolog_rules = prolog_result[0]["X"]
            rules = [rule.value for rule in prolog_rules]
            return rules

    class HED_Reasoner(ReasonerBase):
        def __init__(self, kb, dist_func="hamming"):
            super().__init__(kb, dist_func, zoopt=True)

        def _revise_by_idxs(self, pred_res, y, all_revision_flag, idxs):
            pred = []
            k = []
            revision_flag = []
            for idx in idxs:
                pred.append(pred_res[idx])
                k.append(y[idx])
                revision_flag += list(all_revision_flag[idx])
            revision_idx = np.where(np.array(revision_flag) != 0)[0]
            candidate = self.revise_by_idx(pred, k, revision_idx)
            return candidate

        def zoopt_revision_score(self, pred_res, pred_res_prob, y, sol):
            all_revision_flag = reform_idx(sol.get_x(), pred_res)
            lefted_idxs = [i for i in range(len(pred_res))]
            candidate_size = []
            while lefted_idxs:
                idxs = []
                idxs.append(lefted_idxs.pop(0))
                max_candidate_idxs = []
                found = False
                for idx in range(-1, len(pred_res)):
                    if (not idx in idxs) and (idx >= 0):
                        idxs.append(idx)
                    candidate = self._revise_by_idxs(pred_res, y, all_revision_flag, idxs)
                    if len(candidate) == 0:
                        if len(idxs) > 1:
                            idxs.pop()
                    else:
                        if len(idxs) > len(max_candidate_idxs):
                            found = True
                            max_candidate_idxs = idxs.copy()
                removed = [i for i in lefted_idxs if i in max_candidate_idxs]
                if found:
                    candidate_size.append(len(removed) + 1)
                    lefted_idxs = [i for i in lefted_idxs if i not in max_candidate_idxs]
            candidate_size.sort()
            score = 0
            import math

            for i in range(0, len(candidate_size)):
                score -= math.exp(-i) * candidate_size[i]
            return score

        def abduce_rules(self, pred_res):
            return self.kb.abduce_rules(pred_res)

    kb = HED_prolog_KB(
        pseudo_label_list=[1, 0, "+", "="],
        pl_file="examples/hed/datasets/learn_add.pl",
    )
    reasoner = HED_Reasoner(kb)
    consist_exs = [
        [1, 1, "+", 0, "=", 1, 1],
        [1, "+", 1, "=", 1, 0],
        [0, "+", 0, "=", 0],
    ]
    inconsist_exs1 = [
        [1, 1, "+", 0, "=", 1, 1],
        [1, "+", 1, "=", 1, 0],
        [0, "+", 0, "=", 0],
        [0, "+", 0, "=", 1],
    ]
    inconsist_exs2 = [[1, "+", 0, "=", 0], [1, "=", 1, "=", 0], [0, "=", 0, "=", 1, 1]]
    rules = ["my_op([0], [0], [0])", "my_op([1], [1], [1, 0])"]

    print("HED_kb logic forward")
    print(kb.logic_forward(consist_exs))
    print(kb.logic_forward(inconsist_exs1), kb.logic_forward(inconsist_exs2))
    print()
    print("HED_kb consist rule")
    print(kb.consist_rule([1, "+", 1, "=", 1, 0], rules))
    print(kb.consist_rule([1, "+", 1, "=", 1, 1], rules))
    print()

    print("HED_Reasoner abduce")
    res = reasoner.abduce((consist_exs, [[[None]]] * len(consist_exs), [None] * len(consist_exs)))
    print(res)
    res = reasoner.abduce((inconsist_exs1, [[[None]]] * len(inconsist_exs1), [None] * len(inconsist_exs1)))
    print(res)
    res = reasoner.abduce((inconsist_exs2, [[[None]]] * len(inconsist_exs2), [None] * len(inconsist_exs2)))
    print(res)
    print()

    print("HED_Reasoner abduce rules")
    abduced_rules = reasoner.abduce_rules(consist_exs)
    print(abduced_rules)
