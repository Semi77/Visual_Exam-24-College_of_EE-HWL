import numpy as np
import cv2 as cv

# 1、读取图像
img = cv.imread("test2.png")

# 2、BGR转HSV
hsv = cv.cvtColor(img, cv.COLOR_BGR2HSV)

# 3、红色阈值范围
lower_red1 = np.array([0, 160, 140])
upper_red1 = np.array([10, 255, 255])

lower_red2 = np.array([170, 160, 140])
upper_red2 = np.array([180, 255, 255])

# 4、阈值分割
mask1 = cv.inRange(hsv, lower_red1, upper_red1)
mask2 = cv.inRange(hsv, lower_red2, upper_red2)
mask = mask1 + mask2

# 5、滤波去噪（去掉毛刺考虑中值滤波）
mask_blur = cv.medianBlur(mask, 5)

# 6、形态学处理，建立一个3*3的结构元，然后先开后闭去毛刺
kernel = np.ones((3, 3), np.uint8)
mask_open = cv.morphologyEx(mask_blur, cv.MORPH_OPEN, kernel)
mask_clean = cv.morphologyEx(mask_open, cv.MORPH_CLOSE, kernel)

# 7、Canny边缘提取
edge = cv.Canny(mask_clean, 50, 150)

# 8、定义边缘的结构元，然后对边缘进行膨胀操作
kernel_edge = np.ones((3, 3), np.uint8)
edge = cv.dilate(edge, kernel_edge, iterations=1)

# 9、将提取完的边缘转换为三通道图像，并将边缘改为淡蓝色
result = cv.cvtColor(mask_clean, cv.COLOR_GRAY2BGR)
result[edge != 0] = (255, 205, 0)

# 10、统一显示尺寸为1280×720，并展示图片
img_show = cv.resize(img, (1280, 720))
mask_show = cv.resize(mask_clean, (1280, 720))
result_show = cv.resize(result, (1280, 720))

cv.imshow("img", img_show)
cv.imshow("mask", mask_show)
cv.imshow("result", result_show)

cv.waitKey(0)
cv.destroyAllWindows()

# 11、保存结果图
cv.imwrite("result.png", result)