[![flake8 Lint](https://github.com/AbductiveLearning/ABL-Package/actions/workflows/lint.yml/badge.svg?branch=Dev)](https://github.com/AbductiveLearning/ABL-Package/actions/workflows/lint.yml)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![ABL-Package-CI](https://github.com/AbductiveLearning/ABL-Package/actions/workflows/build-and-test.yaml/badge.svg?branch=Dev)](https://github.com/AbductiveLearning/ABL-Package/actions/workflows/build-and-test.yaml)

# ABL Package

This is the code repository of abductive learning Package.

## Environment dependency 

#### Install Swipl 
[http://www.swi-prolog.org/build/unix.html](http://www.swi-prolog.org/build/unix.html)

#### Install required package

```shell
pip install zoopt
pip install pyswip==0.2.9
```


## Example 
share_example.py and nonshare_exaple.py are examples of grounded abductive learning.

```bash 
python share_example.py
```


## Authors 

- [Yu-Xuan Huang](http://www.lamda.nju.edu.cn/huangyx/) (Nanjing University)
- [](http://www.lamda.nju.edu.cn//) (Nanjing University)


## NOTICE 
They can only be used for academic purpose. For other purposes, please contact with LAMDA Group(www.lamda.nju.edu.cn).

## To do list 

- [ ] Improve speed and accuracy
- [ ] Add comparison with DeepProbLog, NGS,... (Accuracy and Speed)
- [x] Add Inference/Abduction example with FOL engine (e.g., Prolog)
- [x] Add zoopt optimization
- [ ] Rearrange structure and make it a python package
- [ ] Documents
