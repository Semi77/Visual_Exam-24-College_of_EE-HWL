#include "rclcpp/rclcpp.hpp"
#include "sensor_msgs/msg/image.hpp"
#include "cv_bridge/cv_bridge.h"
#include <chrono>
#include <string>
#include <opencv2/opencv.hpp>

using namespace std::chrono_literals;

class ImgPublisher : public rclcpp::Node
{
public:
    ImgPublisher() : Node("Img_publisher")
    {
        // Create Publisher
        publisher_ = this->create_publisher<sensor_msgs::msg::Image>("image_topic",10);

        image_path_ = "test.jpeg";

        timer_ = this->create_wall_timer(1s,std::bind(&ImgPublisher::timer_callback,this));
    }
private:
    // Create timer-callback function
    void timer_callback()
    {
        cv::Mat image = cv::imread(image_path_);
        if(image.empty())
        {
            RCLCPP_ERROR(this->get_logger(), "Failed to read image: %s", image_path_.c_str());
            return;
        }
        auto msg = cv_bridge::CvImage(std_msgs::msg::Header(),"bgr8",image).toImageMsg();

        publisher_->publish(*msg);

        RCLCPP_INFO(this->get_logger(), "Published image: %s", image_path_.c_str());
    }
        rclcpp::Publisher<sensor_msgs::msg::Image>::SharedPtr publisher_;
        rclcpp::TimerBase::SharedPtr timer_;
        std::string image_path_;
};

int main(int argc, char * argv[])
{
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<ImgPublisher>());
    rclcpp::shutdown();
    return 0;
}