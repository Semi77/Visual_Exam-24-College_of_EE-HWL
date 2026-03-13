#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/string.hpp"
#include "sensor_msgs/msg/image.hpp"
#include "cv_bridge/cv_bridge.h"
#include <opencv2/opencv.hpp>
#include <string>

class MultiSubscriber : public rclcpp::Node
{
public:
    MultiSubscriber() : Node("multi_subscriber")
    {
        // 1. 订阅字符串话题
        text_subscription_ = this->create_subscription<std_msgs::msg::String>(
            "chat_text",
            10,
            std::bind(&MultiSubscriber::text_callback, this, std::placeholders::_1));

        // 2. 订阅图像话题
        image_subscription_ = this->create_subscription<sensor_msgs::msg::Image>(
            "image_topic",
            10,
            std::bind(&MultiSubscriber::image_callback, this, std::placeholders::_1));
    }

private:
    void text_callback(const std_msgs::msg::String::SharedPtr msg) const
    {
        // 转回原始类型 std::string
        std::string text = msg->data;

        // 可视化：终端输出
        RCLCPP_INFO(this->get_logger(), "Received text: %s", text.c_str());
    }

    void image_callback(const sensor_msgs::msg::Image::SharedPtr msg) const
    {
        try
        {
            // 转回原始类型 cv::Mat
            cv::Mat image = cv_bridge::toCvCopy(msg, "bgr8")->image;

            // 可视化：OpenCV 显示图像
            cv::imshow("Received Image", image);
            cv::waitKey(1);

            RCLCPP_INFO(this->get_logger(), "Received and displayed image.");
        }
        catch (const cv_bridge::Exception & e)
        {
            RCLCPP_ERROR(this->get_logger(), "cv_bridge exception: %s", e.what());
        }
    }

    rclcpp::Subscription<std_msgs::msg::String>::SharedPtr text_subscription_;
    rclcpp::Subscription<sensor_msgs::msg::Image>::SharedPtr image_subscription_;
};

int main(int argc, char * argv[])
{
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<MultiSubscriber>());
    cv::destroyAllWindows();
    rclcpp::shutdown();
    return 0;
}