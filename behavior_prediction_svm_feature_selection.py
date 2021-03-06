###########################################################################
# loss function changed to SVM
###########################################################################
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
from torch import Tensor
import matplotlib.pyplot as plt
from utils import visualize as vize

# build a MLP
class Net(nn.Module):
    def __init__(self, inputs, units):
        super(Net, self).__init__()
        self.fc0 = nn.Linear(inputs, units)
        self.fc1 = nn.Linear(units, units)
        # self.drop1=nn.Dropout(p=0.5, inplace=False)
        self.fc2 = nn.Linear(units, units)
        self.fc3 = nn.Linear(units, 1)
        self.drop = nn.Dropout(p=dropoutRate)

    def forward(self, x):
        x = F.relu(self.fc0(x))
        x = self.drop(x)
        x = F.relu(self.fc1(x))
        x = self.drop(x)
        x = F.relu(self.fc2(x))
        x = self.drop(x)
        u = self.fc3(x)
        # p = torch.sigmoid(u)
        return u


def infer(net, x_validate, y_validate):
    x_validate = Tensor(x_validate)
    net.eval()  # turn off dropout layer
    with torch.no_grad():
        outputs = net(x_validate)
    outputs = outputs[:, 0]
    y_predict = np.ones_like(y_validate)
    y_predict[outputs<0.] = -1
    loss = 0
    lossRaw = 1. - y_validate * outputs.numpy()
    lossRaw[lossRaw < 0.] = 0.
    temp = y_predict == y_validate
    accuracy = (temp.astype(int)).mean()
    return lossRaw.mean(), accuracy


def analysis(x_test0, y_predict, y_label):
    # visualize_prediction(x_test0, y_test, y_predict)

    # for merge after
    label = y_label[x_test0[:, 0] == 1]
    predict = y_predict[x_test0[:, 0] == 1]
    accuracy = np.mean(label == predict)
    print('merge after', label.shape[0], ', accuracy for merge after samples', accuracy)
    # for merge infront
    label = y_label[x_test0[:, 0] == 0]
    predict = y_predict[x_test0[:, 0] == 0]
    accuracy = np.mean(label == predict)
    print('merge infront', label.shape[0], ', accuracy for merge in front samples', accuracy)

    accuracy = np.mean(y_predict == y_label)
    print('overall accuracy', accuracy)
    truePos = np.sum(y_label)
    trueNeg = y_label.shape[0] - truePos
    predictedPos = np.sum(y_predict)
    predictedNeg = y_predict.shape[0] - predictedPos
    print('true positive ', truePos)
    print('true negative ', trueNeg)
    print('predicted positive ', predictedPos)
    print('predicted negative ', predictedNeg)

def loadData():
    dir = '/home/hh/ngsim/I-80-Emeryville-CA/i-80-vehicle-trajectory-data/vehicle-trajectory-data/'
    f = np.load(dir + 'train_normalized.npz')
    x_train = f['a']
    y_train = f['b']
    print('x_train', x_train.shape[0], y_train.mean(), 'coop rate')
    y_train[y_train == 0] = -1

    f = np.load(dir + 'validate_normalized.npz')
    x_validate = f['a']
    y_validate = f['b']
    print('x_validate', x_validate.shape[0], y_validate.mean(), 'coop rate')
    y_validate[y_validate == 0] = -1

    f = np.load(dir + 'train_origin.npz')
    x_train0 = f['a']
    print(x_train0.shape)

    f = np.load(dir + 'validate_origin.npz')
    x_validate0 = f['a']
    print(x_validate0.shape)
    return (x_train0, x_train, y_train, x_validate0, x_validate, y_validate)

