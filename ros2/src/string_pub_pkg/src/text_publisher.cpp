#include "rclcpp/rclcpp.hpp"
#include "std_msgs/msg/string.hpp"
#include <chrono>
#include <string>

using namespace std::chrono_literals;

// 定义一个自己的节点类，它拥有 ROS2 节点的能力
class TextPublisher : public rclcpp::Node
{
public:
    TextPublisher() : Node("text_publisher"), count_(0)
    {
        // 创建 Publisher
        publisher_ = this->create_publisher<std_msgs::msg::String>("chat_text", 10);

        // 创建定时器
        timer_ = this->create_wall_timer(
            1s,
            std::bind(&TextPublisher::timer_callback, this));
    }

private:
    void timer_callback()
    {
        std_msgs::msg::String msg;
        msg.data = "Hello ROS2 message " + std::to_string(count_++);

        RCLCPP_INFO(this->get_logger(), "Publishing: %s", msg.data.c_str());
        publisher_->publish(msg);
    }

    rclcpp::Publisher<std_msgs::msg::String>::SharedPtr publisher_;
    rclcpp::TimerBase::SharedPtr timer_;
    int count_;
};

int main(int argc, char * argv[])
{
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<TextPublisher>());
    rclcpp::shutdown();
    return 0;
}