"""Storage geometry; square cells, horizontal/vertical axes, diamond footprint."""
import numpy as np
from semantics import ROW_COUNTS, ROW_STARTS, tile_index, tile_xy


class MapGeometry:
    count = 320800
    axis = 800
    x = np.concatenate([np.arange((800-n)//2, (800+n)//2) for n in ROW_COUNTS])
    y = np.repeat(np.arange(800), ROW_COUNTS)
    index_grid = np.full((800,800), -1, dtype=np.int32)
    index_grid[y,x] = np.arange(count)

    def __init__(self, logic, map_size=500):
        self.max_brush_size = min(800, map_size)
        self.playable = (logic & 0x30) == 0
        ids = np.flatnonzero(self.playable)
        if not len(ids):
            raise ValueError('Map has no playable cells')
        self.bounds = (int(self.x[ids].min()), int(self.y[ids].min()),
                       int(self.x[ids].max())+1, int(self.y[ids].max())+1)

    index = staticmethod(tile_index)
    xy = staticmethod(tile_xy)

    def symmetric_indices(self, indices, horizontal=False, vertical=False):
        """Reflect cell footprints around playable bounds, not brush anchors."""
        ids=np.unique(np.asarray(indices,dtype=np.int64))
        if np.any(ids<0) or np.any(ids>=self.count): raise ValueError('Invalid symmetry cells')
        if not horizontal and not vertical: return ids
        x0,y0,x1,y1=self.bounds
        xs=[self.x[ids]]; ys=[self.y[ids]]
        if vertical: xs.append(x0+x1-1-self.x[ids])
        if horizontal: ys.append(y0+y1-1-self.y[ids])
        reflected=[]
        for x in xs:
            for y in ys:
                inside=(x>=0)&(x<800)&(y>=0)&(y<800)
                values=self.index_grid[y[inside],x[inside]]
                values=values[values>=0]
                reflected.append(values[self.playable[values]])
        return np.unique(np.concatenate(reflected))

    def rectangle(self, x, y, width, height):
        if width < 1 or height < 1 or width > 800 or height > 800:
            raise ValueError('Rectangle dimensions must be 1..800')
        if any(type(v) not in (int, np.int32, np.int64) for v in (x,y,width,height)):
            raise ValueError('Rectangle coordinates and dimensions must be integers')
        x0,y0,x1,y1=max(0,x),max(0,y),min(800,x+width),min(800,y+height)
        if x1<=x0 or y1<=y0:
            return np.empty(0,dtype=np.int64)
        ids=self.index_grid[y0:y1,x0:x1].ravel()
        return ids[ids>=0]

    def brush(self, x, y, size, shape='square'):
        if not 1 <= size <= self.max_brush_size:
            raise ValueError('Brush size must be 1..%s' % self.max_brush_size)
        if shape not in ('square', 'circle'):
            raise ValueError('Unknown brush shape')
        left, top = x-size//2, y-size//2
        ids = self.rectangle(left, top, size, size)
        if shape == 'circle':
            cx, cy = left+(size-1)/2, top+(size-1)/2
            ids = ids[(self.x[ids]-cx)**2+(self.y[ids]-cy)**2 <= (size/2)**2]
        return ids

    def stroke_brush(self, start, end, size, shape='square'):
        """Union of integer-interpolated brush footprints, batched by row."""
        if not isinstance(size, int) or not 1 <= size <= self.max_brush_size:
            raise ValueError('Brush size exceeds map limit')
        if shape not in ('square','circle'):
            raise ValueError('Unknown brush shape')
        steps=max(abs(end[0]-start[0]),abs(end[1]-start[1]),1)
        cx=np.rint(np.linspace(start[0],end[0],steps+1)).astype(int)
        cy=np.rint(np.linspace(start[1],end[1],steps+1)).astype(int)
        left=cx-size//2
        top=cy-size//2
        rows=np.arange(max(0,int(top.min())),min(800,int(top.max())+size))
        if not len(rows):
            return np.empty(0,dtype=np.int64)
        active=(rows[:,None]>=top)&(rows[:,None]<top+size)
        if shape=='circle':
            mx=left+(size-1)/2
            my=top+(size-1)/2
            radicand=(size/2)**2-(rows[:,None]-my)**2
            active &= radicand>=0
            radius=np.sqrt(np.maximum(0,radicand))
            lows=np.maximum(left,np.ceil(mx-radius)).astype(int)
            highs=np.minimum(left+size-1,np.floor(mx+radius)).astype(int)
        else:
            lows=np.broadcast_to(left,active.shape)
            highs=lows+size-1
        low=np.min(np.where(active,lows,801),axis=1)
        high=np.max(np.where(active,highs,-1),axis=1)
        cols=np.arange(800)
        chosen=(cols>=low[:,None])&(cols<=high[:,None])
        ids=self.index_grid[rows][chosen]
        return ids[ids>=0]

    def clip_indices(self, indices, rectangle):
        if rectangle is None:
            return indices
        x,y,w,h=rectangle
        return indices[(self.x[indices]>=x)&(self.x[indices]<x+w)&
                       (self.y[indices]>=y)&(self.y[indices]<y+h)]
