# Vision

The KevinbotLib Vision System is a pipeline-based computer vision framework building on top of [OpenCV](https://opencv.org/).

## Cameras

A KevinbotLib Camera will retrieve frames from a connected camera and can set its resolution and frame rate.

KevinbotLib includes two built-in camera connectors, [CameraByIndex](../reference/vision.md#kevinbotlib.vision.CameraByIndex) and [CameraByDevicePath](../reference/vision.md#kevinbotlib.vision.CameraByDevicePath).

### Creating Custom Cameras

Custom camera implementations must extend [BaseCamera](../reference/vision.md#kevinbotlib.vision.BaseCamera) for proper simulation support.
See more info [here](extend-basecamera.md).

## Pipelines

A pipeline will take in camera frames (or another video source), and produce output calculations as well as a frame for visualization.

![vision-pipeline-diagram-dark.svg](../media/vision-pipeline-diagram-dark.svg#only-dark)
![vision-pipeline-diagram-dark.svg](../media/vision-pipeline-diagram-light.svg#only-light)

KevinbotLib includes one basic pipeline, the [EmptyPipeline](../reference/vision.md#kevinbotlib.vision.EmptyPipeline).
The EmptyPipeline will output exactly what is put in.

## Comms, Encoding, and Decoding

The KevinbotLib Vision Systems includes comm sendables and encode/decode support for (M)JPG and PNG

!!! Warning
    The sendables are not activated by default for performance reasons.
    Use the following to activate them before attempting to set/get video data.

    ```python
    from kevinbotlib.vision import VisionCommUtils
    VisionCommUtils.init_comms_types(client)    
    ```

## Examples

### Pipeline

```python title="examples/vision/pipeline.py" linenums="1"
--8<-- "examples/vision/pipeline.py"
```

!!! Note
    The following examples require a running Redis server for RedisCommClient.

### Sending a Video Stream over Redis

```python title="examples/vision/video_sender.py" linenums="1"
--8<-- "examples/vision/video_sender.py"
```

### Receiving a Video Stream over Redis

```python title="examples/vision/video_rx.py" linenums="1"
--8<-- "examples/vision/video_rx.py"
```

## See also

[Vision System Reference](../reference/vision.md)