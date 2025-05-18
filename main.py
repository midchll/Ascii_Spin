from os import listdir
from PIL import Image
import math
import json

def get_ascii(dir_ind, dim=100):
    DIM = dim
    sects = []
    
    test_images = [f"test_images/{f}" for f in listdir('test_images')]
    img = Image.open(test_images[dir_ind])
    if img.mode == "RGBA":
        white_bg = Image.new("RGBA", img.size, "WHITE")
        img = Image.alpha_composite(white_bg, img)
        img = img.convert("RGB")

    
    img = img.resize((img.size[0] - img.size[0] % DIM, img.size[1] - img.size[1] % DIM), resample=Image.BILINEAR)
    
    TILESIZE = int(img.size[0] / DIM)
        
    TILESIZE = img.size[0] // DIM
    width, height = img.size
    tiles_x = width // TILESIZE
    tiles_y = height // TILESIZE

    for ty in range(tiles_y):
        for tx in range(tiles_x):
            left = tx * TILESIZE
            upper = ty * TILESIZE
            right = left + TILESIZE
            lower = upper + TILESIZE
            
            sec = img.crop((left, upper, right, lower))
            blc = 0
            
            for j in range(TILESIZE):
                for k in range(TILESIZE):
                    rgb = sec.getpixel((j, k))
                    if (rgb[0] + rgb[1] + rgb[2]) <= 90:
                        blc += 1

            if blc >= math.floor(TILESIZE * TILESIZE * 0.9):
                sects.append("#")
            else:
                sects.append(" ")

    # Reshape sects array to 2D and convert ascii to voxel points
    sects_w = DIM
    sects_h = len(sects) // sects_w
    ascii_2d = [sects[i * sects_w: (i + 1) * sects_w] for i in range(sects_h)]
    
    return ascii_2d
    
def ascii_to_3d(ascii_2d, depth):
    voxels = []
    for z in range(depth):
        for y, row in enumerate(ascii_2d):
            for x, char in enumerate(row):
                if char == '#':
                    is_side = (z == 0 or z == depth - 1)
                    voxels.append(([x, y, z], is_side))
                    
    return voxels    
    
def center_voxels(voxels):
    xs = [v[0][0] for v in voxels]
    ys = [v[0][1] for v in voxels]
    zs = [v[0][2] for v in voxels]
    cx = (max(xs) + min(xs)) / 2
    cy = (max(ys) + min(ys)) / 2
    cz = (max(zs) + min(zs)) / 2
    
    return cx, cy, cz
    
# Y-axis rotation
def rotate_y(point, angle_rad):
    x, y, z = point
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    x_rot = x * cos_a + z * sin_a
    z_rot = -x * sin_a + z * cos_a
    
    return[x_rot, y, z_rot]
    
# 3D -> 2D plane projection and rendering
def project(point, view_distance=200, screen_w=100, screen_h=100):
    x, y, z = point
    denom = view_distance + z
    if denom <= 0:
        return None
    
    factor = view_distance / denom
    x_proj = int(screen_w / 2 + x * factor)
    y_proj = int(screen_h / 2 + y * factor)
    
    return (x_proj, y_proj)
    
def render_frame(points, chars, min_x, min_y, w, h, padding=5, depths=None):
    frame = [['.' for _ in range(w)] for _ in range(h)]
    zbuffer = [[float('inf') for _ in range(w)] for _ in range(h)]

    for i, (x, y) in enumerate(points):
        fx = x - min_x + padding
        fy = y - min_y + padding
        if 0 <= fx < w and 0 <= fy < h:
            z = depths[i] if depths else 0
            if z < zbuffer[fy][fx]:
                zbuffer[fy][fx] = z
                frame[fy][fx] = chars[i]
    
    return '\n'.join(''.join(row) for row in frame) + '\n' + ''.join(['.' for _ in range(w - 13)] + ['N', 'O', 'T', ' ', 'A', ' ', 'G', 'I', 'F', '.', '.', '.', '.']) + '\n' + ''.join('.' for _ in range(w))

            
def save_frames_to_json(frames, json_path):
    with open(json_path, 'w') as f:
        json.dump(frames, f)
    
if __name__ == '__main__':
    DIM = 170
    IMGINDEX = 4
    DEPTH = 10
    FRAME_COUNT = 50
    JSON_PATH = "ascii_frames.json"
    
    ascii = get_ascii(dir_ind=IMGINDEX, dim=DIM)
    voxels = ascii_to_3d(ascii, DEPTH)
    cx, cy, cz = center_voxels(voxels)
    
    # Static projection to determine frame size
    project_static = [project([v[0][0] - cx, v[0][1] - cy, v[0][2] - cz]) for v in voxels]
    xs, ys = zip(*project_static)
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    fixed_width = max_x - min_x + 1 + 10
    fixed_height = max_y - min_y + 1 + 10
    
    frames = []
    
    for i in range(FRAME_COUNT):
        angle = i * (2 * math.pi / FRAME_COUNT)
        rotated = []
        chars = []
        
        for (pos, is_side) in voxels:
            shifted = [pos[0] - cx, pos[1] - cy, pos[2] - cz]
            rot = rotate_y(shifted, angle)
            rotated.append(rot)
            chars.append('#' if is_side else '@')
        
        projected = []
        depths = []
        filtered_chars = []

        for j, p in enumerate(rotated):
            proj = project(p)
            if proj is not None:
                projected.append(proj)
                depths.append(p[2])
                filtered_chars.append(chars[j])

        frame = render_frame(projected, filtered_chars, min_x, min_y, fixed_width, fixed_height, padding=5, depths=depths)
        frames.append(frame)

    save_frames_to_json(frames, JSON_PATH)
    print(f"Saved {len(frames)} frames to '{JSON_PATH}'")