"""Current-map menu thumbnails in DE's RGB555 palette/index format; no Qt."""
import numpy as np
from PIL import Image,ImageDraw
from .render import render_rgb,PLAYER_COLORS
from .services import EntityService
from .menu import castle_markers

def project(document,x,y):
    # Orthogonal storage diamond becomes the square menu overview.
    scale=1/max(1,(document.size+199)//200)
    return ((x-y)*scale+100,(x+y-799)*scale+100)

def render_preview(document):
    d=document
    from .geometry import SUPPORTED_MAP_SIZES
    if d.size not in SUPPORTED_MAP_SIZES: raise ValueError('Unsupported map size')
    rgb=render_rgb(d,objects=True,players=False)
    heights=np.full((800,800),8,dtype=np.float32)
    heights[d.geometry.y,d.geometry.x]=d.grid(3045)
    # Subtle relief, not the GUI's diagnostic jet colormap.
    dy,dx=np.gradient(heights)
    shade=np.clip(1+(heights-8)*.0015+(dx-dy)*.018,.55,1.3)
    rgb=np.clip(rgb.astype(np.float32)*shade[:,:,None],0,255).astype('uint8')
    v,u=np.indices((200,200),dtype=float)
    step=max(1,(d.size+199)//200)
    x=np.rint(399.5+(u+v-199)*step/2).astype(int)
    y=np.rint(399.5+(v-u)*step/2).astype(int)
    pixels=rgb[y.clip(0,799),x.clip(0,799)].copy()
    if d.size not in (400,500):
        half=d.size/step/2
        inside=(u>=100-half)&(u<100+half)&(v>=100-half)&(v<100+half)
        pixels[~inside]=0
    if d.size==500:
        # Native500 preview footprint verified against Ada:166 pixels square.
        inside=(u>=18)&(u<184)&(v>=17)&(v<183)
        pixels[~inside]=0
    image=Image.fromarray(pixels)
    draw=ImageDraw.Draw(image)
    for r in EntityService(d).records('vegetation'):
        px,py=project(d,r['x'],r['y'])
        if 0<=px<200 and 0<=py<200: draw.point((round(px),round(py)),fill=(43,83,42))
    for owner,(px,py) in castle_markers(d).items():
        if not (0<=px<200 and 0<=py<200):continue
        color=PLAYER_COLORS[owner-1] if 1<=owner<=8 else (220,210,185)
        draw.rectangle((px-2,py-1,px+3,py+3),fill=(60,48,34))
        draw.rectangle((px-2,py-2,px+2,py+2),fill=(237,209,158))
        for xx in (px-2,px,px+2): draw.point((xx,py-3),fill=(237,209,158))
        draw.rectangle((px-1,py,px+1,py+2),fill=color)
        draw.point((px,py+2),fill=(54,41,30))
        draw.line((px+2,py-5,px+2,py-2),fill=(58,43,26))
        draw.line((px+2,py-5,px+4,py-5),fill=color)
    return image

def encode_preview(document):
    image=render_preview(document).quantize(colors=256,method=Image.Quantize.MEDIANCUT,dither=Image.Dither.NONE)
    palette=np.array(image.getpalette(),dtype=np.uint16).reshape(-1,3)
    full=np.zeros((256,3),dtype=np.uint16);full[:len(palette)]=palette
    rgb555=((full[:,0]>>3)<<10)|((full[:,1]>>3)<<5)|(full[:,2]>>3)
    return rgb555.astype('<u2').tobytes()+image.tobytes()
