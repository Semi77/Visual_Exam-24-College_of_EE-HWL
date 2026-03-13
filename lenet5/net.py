import torch
from torch import nn

# 定义一个网络模型
class  MyLeNet(nn.Module):
    # 初始化网络模型
    def __init__(self):
        super(MyLeNet,self).__init__()
        # 第一步：第一层卷积
        self.c1 = nn.Conv2d(in_channels=1,out_channels=16,kernel_size=5,padding=2)
        # 第二步：使用Sigmoid函数激活
        self.Sigmoid = nn.Sigmoid()
        # 第三步：平均池化s2
        self.s2 = nn.AvgPool2d(kernel_size=2,stride=2)
        # 第四步：第二层卷积
        self.c3 = nn.Conv2d(in_channels=16,out_channels=16,kernel_size=5)
        # 第五步：池化s4
        self.s4 = nn.AvgPool2d(kernel_size=2,stride=2)
        # 第六步：卷积c5
        self.c5 = nn.Conv2d(in_channels=16,out_channels=120,kernel_size=5)
        # 第七步：展平flatten
        self.flatten = nn.Flatten()
        # 第八步：全连接层
        self.f6 = nn.Linear(120,84)
        # 第九步：输出层
        self.output = nn.Linear(84,10)

    def forward(self,x):
        # 数据的前项传输函数
        x = self.Sigmoid(self.c1(x))
        x = self.s2(x)
        x = self.Sigmoid(self.c3(x))
        x = self.s4(x)
        x = self.c5(x)
        x = self.flatten(x)
        x = self.f6(x)
        x = self.output(x)
        return x

# 程序入口
if __name__ == "__main__":
    # 随机生成一张假图片，1张图、灰度图、Minst尺寸
    x = torch.rand([1, 1, 28, 28])
    model = MyLeNet()
    y = model(x)







