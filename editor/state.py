"""Transient editor choices, independent of Qt and map data."""
from dataclasses import dataclass, asdict
from .services import MATERIALS


@dataclass
class EditorState:
    tool: str = 'Paint'
    material: str = 'oasis'
    brush_shape: str = 'square'
    brush_size: int = 5
    height: int = 8
    variation: int = 0
    uniform_variation: bool = False
    mask_path: str = ''
    rotation: int = 0
    mirror: bool = False
    mask_invert: bool = False
    mask_tag: str = ''
    symmetry_horizontal: bool = False
    symmetry_vertical: bool = False

    @classmethod
    def restore(cls, values):
        state = cls()
        for key, value in values.items():
            if key in asdict(state) and type(value) is type(getattr(state, key)):
                setattr(state, key, value)
        state.tool = 'Paint'
        if state.material not in MATERIALS:
            state.material = 'oasis'
        if state.brush_shape not in ('square','circle','mask'):
            state.brush_shape = 'square'
        state.brush_size = max(1,min(500,state.brush_size))
        # Start each session at ordinary ground, never a previous risky target.
        state.height=8
        state.variation=max(0,min(65535,state.variation))
        state.rotation = state.rotation % 360 if state.rotation % 90 == 0 else 0
        return state

    def preferences(self):
        data = asdict(self)
        data.pop('tool')
        data['height']=8
        return data
