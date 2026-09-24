"""Per-user display preferences, separate from map data."""
import json
import os
from pathlib import Path


class EditorSettings:
    def __init__(self, path=None):
        self.path = Path(path) if path else Path(os.environ.get('APPDATA', str(Path.home()))) / 'SHCDEMapEditor/settings.json'
        self.values = {'castle_area_opacity': 25, 'show_castle_areas': True,
                       'hide_high_height_warning': False, 'hide_low_height_warning': False}
        if self.path.exists():
            try:
                data = json.loads(self.path.read_text(encoding='utf-8'))
                if isinstance(data, dict):
                    self.values.update(data)
            except (ValueError, OSError):
                pass
        opacity = self.values['castle_area_opacity']
        if type(opacity) is not int or not 0 <= opacity <= 100:
            self.values['castle_area_opacity'] = 25
        if type(self.values['show_castle_areas']) is not bool:
            self.values['show_castle_areas'] = True
        if type(self.values['hide_high_height_warning']) is not bool:
            self.values['hide_high_height_warning'] = False
        if type(self.values['hide_low_height_warning']) is not bool:
            self.values['hide_low_height_warning'] = False
        if not self.path.exists():
            self.save()

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix('.json.tmp')
        temporary.write_text(json.dumps(self.values, indent=2), encoding='utf-8')
        temporary.replace(self.path)
