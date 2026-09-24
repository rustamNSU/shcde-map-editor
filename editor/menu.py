"""Shared lobby/preview castle positions for supported map sizes."""
from semantics import entity_report, ENTITY_LAYOUTS
from .services import EntityService


def project_keep(size, x, y):
    if size == 400:
        return ((x-y+197)//2, (x+y-598)//2)
    if size == 500:
        # Native500 uses three cells per pixel, not 2.5. Matches Ada exactly;
        # native x raster rounding can differ by one pixel on other maps.
        return ((x-y+301)//3, (x+y-495)//3)
    raise ValueError('Lobby projection supports 400 and 500 maps')


def castle_markers(document):
    """Preserve valid native markers for unchanged keeps; repair missing ones."""
    d=document
    before=entity_report(d.container,ENTITY_LAYOUTS['buildings'])['records']
    old={r['owner']:r for r in before if 40<=r['type']<=44 and 1<=r['owner']<=8}
    stored={r['player']:r for r in d.container.menu_metadata().get('start_markers',[])}
    signature=lambda r:(r['type'],r['x'],r['y'])
    result={}
    for r in EntityService(d).records('buildings'):
        owner=r['owner']
        if not 40<=r['type']<=44 or not 1<=owner<=8: continue
        previous=stored.get(owner)
        if (owner in old and signature(old[owner])==signature(r) and previous
                and previous['present'] and 0<=previous['x']<200 and 0<=previous['y']<200):
            xy=(previous['x'],previous['y'])
        else:
            xy=project_keep(d.size,r['x'],r['y'])
        result[owner]=tuple(max(0,min(199,v)) for v in xy)
    return result