def train(epochs, train_loader, x_validate, y_validate, optimizer, net, PATH):
    losses = []
    accuracies = []
    losses_validate = []
    accuracies_validate = []
    bestValidationAcc = 0.
    stateDict = None
    for epoch in range(epochs):  # loop over the dataset multiple times
        running_loss = 0.0
        misClassify = 0
        for i, data in enumerate(train_loader, 0):
            # get the inputs; data is a list of [inputs, labels]
            inputs, labels = data
            if (i == 0 and epoch == 0):
                print('inputs', inputs)

            # zero the parameter gradients
            optimizer.zero_grad()

            # forward + backward + optimize
            outputs = net(inputs)
            # print('label', labels)
            # print('outputs', outputs)
            outputs = outputs[:, 0]
            lossRaw = 1 - labels * outputs
            lossRaw[lossRaw < 0.] = 0.
            # print(lossRaw)
            loss = lossRaw.sum()
            loss.backward()
            optimizer.step()

            y_predict = outputs.detach().numpy()
            y_predict[y_predict > 0] = 1
            y_predict[y_predict <= 0] = -1
            misClassify += np.sum(y_predict != labels.numpy())

            # print statistics
            running_loss += loss.item()
        accuracy = 1 - misClassify / x_train.shape[0]
        loss = running_loss / x_train.shape[0]
        losses.append(loss)
        accuracies.append(accuracy)
        print('train: epoch', epoch, ', loss', loss, 'accuracy', accuracy)

        loss, accuracy = infer(net, x_validate, y_validate)
        if accuracy > bestValidationAcc:
            bestValidationAcc = accuracy
            stateDict = net.state_dict()
            torch.save(stateDict, PATH)
        losses_validate.append(loss)
        accuracies_validate.append(accuracy)
        print('validate: epoch', epoch, ', loss', loss, 'accuracy', accuracy)

        net.train()  # switch back to train model, in which dropout is turned on

    plt.figure()
    plt.plot(np.arange(len(losses)) + 1, losses, label='train')
    plt.plot(np.arange(len(losses)) + 1, losses_validate, label='validate')
    plt.xlabel('epoch')
    plt.ylabel('loss')
    plt.legend()

    plt.figure()
    plt.plot(np.arange(len(losses)) + 1, accuracies, label='train')
    plt.plot(np.arange(len(losses)) + 1, accuracies_validate, label='validate')
    plt.xlabel('epoch')
    plt.ylabel('accuracy')
    plt.legend()
    plt.show()

    np.savetxt(dir + 'svm_10_features_loss_acc.txt', np.array([np.arange(len(losses))+1, losses, losses_validate,
                                                               accuracies, accuracies_validate]).T, fmt='%1.4f')
    print('Best validation acc ', max(accuracies_validate))

seed0 = 1013899
seed1 = 1018859
torch.manual_seed(seed0)

batchSize = 4
epochs = 200
hiddenUnits = 64
learningRate = 0.0002
dropoutRate = 0.3
l2Penalty = 1.0e-3

inputs = 2
(x_train0, x_train, y_train, x_validate0, x_validate, y_validate) = loadData()
mask0 = np.array([0, 1, 3, 6, 7, 8, 9]) # already been chosen to delete
for i in range(10):
    if i in mask0: continue
    mask = np.insert(mask0, -1, i)
    print('Delete feature ', mask)
    x_train1 = np.delete(x_train, mask, axis=1)
    x_validate1 = np.delete(x_validate, mask, axis=1)
    dataset_train = TensorDataset(Tensor(x_train1), Tensor(y_train))
    train_loader = torch.utils.data.DataLoader(dataset_train, batch_size=batchSize, shuffle=False)

    net = Net(inputs, hiddenUnits)
    optimizer = optim.Adam(net.parameters(), lr=learningRate,
                           weight_decay=l2Penalty)
    dir = '/home/hh/data/ngsim/'
    PATH = dir + '/svm_10_features_net.pth'

    trained = False
    # trained=True
    if not trained:
        train(epochs, train_loader, x_validate1, y_validate, optimizer, net, PATH)

# net.load_state_dict(torch.load(PATH))
# print('load parameters successfully')

# print('for train')
# net.eval()  # turn on eval, switch off dropout layer
# with torch.no_grad():
#     y_predict = net(Tensor(x_train))
# y_predict = y_predict[:,0]
# predict = np.ones_like(y_predict)
# predict[y_predict<0]=-1
# analysis(x_train0, predict, y_train)
# y_train[y_train == -1] = 0.
# predict[predict == -1] = 0.
# vize.visualize_sample(x_train0, y_train)
# vize.visualize_prediction(x_train0, y_train, predict)
#
# print('for validate')
# with torch.no_grad():
#     y_predict = net(Tensor(x_validate))
# y_predict = y_predict[:,0]
# predict = np.ones_like(y_predict)
# predict[y_predict<0]=-1
# analysis(x_validate0, predict, y_validate)
# y_validate[y_validate == -1] = 0.
# predict[predict == -1] = 0.
# vize.visualize_sample(x_validate0, y_validate)
# vize.visualize_prediction(x_validate0, y_validate, predict)

