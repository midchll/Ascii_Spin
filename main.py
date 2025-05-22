'''
Image to 3D rotating ascii conversion. This script outputs
    created frames to JSON to be rendered by a secondary program.
Author: Mitchell Deevers
'''

from os import listdir
from PIL import Image
import math
import json

# Source image directory
IMGDIR = 'test_images'
# Input image index in image directory
IMGINDEX = 1
# Color selection, 1 for black, 0 for white
SELECTION = 1
# Number tiles in img width
DIM = 100
# 3D image thickness
DEPTH = 11
# Number of frames in 360*
FRAMECOUNT = 50
# Path to JSON file to store frames
JSONPATH = "ascii_frames.json"

def get_ascii(img_index, select_black=1, dim=100):
    '''
    Standard image to ASCII conversion. Image disection and character assignment
    based on target color density.
    '''
    img = Image.open(f'{IMGDIR}/{listdir('test_images')[img_index]}')
    # Paste image over b/w background to eliminate transparency
    if img.mode == "RGBA":
        bg = Image.new("RGBA", img.size, "WHITE") if select_black \
            else Image.new("RGBA", img.size, "BLACK")
        img = Image.alpha_composite(bg, img)
        img = img.convert("RGB")
        
    # Resizing minimally for nxn tiling, dim = num divisions in img width
    tilesize = int(img.size[0] // dim)
    img = img.resize((tilesize * dim, img.size[1] - img.size[1] % tilesize), resample=Image.BILINEAR)   
    
    print(f"Final IMG size: {img.size}\nTILESIZE: {tilesize}\n")
    
    # Store image section densities
    ascii_2d = []
    for top in range(img.size[1]//tilesize):
        row = []
        for left in range(img.size[0]//tilesize):
            sect = img.crop((left*tilesize, top*tilesize, (left+1)*tilesize, (top+1)*tilesize))
            sel_total = 0
            for i in range(tilesize):
                for j in range(tilesize):
                    rgb = sect.getpixel((i, j))
                    rgb = rgb[0] + rgb[1] + rgb[2]
                    if select_black:
                        sel_total += 1 if rgb <= 90 else 0
                    else:
                        sel_total += 1 if rgb >= 690 else 0
            if sel_total >= math.floor(tilesize * tilesize * 0.9):
                row.append('#')
            else:
                row.append(" ")
        ascii_2d.append(row)
    return ascii_2d

def ascii_to_3d(ascii_2d, depth):
    '''
    Reshape ascii_2d points to voxels, stack on z-axis to specified depth,
    track object-face/back voxels for different ascii assignment in rendering
    Voxel structure = [((x, y, z), is_side), ...]
    '''
    voxels = []
    for z in range(depth):
        for y, row in enumerate(ascii_2d):
            for x, char in enumerate(row):
                if char == '#':
                    is_face = (z == 0 or z == depth - 1)
                    voxels.append(([x, y, z], is_face))
    return voxels

def center_voxels(voxels):
    '''
    Find geometric center of 3d object to offset rotated points each frame.
    Without, object will swing around y-axis and out of frame.
    '''
    x_vals = [v[0][0] for v in voxels]
    y_vals = [v[0][1] for v in voxels]
    z_vals = [v[0][2] for v in voxels]
    # Find  midpoint of each axis
    mid_x = (max(x_vals) + min(x_vals)) / 2
    mid_y = (max(y_vals) + min(y_vals)) / 2
    mid_z = (max(z_vals) + min(z_vals)) / 2
    return mid_x, mid_y, mid_z

def rotate_y(point, angle):
    '''
    Rotate voxels around y-axis.
        [x']   [cosΘ    0    sinΘ]   [x]
        [y'] = [  0     1      0 ] * [y]
        [z']   [-sinΘ   0    cosΘ]   [z]
    '''
    x, y, z = point
    cos = math.cos(angle)
    sin = math.sin(angle)
    x_rot = x*cos + z*sin
    z_rot = -x*sin + z*cos
    return [x_rot, y, z_rot]

def project(point, view_distance=250, screen_w=100, screen_h=100):
    '''
    3D -> 2D plane perspective projection for frame rendering. Scale x and
    y values inversely by factor that scales with z (view_distance + z)
    '''
    x, y, z = point
    denom = view_distance + z
    if denom <= 0:
        return None
    factor = view_distance / denom
    x_proj = int(screen_w / 2 + x * factor)
    y_proj = int(screen_h / 2 + y * factor)
    return (x_proj, y_proj)

def render_frame(points, chars, min_x, min_y, w, h, padding=5, depths=None):
    '''
    Return string represented frames of given character array with excess 
    space trimmed from object. String is prepared json.
    '''
    frame = [['.' for _ in range(w)] for _ in range(h)] # 'blank' frame
    zbuffer = [[float('inf') for _ in range(w)] for _ in range(h)] # minimum z val frame
    
    for i, (x, y) in enumerate(points):
        # frame-relative positions
        fx = x - min_x + padding
        fy = y - min_y + padding
        if 0 <= fx < w and 0 <= fy < h:
            # render top-most surface only
            z = depths[i] if depths else 0
            if z < zbuffer[fy][fx]:
                zbuffer[fy][fx] = z
                frame[fy][fx] = chars[i]
    return '\n'.join(''.join(row) for row in frame)

def save_frames_to_json(frames, path):
    '''
    Dump frame strings into json
    '''
    with open(path, 'w') as f:
        json.dump(frames, f)


if __name__ == '__main__':
    ascii = get_ascii(img_index=IMGINDEX, select_black=SELECTION, dim=DIM)    
    voxels = ascii_to_3d(ascii_2d=ascii, depth=DEPTH)
    mid_x, mid_y, mid_z = center_voxels(voxels=voxels)
    
    # Determine frame size with static projection centered around 0,0,0
    project_static = [project(point=[v[0][0] - mid_x, v[0][1] - mid_y, v[0][2] - mid_z]) for v in voxels]
    x_vals, y_vals = zip(*project_static)
    # Calculating 2D bounding box
    min_x, max_x = min(x_vals), max(x_vals)
    min_y, max_y = min(y_vals), max(y_vals)
    frame_width = max_x - min_x + 1 + 10 # Add 1 for inclusive size, extra is padding
    frame_height = max_y - min_y + 1 + 10
    
    frames = []
    
    for i in range(FRAMECOUNT):
        angle = i * (2 * math.pi / FRAMECOUNT)
        rotated = []
        chars = []
        
        # Offsetting voxels by midpoints and picking chars to represent sides 
        for (pos, is_face) in voxels:
            shifted = [pos[0] - mid_x, pos[1] - mid_y, pos[2] - mid_z]
            rot_pos = rotate_y(point=shifted, angle=angle)
            rotated.append(rot_pos)
            chars.append('#' if is_face else '@')
        
        projected = []
        depths = []
        filtered_chars = []
        
        # Projecting each rotated voxel, extract z for depth used in rendering
        for j, p in enumerate(rotated):
            proj = project(point=p)
            if proj is not None:
                projected.append(proj)
                depths.append(p[2])
                filtered_chars.append(chars[j])
                
        frame = render_frame(points=projected, chars=filtered_chars, min_x=min_x, \
                            min_y=min_y, w=frame_width, h=frame_height, padding=5, depths=depths)
        frames.append(frame)
        
    save_frames_to_json(frames=frames, path=JSONPATH)
    print(f"Saved {len(frames)} frames to {JSONPATH}")