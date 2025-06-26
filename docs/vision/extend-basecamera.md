# Extending BaseCamera

When creating a custom camera, the simulator must always be initialized after your camera instantiation.
Failure to do so may result in a broken [Simulator WindowView](simulation.md#simulation-window)

## Basic Example

```python
from kevinbotlib.vision import BaseCamera
from kevinbotlib.robot import BaseRobot
from cv2.typing import MatLike

class CustomCamera(BaseCamera):
    def __init__(self, robot: BaseRobot | None = None):
        super().__init__(robot)
        
        # your camera init here
        if not self.simulated:
            ...
        
        self.__init_sim__("My Awesome Camera Name") # Initialize the camera simulator - name must be unique

    def get_frame(self) -> tuple[bool, MatLike]:
        if not self.simulated:
            # return your camera frame here along with a success flag
            ...
        else:
            return self._sim_frame # return the simulator frame here

    def set_resolution(self, width: int, height: int) -> None:
        super().set_resolution(width, height)
        # set your camera resolution here
```