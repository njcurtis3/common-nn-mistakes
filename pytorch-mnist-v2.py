################################
## Imports
################################
from __future__ import print_function
import argparse

import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torchvision import datasets, transforms
from torch.autograd import Variable

# livelossplot requires inline matplotlib
import missinglink

missinglink_project = missinglink.PyTorchProject(project_token='KzcbCxZWjewiqxCi')

################################
## Constants
################################

class dotdict(dict):
    """dot.notation access to dictionary attributes"""
    __getattr__ = dict.get
    __setattr__ = dict.__setitem__
    __delattr__ = dict.__delitem__

args = dotdict()

args.seed = 321
args.batch_size = 200
args.test_batch_size = 64
args.epochs = 3
args.lr = 0.03
args.momentum = 0.5
args.log_interval = 5

mnist_mean = 0.1307
mnist_std = 0.3081

torch.manual_seed(args.seed)

################################
## NN Architecture
################################

class SimpleNet(nn.Module):
    def __init__(self):
        super(SimpleNet, self).__init__()
        self.conv1 = nn.Conv2d(1, 10, kernel_size=5)
        self.conv2 = nn.Conv2d(10, 20, kernel_size=5)
        self.conv2_drop = nn.Dropout2d()
        self.fc1 = nn.Linear(320, 50)
        self.fc2 = nn.Linear(50, 10)

    def forward(self, x):
        batch_size = x.shape[0]
        x = F.relu(F.max_pool2d(self.conv1(x), 2))
        x = F.relu(F.max_pool2d(self.conv2_drop(self.conv2(x)), 2))
        #x = F.relu(F.max_pool2d(self.conv2(x), 2))
        x = x.view(batch_size, -1)
        x = F.relu(self.fc1(x))
        x = F.dropout(x, training=self.training)
        x = self.fc2(x)
        return F.log_softmax(x, dim=1)

################################
## Functions
################################

def get_correct_count(output, target):
    _, indexes = output.data.max(1, keepdim=True)
    return indexes.eq(target.data.view_as(indexes)).cpu().sum().item()

def test(model, test_loader):
    model.eval()
    test_loss = 0
    correct = 0
    seen = 0
    # `no_grad` so we don't use these calculations in backprop
    with torch.no_grad():
        for data, target in test_loader:
            data = Variable(data)
            target = Variable(target)
            output = model(data)
            seen += len(output)
            
            # sum up batch loss
            test_loss += F.nll_loss(output, target, reduction='sum').item()
            
            # get the index of the max log-probability
            correct += get_correct_count(output, target)

    test_loss /= seen
    test_accuracy = correct * 100.0 / seen

    print(
       'Test: Average loss: {:.4f}, Accuracy: {}/{} ({:.0f}%)'.format(
           test_loss, correct, seen, test_accuracy))
    return test_loss, test_accuracy

def train(model, optimizer, epoch, train_loader, test_loader):
    #for batch_idx, (data, target) in enumerate(train_loader):
    for batch_idx, (data, target) in experiment.batch_loop(iterable=train_loader):
        model.train()
        data, target = Variable(data), Variable(target)
        output = model(data)
        loss_t = F.nll_loss(output, target)
        optimizer.zero_grad()
        loss_t.backward()
        optimizer.step()

        #train_accuracy = get_correct_count(output, target) * 100.0 / len(target)
        if batch_idx % args.log_interval == 0:
            train_loss = loss_t.item()
            train_accuracy = get_correct_count(output, target) * 100.0 / len(target)
            experiment._update_metric_data('ml_train_Loss', train_loss)
            experiment._update_metric_data('ml_train_Accuracy', train_accuracy)
            # wrapped_loss(train_loss)
            # wrapped_acc(train_accuracy)
            print('Train Epoch: {} [{}/{} ({:.0f}%)]\tLoss: {:.6f}'.format(
                epoch, batch_idx, len(train_loader),
                100. * batch_idx / len(train_loader), train_loss))
            with experiment.validation():
                test_loss, test_accuracy = test(model, test_loader)
                experiment._update_metric_data('ml_val_Loss', test_loss)
                experiment._update_metric_data('ml_val_Accuracy', test_accuracy)
                # wrapped_acc(test_accuracy)
                # wrapped_loss(test_loss)


def get_train_test():
    train_loader = torch.utils.data.DataLoader(
        datasets.MNIST(
            './data',
            train=True,
            download=True,
            transform=transforms.Compose([
                transforms.ToTensor(),
                transforms.Normalize((mnist_mean, ), (mnist_std, ))
            ])),
        batch_size=args.batch_size,
        shuffle=True,
        drop_last=True)
    
    test_loader = torch.utils.data.DataLoader(
        datasets.MNIST(
            './data',
            train=False,
            transform=transforms.Compose([
                transforms.ToTensor(),
                transforms.Normalize((mnist_mean, ), (mnist_std, ))
            ])),
        batch_size=args.test_batch_size,
        shuffle=True,
        drop_last=True)
    
    return train_loader, test_loader

################################
## Main Execution
################################
def report_metric(val):
    return val

def main():
    global experiment#, wrapped_loss, wrapped_acc

    # Get Data
    train_loader, test_loader = get_train_test()

    # instatiate NN model
    model = SimpleNet()

    optimizer = optim.SGD(model.parameters(), lr=args.lr, momentum=args.momentum)

    first_batch = next(iter(train_loader))

    with missinglink_project.create_experiment(
            model=model,
            optimizer=optimizer,
            train_data_object=train_loader,
            metrics={'Loss': report_metric, 'Accuracy': report_metric}
            ) as experiment:
        # wrapped_loss = experiment.metrics['Loss']
        # wrapped_acc = experiment.metrics['Accuracy']
        #for epoch in range(args.epochs):
        for epoch in experiment.epoch_loop(args.epochs):
            #train(model, optimizer, epoch, [first_batch] * 50, [first_batch])
            train(model, optimizer, epoch, [first_batch] * 50, [next(iter(test_loader))])
            #train(model, optimizer, epoch, [first_batch] * 50, test_loader)
            #train(model, optimizer, epoch, train_loader, test_loader)

        with experiment.test():
            print("--Final test--")
            test(model, test_loader)
    
    return model

trained_model = main()

