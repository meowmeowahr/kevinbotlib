# User Interface

## Status Bar

The dashboard bottom status bar shows the connection state, e.g. `Robot Connected` or `Robot Disconnected`, IP Address, and the round-trip latency.

![dashboard-bar.png](../../media/dashboard-bar.png)

## Widget Grid

The widget grid supports dragging-and-dropping widgets. An unsuccessful drag (indicated by a red highlight) will cause the widget to snap back to its original spot.

Widgets can be resized by dragging their bottom right corner.

![dashboard-grid.gif](../../media/dashboard-grid.gif)

## Sidebar

The sidebar can be resized or hidden entirely by dragging the splitter.

![dashboard-split.gif](../../media/dashboard-split.gif)

### Data Tree

The data tree will show all Sendable keys on the network that contain a valid structure.
Key groups are separated with a forward slash.
Selecting a key will display it in the [Sendable Viewer](#sendable-viewer)

![dashboard-tree.gif](../../media/dashboard-tree.gif){width=220px}

### Sendable Viewer

The sendable viewer can preview data before adding a widget to the grid.
The viewer also contains a raw view that allows you to see the raw JSON data of the Sendable.

Clicking on a widget type will add the widget to the grid if a slot is available.

![dashboard-sendable.gif](../../media/dashboard-sendable.gif){width=380px}

## Log Viewer

The log viewer can be used to diagnose issues with KevinbotLib Dashboard.
The log viewer is limited to 100 lines before removing the oldest line.

Click on the "Dashboard Logs" button to expand/collapse it.

![dashboard-logs.png](../../media/dashboard-logs.png)

!!! Note
    The dashboard log viewer will not display any robot logs. Only log messages generated internally by KevinbotLib Dashboard