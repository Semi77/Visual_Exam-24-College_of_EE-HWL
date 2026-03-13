#include "rclcpp/rclcpp.hpp"
#include "sensor_msgs/msg/image.hpp"
#include "cv_bridge/cv_bridge.h"
#include <opencv2/opencv.hpp>

class ImgSubscriber : public rclcpp::Node
{
public:
    ImgSubscriber() : Node("img_subscriber")
    {
        subscription_ = this->create_subscription<sensor_msgs::msg::Image>(
            "image_topic",
            10,
            std::bind(&ImgSubscriber::topic_callback, this, std::placeholders::_1));
    }

private:
    void topic_callback(const sensor_msgs::msg::Image::SharedPtr msg) const
    {
        try
        {
            cv::Mat image = cv_bridge::toCvCopy(msg, "bgr8")->image;

            cv::imshow("Received Image", image);
            cv::waitKey(1);

            RCLCPP_INFO(this->get_logger(), "Received and displayed image.");
        }
        catch (const cv_bridge::Exception & e)
        {
            RCLCPP_ERROR(this->get_logger(), "cv_bridge exception: %s", e.what());
        }
    }

    rclcpp::Subscription<sensor_msgs::msg::Image>::SharedPtr subscription_;
};

int main(int argc, char * argv[])
{
    rclcpp::init(argc, argv);
    rclcpp::spin(std::make_shared<ImgSubscriber>());
    cv::destroyAllWindows();
    rclcpp::shutdown();
    return 0;
}