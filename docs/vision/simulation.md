# Simulation

The BaseCamera class has support for integrating with a [Simulation Framework WindowView](../sim/windowview.md)

!!! Info
    See [Extending BaseCamera](extend-basecamera.md)

## Simulation Window

![camera.png](../media/windowview/camera.png)

The Simulation Window consists of a tab for each of the robot's cameras.
Each tab will have independent resolution and frame rates, according to the robot configuration.

Upon initializing the camera simulator, an ephemeral TCP port will be assigned to an internal ZeroMQ server/client for IPC.

!!! Info
    The internal ZeroMQ server uses CURVE encryption based on a differing random key.
    It is currently not possible to get video frames outside the KevinbotLib robot.

### Video Sources

Each simulated camera can connect to a physically connected camera using camera passthrough, or an uploaded image file.

!!! Note
    Camera passthrough is experimental on macOS

!!! Warning
    A physical camera can only connect to one simulated camera, since connections aren't pooled.

### Image Upload

Image upload can be used in the "Uploaded Image" video source.

Pressing the image upload button will display a file chooser to select an image.

!!! Info
    Only PNG, JPG, JPEG, and BMP images are supported

After an image is uploaded, you may select a crop mode.

![camera-editor.png](../media/windowview/camera-editor.png){ width=300px; }