#include<iostream>
#include<cmath>
using namespace std;

// 定义Rect结构体，
struct Rect 
{
    int id;         // 数字ID(1-6)
    int color;      // 装甲板颜色(蓝色为0、红色为1)
    float x;        // 坐标x
    float y;        // 坐标y
    float width;    // 宽度
    float height;   // 高度
};

// 定义点类
class Point 
{
public:
    float x; // x坐标
    float y; // y坐标

    // 构造函数，初始化点的坐标
    Point(float x = 0, float y = 0) : x(x), y(y) {}
};

// 定义Armor类
class Armor 
{
public:
    // 接收Rect结构体对象的构造函数
    Armor(const Rect& rect) : rect(rect) {}

    // 计算中心坐标
    Point Central_Point()
    {
        return Point(rect.x + rect.width / 2, rect.y + rect.height / 2);
    }

    // 计算对角线长度
    float Diagonal_Length()
    {
        return sqrt(rect.width * rect.width + rect.height * rect.height);
    }

    // 获取装甲板4点坐标,从左上角坐标开始顺时针输出
    void Get_Corner_Points(Point points[4])
    {
        points[0] = Point(rect.x, rect.y);                              // 左上角
        points[1] = Point(rect.x + rect.width, rect.y);                 // 右上角
        points[2] = Point(rect.x + rect.width, rect.y + rect.height);   // 右下角
        points[3] = Point(rect.x, rect.y + rect.height);                // 左下角
    }

    // 输出装甲板颜色
    int Get_Color() 
    {
        return rect.color;
    }
private:
    Rect rect;
};


int main()
{
    // 创建Rect对象并输入数据
    Rect rect;
    cin >> rect.id >> rect.color;
    cin >> rect.x >> rect.y >> rect.width >> rect.height;

    // 创建Armor对象，接收结构体数据并进行计算
    Armor armor(rect);

    // 调用成员函数计算中心点
    Point center = armor.Central_Point();

    // 调用成员函数计算对角线长度
    float diagonal = armor.Diagonal_Length();

    // 定义数组来存放四点坐标
    Point corners[4];

    // 调用成员函数来计算四点坐标
    armor.Get_Corner_Points(corners);

    // 输出结果
    cout << "ID: " << rect.id << " 颜色: " << (rect.color == 0 ? "蓝" : "红") << endl;

    cout << "(" << center.x << ", " << center.y << ")" << " 长度: " << diagonal << endl;

    for (int i = 0; i < 4; i++) 
    {
        cout << "(" << corners[i].x << ", " << corners[i].y << ")";
        if(i<3)
        {
            cout << " ";
        }
    }
    cout << endl;

    system("pause");
    return 0;
}
