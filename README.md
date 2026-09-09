# Warband Map & Party Editor

A lightweight visual editor for *Mount & Blade: Warband* overworld maps (`map.txt`) and parties (`parties.txt`).

Compatible with Native and various community modules (e.g., 1257 AD, 1815, Custom/Naval mods).

## Features

- **Mesh Rendering**: Direct parsing and rendering of `map.txt` vertices and faces.
- **Terrain Types**: Supports all 16 engine terrain types, including deep ocean.
- **Editing Tools**:
  - **Party Positioning**: Select and reposition settlements and spawns directly on the map.
  - **Brush**: Multi-radius terrain painting with spatial indexing.
  - **Fill**: Topology-based flood fill for connected terrain regions.
  - **Picker**: Sample terrain material directly from mesh faces.
  - **Pan & Zoom**: Smooth canvas navigation and viewport reset.
- **Undo / Redo**: Operation history stack (`Ctrl+Z` / `Ctrl+Y`).
- **File Safety**: In-place updates for `map.txt` and `parties.txt` preserving original structure and encodings.
- **Export**: Render and export the current map view to PNG or JPG.

## Requirements

- Python 3.8+
- PyQt5

```bash
pip install PyQt5
python3 map_editor.py
```

## Controls & Shortcuts

| Action | Shortcut |
|---|---|
| Pan | Right-click drag |
| Zoom | Scroll wheel |
| Save (`map.txt` & `parties.txt`) | `Ctrl + S` |
| Undo | `Ctrl + Z` |
| Redo | `Ctrl + Y` |
| Export Image | `Ctrl + Shift + E` |
| Reset View | `Ctrl + 0` / Reset button |
