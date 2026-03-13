#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/string.hpp"
#include "sensor_msgs/msg/image.hpp"
#include "cv_bridge/cv_bridge.h"
#include "std_msgs/msg/header.hpp"
#include <opencv2/opencv.hpp>
#include <chrono>
#include <string>

using namespace std::chrono_literals;

class MultiPublisher : public rclcpp::Node
{
public:
    MultiPublisher() : Node("multi_publisher"), count_(0)
    {
        // 1. 声明参数
        this->declare_parameter("person_name", "HWL");
        this->declare_parameter("person_age", 19);

        // 2. 创建字符串发布器
        text_publisher_ = this->create_publisher<std_msgs::msg::String>("chat_text", 10);

        // 3. 创建图像发布器
        image_publisher_ = this->create_publisher<sensor_msgs::msg::Image>("image_topic", 10);

        // 4. 设置测试图片路径
        image_path_ = "test.jpg";

        // 5. 定时器：每秒同时发布字符串和图像
        timer_ = this->create_wall_timer(
            1s,
            std::bind(&MultiPublisher::timer_callback, this));
    }

private:
    void timer_callback()
    {
        // 读取参数
        std::string name = this->get_parameter("person_name").as_string();
        int age = this->get_parameter("person_age").as_int();

        // ---------- 发布字符串 ----------
        std_msgs::msg::String text_msg;
        text_msg.data = "Hello ROS2! name=" + name +
                        ", age=" + std::to_string(age) +
                        ", count=" + std::to_string(count_++);

        text_publisher_->publish(text_msg);

        RCLCPP_INFO(this->get_logger(), "Published text: %s", text_msg.data.c_str());

        // ---------- 发布图像 ----------
        cv::Mat image = cv::imread(image_path_);

        if (image.empty())
        {
            RCLCPP_ERROR(this->get_logger(), "Failed to read image: %s", image_path_.c_str());
            return;
        }

        auto image_msg = cv_bridge::CvImage(
            std_msgs::msg::Header(),
            "bgr8",
            image
        ).toImageMsg();

        image_publisher_->publish(*image_msg);

        RCLCPP_INFO(this->get_logger(), "Published image: %s", image_path_.c_str());
    }

    rclcpp::Publisher<std_msgs::msg::String>::SharedPtr text_publisher_;
    rclcpp::Publisher<sensor_msgs::msg::Image>::SharedPtr image_publisher_;
    rclcpp::TimerBase::SharedPtr timer_;

    std::string image_path_;
    int count_;
};

int main(int argc, char * argv[])
{
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<MultiPublisher>());
    rclcpp::shutdown();
    return 0;
}