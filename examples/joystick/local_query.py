import sys
import time
from multiprocessing.spawn import freeze_support

import sdl2
import sdl2.ext


def main():
    # Initialize SDL2
    if sdl2.SDL_Init(sdl2.SDL_INIT_VIDEO | sdl2.SDL_INIT_GAMECONTROLLER) != 0:
        print(f"SDL2 initialization failed: {sdl2.SDL_GetError().decode()}")
        return 1

    # Check for game controllers
    num_joysticks = sdl2.SDL_NumJoysticks()
    print(f"Found {num_joysticks} joystick(s)")

    controllers = []
    for i in range(num_joysticks):
        if sdl2.SDL_IsGameController(i):
            controller = sdl2.SDL_GameControllerOpen(i)
            if controller:
                name = sdl2.SDL_GameControllerName(controller)
                print(f"Opened controller {i}: {name.decode() if name else 'Unknown'}")
                controllers.append(controller)
            else:
                print(f"Failed to open controller {i}")

    if not controllers:
        print("No game controllers found! Connect a controller and restart.")

    # Main loop
    running = True
    event = sdl2.SDL_Event()

    while running:
        while sdl2.SDL_PollEvent(event):
            if event.type == sdl2.SDL_QUIT:
                running = False

            elif event.type == sdl2.SDL_CONTROLLERBUTTONDOWN:
                button = event.cbutton.button
                print(f"Button pressed: {button}")

                # Exit on START button
                if button == sdl2.SDL_CONTROLLER_BUTTON_START:
                    running = False

            elif event.type == sdl2.SDL_CONTROLLERBUTTONUP:
                button = event.cbutton.button
                print(f"Button released: {button}")

            elif event.type == sdl2.SDL_CONTROLLERAXISMOTION:
                axis = event.caxis.axis
                value = event.caxis.value

                # Normalize axis values (-32768 to 32767) to -1.0 to 1.0
                normalized_value = value / 32767.0
                print(f"{axis}: {normalized_value:.2f}")

            elif event.type == sdl2.SDL_CONTROLLERDEVICEADDED:
                device_index = event.cdevice.which
                if sdl2.SDL_IsGameController(device_index):
                    controller = sdl2.SDL_GameControllerOpen(device_index)
                    if controller:
                        name = sdl2.SDL_GameControllerName(controller)
                        print(f"Controller connected: {name.decode() if name else 'Unknown'}")
                        controllers.append(controller)

            elif event.type == sdl2.SDL_CONTROLLERDEVICEREMOVED:
                print("Controller disconnected")

        # Small delay to prevent excessive CPU usage
        time.sleep(0.016)  # ~60 FPS
    return None


if __name__ == "__main__":
    freeze_support()
    sys.exit(main())
