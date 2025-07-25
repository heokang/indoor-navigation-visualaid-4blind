# Indoor Navigation App for the Visually Impaired

This project aims to develop a mobile navigation application that helps visually impaired users independently navigate indoor environments such as shopping malls, where GPS signals are unavailable.

🔍 Key Features:
Image-based Positioning
Using computer vision models (YOLOv5, Mask R-CNN), the app estimates the user's indoor location by detecting static objects and calculating distance via triangulation.

Turn-Minimizing Pathfinding
A custom algorithm (TFT*: Theta Fewer Turns) is developed to reduce the number of turns in navigation, minimizing cognitive load for visually impaired users.

Sensor-Based Real-Time Guidance
Using accelerometer and magnetometer data, the app provides step detection, heading correction (Kalman Filter), and personalized voice instructions based on the user’s walking speed and direction.

NOTE: This project is a prototype created for learning purposes.
