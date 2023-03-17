# coding: utf-8
# ================================================================#
#   Copyright (C) 2021 Freecss All rights reserved.
#
#   File Name     ：share_example.py
#   Author        ：freecss
#   Email         ：karlfreecss@gmail.com
#   Created Date  ：2021/06/07
#   Description   ：
#
# ================================================================#

import sys
sys.path.append("../")

from abl.utils.plog import logger, INFO
import torch.nn as nn
import torch

from abl.models.nn import LeNet5, SymbolNet
from abl.models.basic_model import BasicModel, BasicDataset
from abl.models.wabl_models import DecisionTree, WABLBasicModel

from multiprocessing import Pool
from abl.abducer.abducer_base import AbducerBase, HED_Abducer
from abl.abducer.kb import add_KB, HWF_KB, prolog_KB, HED_prolog_KB
from datasets.mnist_add.get_mnist_add import get_mnist_add
from datasets.hwf.get_hwf import get_hwf
from datasets.hed.get_hed import get_hed, split_equation
from abl import framework_hed


def run_test():

    # kb = add_KB()
    kb = HWF_KB(GKB_flag=True)
    abducer = AbducerBase(kb, 'confidence')

    # kb = HED_prolog_KB(pseudo_label_list=[1, 0, '+', '='], pl_file='../examples/datasets/hed/learn_add.pl')
    # abducer = HED_Abducer(kb)

    recorder = logger()

    # total_train_data = get_hed(train=True)
    # train_data, val_data = split_equation(total_train_data, 3, 1)
    # test_data = get_hed(train=False)
    
    # train_data = get_mnist_add(train=True, get_pseudo_label=True)
    # test_data = get_mnist_add(train=False, get_pseudo_label=True)

    train_data = get_hwf(train=True, get_pseudo_label=True)
    test_data = get_hwf(train=False, get_pseudo_label=True)
    
    # cls = LeNet5(num_classes=len(kb.pseudo_label_list), image_size=(train_data[0][0][0].shape[1:]))
    cls = SymbolNet(num_classes=len(kb.pseudo_label_list), image_size=(train_data[0][0][0].shape[1:]))
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    
    # framework_hed.hed_pretrain(kb, cls, recorder)
    
    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.RMSprop(cls.parameters(), lr=0.001, weight_decay=1e-6)
    # optimizer = torch.optim.Adam(cls.parameters(), lr=0.001, betas=(0.9, 0.99))
    
    base_model = BasicModel(cls, criterion, optimizer, device, save_interval=1, save_dir=recorder.save_dir, batch_size=32, num_epochs=1, recorder=recorder)
    model = WABLBasicModel(base_model, kb.pseudo_label_list)

    # model, mapping = framework_hed.train_with_rule(model, abducer, train_data, val_data, select_num=10, min_len=5, max_len=8)
    # framework_hed.hed_test(model, abducer, mapping, train_data, test_data, min_len=5, max_len=8)
    
    framework_hed.train(model, abducer, train_data, test_data, sample_num=-1, verbose=1)

    recorder.dump()
    return True


if __name__ == "__main__":
    run_test()
