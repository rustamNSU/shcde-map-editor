"""Vectorized schematic rendering shared by GUI and tests; no Qt dependency."""
import numpy as np
from .services import MATERIALS, EntityService
from .castle_areas import CASTLE_AREA_RADIUS, castle_parts, existing_clear_indices


# shcde-stats-rust: src/engine/enums.rs PlayerColor, ui/app.slint swatches.
PLAYER_COLORS = [tuple(bytes.fromhex(c)) for c in
                 ('df3b30','f28c28','f2d447','3b6eea','1d2430','8e44d7','58c7e8','33a852')]

# Fixed jet scale: values never depend on the current map's minimum/maximum.
HEIGHT_COLORS=np.array([np.interp(np.arange(256),[0,32,96,160,224,255],channel)
    for channel in ([0,0,0,255,255,128],[0,0,255,255,0,0],[128,255,255,0,0,0])],dtype=np.uint8).T.copy()


def render_rgb(document, layer='surface', objects=True, players=True, area_opacity=25,
               *, terrain_rewrite=False):
    d = document
    image = np.full((800, 800, 3), (24, 30, 35), dtype=np.uint8)
    colors = np.full((d.geometry.count, 3), (188, 167, 117), dtype=np.uint8)
    if layer == 'height':
        colors=HEIGHT_COLORS[d.grid(3005)].copy()
    elif layer == 'noise':
        # Display the full uint16 storage range; never normalize per map.
        grey=(d.grid(3008).astype(np.uint32)*255//65535).astype(np.uint8)
        colors=np.repeat(grey[:,None],3,axis=1)
    else:
        surface, logic = d.grid(3037), d.grid(3003)
        for name, (value, color) in MATERIALS.items():
            if name in ('stone', 'iron', 'marsh', 'sea', 'river', 'ford', 'pitch', 'moat', 'rocks'):
                continue
            colors[surface == value] = tuple(bytes.fromhex(color[1:]))
        for bit, rgb in [(7,(116,113,107)), (17, (173,181,189)), (19,(149,103,83)),
                         (29,(92,118,99)), (20,(69,125,151)), (21,(113,159,166)),
                         (0,(49,94,125)), (30,(57,85,102)), (31,(70,55,67)),
                         (8,(171,157,137))]:
            colors[(logic & (1 << bit)) != 0] = rgb
    colors[~d.geometry.playable] = (31, 40, 44)
    image[d.geometry.y, d.geometry.x] = colors
    mask = np.zeros((800, 800), dtype=bool)
    mask[d.geometry.y, d.geometry.x] = d.geometry.playable
    edge = mask & ~(np.roll(mask,1,0) & np.roll(mask,-1,0) & np.roll(mask,1,1) & np.roll(mask,-1,1))
    image[edge] = (215,184,107)
    if layer in ('height','noise'):
        return image  # Keep data colors accurate; no castle tint or object recoloring.
    castles = list(castle_parts(d))
    if players and d.size in CASTLE_AREA_RADIUS:
        radius = CASTLE_AREA_RADIUS[d.size]
        alpha = max(0,min(100,area_opacity))/100
        for owner, parts, center in castles:
            if center is None:
                continue
            x,y = center
            region = np.zeros_like(mask)
            region[max(0,y-radius):min(800,y+radius+1),max(0,x-radius):min(800,x+radius+1)] = True
            region &= mask & ~edge
            image[region] = np.rint(image[region]*(1-alpha)+np.array(PLAYER_COLORS[owner-1])*alpha).astype(np.uint8)
    if objects:
        for sid, color in [(3004,(52,94,61)),(3012,(203,163,103))]:
            ids = np.flatnonzero((d.grid(sid) != 0) & d.geometry.playable)
            image[d.geometry.y[ids],d.geometry.x[ids]] = color
        for unit in EntityService(d).records('units'):
            if unit['coordinates_match']:
                image[unit['y'], unit['x']] = (104,192,205) if unit['hp_candidate'] else (109,101,111)
    if terrain_rewrite:
        ids = existing_clear_indices(d)
        yy,xx = d.geometry.y[ids],d.geometry.x[ids]
        image[yy,xx] = np.rint(image[yy,xx]*0.5+np.array((255,177,45))*0.5).astype(np.uint8)
    # Solid castle footprints remain visible independently of the area toggle.
    for owner, parts, center in castles:
        for b in parts:
            x,y = b['x'],b['y']
            side = b.get('footprint_size',7) if b['type'] in set(range(40,45)) | {55} else 1
            region = np.zeros_like(mask)
            region[max(0,y):min(800,y+side),max(0,x):min(800,x+side)] = True
            image[region & mask] = PLAYER_COLORS[owner-1]
    return image
