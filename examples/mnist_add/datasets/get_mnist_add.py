import os.path as osp

import torchvision
from torchvision.transforms import transforms

CURRENT_DIR = osp.abspath(osp.dirname(__file__))


def get_data(file, img_dataset, get_pseudo_label):
    X, Y = [], []
    if get_pseudo_label:
        Z = []
    with open(file) as f:
        for line in f:
            # if len(X) == 1000:
            #     break
            line = line.strip().split(" ")
            X.append([img_dataset[int(line[0])][0], img_dataset[int(line[1])][0]])
            if get_pseudo_label:
                Z.append([img_dataset[int(line[0])][1], img_dataset[int(line[1])][1]])
            Y.append(int(line[2]))

    if get_pseudo_label:
        return X, Z, Y
    else:
        return X, None, Y


def get_mnist_add(train=True, get_pseudo_label=False):
    transform = transforms.Compose(
        [transforms.ToTensor(), transforms.Normalize((0.1307,), (0.3081,))]
    )
    img_dataset = torchvision.datasets.MNIST(
        root=CURRENT_DIR, train=train, download=True, transform=transform
    )

    if train:
        file = osp.join(CURRENT_DIR, "train_data.txt")
    else:
        file = osp.join(CURRENT_DIR, "test_data.txt")

    return get_data(file, img_dataset, get_pseudo_label)


if __name__ == "__main__":
    train_X, train_Z, train_Y = get_mnist_add(train=True)
    test_X, test_Z, test_Y = get_mnist_add(train=False)
    print(len(train_X), len(test_X))
    print(train_X[0][0].shape, train_X[0][1].shape, train_Y[0])
