from typing import Optional

from ..structures import ListData
from .base_metric import BaseMetric


class SymbolMetric(BaseMetric):
    def __init__(self, prefix: Optional[str] = None) -> None:
        super().__init__(prefix)

    def process(self, data_samples: ListData) -> None:
        pred_pseudo_label_list = data_samples.flatten("pred_pseudo_label")
        gt_pseudo_label_list = data_samples.flatten("gt_pseudo_label")

        if not len(pred_pseudo_label_list) == len(gt_pseudo_label_list):
            raise ValueError("lengthes of pred_pseudo_label and gt_pseudo_label should be equal")

        correct_num = 0
        for pred_pseudo_label, gt_pseudo_label in zip(pred_pseudo_label_list, gt_pseudo_label_list):
            if pred_pseudo_label == gt_pseudo_label:
                correct_num += 1
        self.results.append((correct_num, len(pred_pseudo_label_list)))

    def compute_metrics(self) -> dict:
        results = self.results
        metrics = dict()
        metrics["character_accuracy"] = sum(t[0] for t in results) / sum(t[1] for t in results)
        return metrics
