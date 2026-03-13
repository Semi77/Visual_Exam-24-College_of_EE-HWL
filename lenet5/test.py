import torch
from net import MyLeNet
from torchvision.transforms import ToPILImage
from torchvision import datasets,transforms

# 数据转化为tensor格式
data_transform = transforms.Compose([
    transforms.ToTensor()
])

# 加载测试的数据集
test_dataset = datasets.MNIST(root='./data',train=False,transform=data_transform,download=True)
test_dataloader = torch.utils.data.DataLoader(dataset=test_dataset, batch_size=64,shuffle=False)

# 将数据转到GPU
device = "cuda" if torch.cuda.is_available() else "cpu"

# 调用之前搭建好的网络模型，将模型数据转到GPU上
model = MyLeNet().to(device)

model.load_state_dict(torch.load("C:/Users/28478/Desktop/letnet5/save_model/best_model.pth"))

# 获取结果
classes = ["0","1","2","3","4","5","6","7","8","9"]

# 将Tensor转化为图片，方便可视化
show = ToPILImage()
model.eval()

# 进入验证
for i in range(20):
    x,y = test_dataset[i][0],test_dataset[i][1]
    show(x).show(y)
    x = torch.unsqueeze(x,dim=0).to(device)

    with torch.no_grad():
        pred = model(x)
        predicted,actual =  classes[torch.argmax(pred[0])],classes[y]

        print(f'predicted:"{predicted}",actual:"{actual}"')


