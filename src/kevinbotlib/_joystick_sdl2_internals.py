from queue import Queue

import sdl2
import sdl2.ext

_sdl2_event_dispatcher: "_InternalSdl2EventDispatcher | None" = None


class _InternalSdl2EventDispatcher:
    def __init__(self) -> None:
        self.queues: dict[int, Queue[sdl2.events.SDL_Event]] = {}

    def iterate(self):
        events: list[sdl2.events.SDL_Event] = sdl2.ext.get_events()
        event: sdl2.events.SDL_Event
        for event in events:
            if event.type in (
                sdl2.SDL_JOYAXISMOTION,
                sdl2.SDL_JOYBUTTONDOWN,
                sdl2.SDL_JOYBUTTONUP,
                sdl2.SDL_JOYHATMOTION,
                sdl2.SDL_JOYDEVICEADDED,
                sdl2.SDL_JOYDEVICEREMOVED,
            ):
                joyid: int = event.jdevice.which
                if joyid not in self.queues:
                    self.queues[joyid] = Queue()
                self.queues[joyid].put(event)

    def get(self, index: int):
        items: list[sdl2.events.SDL_Event] = []
        if index not in self.queues:
            return items
        while not self.queues[index].empty():
            items.append(self.queues[index].get())
        return items


def dispatcher():
    global _sdl2_event_dispatcher  # noqa: PLW0603
    if _sdl2_event_dispatcher:
        return _sdl2_event_dispatcher
    _sdl2_event_dispatcher = _InternalSdl2EventDispatcher()
    return _sdl2_event_dispatcher
