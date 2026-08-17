"""
Figure-Ground Perception Stimulus Generator
Based on Peterson & Salvagio (2008) and Stevens & Brookes (1988)

Generates vertical wavy-edge stimuli with alternating convex and concave regions.

Usage:
    python3 stimulus_generator.py [options]

    --num_regions INT        Number of alternating vertical regions (default: 8)
    --num_lobes INT          Number of lobes (wave cycles) per edge, top to bottom (default: 6)
    --fill_mode STR          'outline' | 'binary' | 'colored' | 'homogeneous' (default: outline)
    --target_part STR        'convex' | 'concave' | 'both' (default: convex)
    --convex_palette COL...  Space-separated list of colors for convex regions
    --concave_palette COL... Space-separated list of colors for concave regions
    --probe_region INT       Region index (0-based) where red probe appears (default: center)
    --no_probe               Disable the red probe square
    --amplitude FLOAT        Lobe amplitude in pixels (default: 22)
    --sublobe_prob FLOAT     Probability of sub-lobes on each lobe, 0.0-1.0 (default: 0.44)
    --seed INT               Random seed for reproducibility
    --output STR             Output file path (default: generated_stimulus.png)
    --width INT              Image width in pixels (default: 750)
    --height INT             Image height in pixels (default: 260)
"""

import argparse
import math
import random
from PIL import Image, ImageDraw


def _color_to_rgb(color):
    """Convert color name, hex string, or RGB tuple to (R, G, B) tuple."""
    if isinstance(color, tuple) and len(color) == 3:
        return color
    if isinstance(color, str):
        color = color.strip()
        if color.startswith('#'):
            h = color.lstrip('#')
            if len(h) == 6:
                return tuple(int(h[i:i+2], 16) for i in (0, 2, 4))
        lookup = {
            'white': (255, 255, 255), 'black': (0, 0, 0), 'red': (220, 30, 30),
            'gray': (128, 128, 128), 'lightgray': (200, 200, 200), 'darkgray': (80, 80, 80),
            'yellow': (235, 210, 40), 'cyan': (40, 195, 215), 'magenta': (215, 50, 140),
            'green': (50, 165, 75), 'orange': (240, 130, 40), 'blue': (40, 100, 220),
            'purple': (130, 50, 200), 'pink': (230, 100, 150), 'brown': (140, 80, 40),
        }
        return lookup.get(color.lower(), (180, 180, 180))
    return (255, 255, 255)


def make_edge_points(spine_x, y_start, y_end, num_lobes,
                     direction, amplitude, sublobe_prob, rng,
                     spine_wobble=0.0, amplitude_variability=0.2, lobe_height_variability=0.0):
    """
    Build an ordered list of (x, y) points describing one vertical wavy edge.

    The edge oscillates left and right of `spine_x` with smooth rounded lobes.
    `direction` (+1 or -1) controls which side the convex bulge faces.
    `spine_wobble` (px): lateral drift of the edge spine along y (varies width throughout region).
    `amplitude_variability`: variation in peak bulge amplitude between lobes along the edge.
    `lobe_height_variability`: variation in vertical heights of individual lobes along the edge.
    """
    height = y_end - y_start
    samples_per_lobe = 80  # dense sampling for smooth curves

    # Setup spine lateral wobble params
    if spine_wobble > 0.0:
        wobble_freq = rng.uniform(0.8, 1.6)
        wobble_phase = rng.uniform(0.0, 2.0 * math.pi)
        wobble_amp = rng.uniform(spine_wobble * 0.5, spine_wobble)
    else:
        wobble_amp = 0.0

    def get_spine_x(y):
        if wobble_amp > 0.0:
            norm_y = (y - y_start) / max(1.0, height)
            return spine_x + wobble_amp * math.sin(2.0 * math.pi * wobble_freq * norm_y + wobble_phase)
        return spine_x

    # Calculate per-lobe vertical heights
    if lobe_height_variability > 0.0:
        var = min(0.7, max(0.0, lobe_height_variability))
        raw_h = [1.0 + rng.uniform(-var, var) for _ in range(num_lobes)]
        tot_raw = sum(raw_h)
        lobe_h_list = [h_i / tot_raw * height for h_i in raw_h]
    else:
        lobe_h_list = [height / float(num_lobes)] * num_lobes

    pts = []
    curr_top = y_start

    for lobe_i in range(num_lobes):
        lobe_top = curr_top
        lobe_h = lobe_h_list[lobe_i]
        lobe_bot = lobe_top + lobe_h
        curr_top = lobe_bot

        # Amplitude variation per lobe
        var_amp = max(0.1, amplitude_variability)
        amp = amplitude * rng.uniform(max(0.2, 1.0 - var_amp), 1.0 + var_amp)

        has_sublobe = rng.random() < sublobe_prob

        if not has_sublobe:
            for s in range(samples_per_lobe):
                t = s / samples_per_lobe
                y = lobe_top + t * lobe_h
                sx = get_spine_x(y)
                x_offset = amp * math.sin(math.pi * t)
                pts.append((sx + direction * x_offset, y))
        else:
            sub_on_upper = rng.random() < 0.5
            t_split = rng.uniform(0.30, 0.50)
            sub_amp = amp * rng.uniform(0.35, 0.55)

            for s in range(samples_per_lobe):
                t = s / samples_per_lobe
                y = lobe_top + t * lobe_h
                sx = get_spine_x(y)

                if sub_on_upper:
                    if t <= t_split:
                        t_norm = t / t_split
                        x_offset = sub_amp * math.sin(math.pi * t_norm)
                    else:
                        t_norm = (t - t_split) / (1.0 - t_split)
                        x_offset = amp * math.sin(math.pi * t_norm)
                else:
                    if t <= t_split:
                        t_norm = t / t_split
                        x_offset = amp * math.sin(math.pi * t_norm)
                    else:
                        t_norm = (t - t_split) / (1.0 - t_split)
                        x_offset = sub_amp * math.sin(math.pi * t_norm)

                pts.append((sx + direction * x_offset, y))

    pts.append((get_spine_x(y_end), y_end))
    return pts


def make_cap_arc(p1, p2, bulge=18.0, direction=1, samples=40):
    """
    Builds a smooth capping spline arc connecting point p1 to p2.
    direction: +1 bulges outward (away from region center), -1 bulges inward.
    """
    x1, y1 = p1
    x2, y2 = p2
    pts = []
    dx = x2 - x1
    dy = y2 - y1
    dist = math.hypot(dx, dy)
    if dist < 1e-5:
        return [p1, p2]

    # Normal vector perpendicular to chord
    nx = -dy / dist
    ny = dx / dist

    for s in range(samples + 1):
        t = s / float(samples)
        cx = x1 + t * dx
        cy = y1 + t * dy
        # Sine arch
        h = bulge * math.sin(math.pi * t) * direction
        px = cx + h * nx
        py = cy + h * ny
        pts.append((px, py))

    return pts


class FigureGroundGenerator:
    """
    Generates figure-ground visual stimuli with vertical wavy edges.
    """

    def __init__(self, width=750, height=260, seed=None):
        self.width = width
        self.height = height
        self.seed = seed

    def generate(self,
                 num_regions=8,
                 num_lobes=6,
                 target_part='convex',
                 fill_mode='outline',
                 convex_color_palette=None,
                 concave_color_palette=None,
                 background_color='white',
                 amplitude=22,
                 sublobe_prob=0.44,
                 width_variability=0.0,
                 spine_wobble=0.0,
                 amplitude_variability=0.2,
                 lobe_height_variability=0.0,
                 closure='open',
                 cap_amplitude=18.0,
                 probe_config=None,
                 seed=None):
        """
        Generate a figure-ground stimulus image.

        Parameters
        ----------
        num_regions : int
            Number of alternating vertical regions (odd number required for closure='closed').
        num_lobes : int
            Number of convex lobes per vertical edge (controls wave frequency).
        target_part : str
            Which region type to apply color palette to: 'convex', 'concave', or 'both'.
        fill_mode : str
            'outline'      – white background, black edge lines, red probe.
            'binary'       – alternating black/white fills.
            'colored'      – apply convex_color_palette and concave_color_palette.
            'homogeneous'  – uniform color on target regions, varied on non-target.
        convex_color_palette : list of str/tuple
            Colors assigned to convex regions.
        concave_color_palette : list of str/tuple
            Colors assigned to concave regions.
        background_color : str or tuple
            Canvas background color.
        amplitude : float
            Peak lobe displacement in pixels from the spine.
        sublobe_prob : float
            Probability (0–1) that any lobe has a secondary notch/sub-lobe.
        width_variability : float
            Variability factor (0.0 to 0.7) for overall region base widths across columns.
        spine_wobble : float
            Maximum pixel lateral drift of the spine along vertical y.
        amplitude_variability : float
            Variation factor for peak lobe amplitude vertically along the edge.
        lobe_height_variability : float
            Variation factor for vertical lobe heights along the edge.
        closure : str
            'open' (default) – standard open top/bottom horizontal frame lines.
            'closed' – encloses target regions at top and bottom with matching splines. Requires odd num_regions.
        cap_amplitude : float
            Bulge height of top/bottom capping splines when closure='closed'.
        probe_config : dict
            Red probe options: {'enabled': bool, 'region': int, 'size': int, 'color': str}
        seed : int
            Random seed for reproducible generation.

        Returns
        -------
        PIL.Image.Image
        """
        effective_seed = seed if seed is not None else self.seed
        rng = random.Random(effective_seed) if effective_seed is not None else random.Random()

        # Enforce odd number of regions when closure='closed'
        if closure == 'closed' and num_regions % 2 == 0:
            num_regions += 1  # auto-convert to next odd integer (e.g. 8 -> 9)

        W, H = self.width, self.height
        num_edges = num_regions - 1

        # Determine region widths and spine positions
        if width_variability > 0.0:
            var = min(0.8, max(0.0, width_variability))
            raw_w = [1.0 + rng.uniform(-var, var) for _ in range(num_regions)]
            total_raw = sum(raw_w)
            region_widths = [w_i / total_raw * W for w_i in raw_w]
        else:
            uniform_w = W / float(num_regions)
            region_widths = [uniform_w] * num_regions

        spine_xs = []
        cum_x = 0.0
        for r in range(num_edges):
            cum_x += region_widths[r]
            spine_xs.append(cum_x)

        # Padding for closed top/bottom cap bulges if needed
        y_pad = cap_amplitude + 2 if closure == 'closed' else 0
        y_start = y_pad
        y_end = H - 1 - y_pad

        # --- Generate edge contours ---
        edge_curves = []
        for e in range(num_edges):
            spine_x = spine_xs[e]
            direction = 1 if (e % 2 == 0) else -1

            pts = make_edge_points(
                spine_x=spine_x,
                y_start=y_start,
                y_end=y_end,
                num_lobes=num_lobes,
                direction=direction,
                amplitude=amplitude,
                sublobe_prob=sublobe_prob,
                rng=rng,
                spine_wobble=spine_wobble,
                amplitude_variability=amplitude_variability,
                lobe_height_variability=lobe_height_variability
            )
            edge_curves.append(pts)

        # --- Build region fill polygons and capping arcs ---
        def edge_as_poly_fwd(curve):
            return [(px, py) for px, py in curve]

        def edge_as_poly_rev(curve):
            return [(px, py) for px, py in reversed(curve)]

        region_polygons = []
        top_caps = {}
        bot_caps = {}

        for r in range(num_regions):
            poly = []
            is_closed_target = (closure == 'closed' and r % 2 == 0)

            # Left & right top/bottom anchor points
            p_tl = (0, y_start) if r == 0 else edge_curves[r - 1][0]
            p_tr = (W, y_start) if r == num_regions - 1 else edge_curves[r][0]
            p_br = (W, y_end) if r == num_regions - 1 else edge_curves[r][-1]
            p_bl = (0, y_end) if r == 0 else edge_curves[r - 1][-1]

            if is_closed_target:
                # Create curved top and bottom caps matching opposite sides
                t_cap = make_cap_arc(p_tl, p_tr, bulge=cap_amplitude, direction=-1)
                b_cap = make_cap_arc(p_br, p_bl, bulge=cap_amplitude, direction=-1)

                top_caps[r] = t_cap
                bot_caps[r] = b_cap

                poly.extend(t_cap)
                if r < num_edges:
                    poly.extend(edge_as_poly_fwd(edge_curves[r]))
                else:
                    poly.append(p_br)
                poly.extend(b_cap)
                if r > 0:
                    poly.extend(edge_as_poly_rev(edge_curves[r - 1]))
                else:
                    poly.append(p_tl)
            else:
                if r == 0:
                    poly.append((0, y_start))
                    poly.extend(edge_as_poly_fwd(edge_curves[0]))
                    poly.append((0, y_end))
                elif r == num_regions - 1:
                    poly.extend(edge_as_poly_rev(edge_curves[-1]))
                    poly.append((W, y_start))
                    poly.append((W, y_end))
                else:
                    poly.extend(edge_as_poly_fwd(edge_curves[r - 1]))
                    poly.extend(edge_as_poly_rev(edge_curves[r]))

            region_polygons.append(poly)

        # --- Create image ---
        bg = _color_to_rgb(background_color)
        img = Image.new('RGB', (W, H), bg)
        draw = ImageDraw.Draw(img)

        # --- Fill regions ---
        cvx_pal = convex_color_palette or (['black'] if fill_mode == 'binary' else ['white'])
        cnc_pal = concave_color_palette or (['white'])

        if fill_mode != 'outline':
            for r, poly in enumerate(region_polygons):
                is_convex = (r % 2 == 0)

                if fill_mode == 'binary':
                    c = 'black' if is_convex else 'white'
                elif fill_mode == 'homogeneous':
                    if target_part == 'convex' and is_convex:
                        c = cvx_pal[0]
                    elif target_part == 'concave' and not is_convex:
                        c = cnc_pal[0]
                    else:
                        pal = cnc_pal if is_convex else cvx_pal
                        c = pal[(r // 2) % len(pal)]
                else:  # 'colored' / 'heterogeneous'
                    if is_convex:
                        c = cvx_pal[(r // 2) % len(cvx_pal)]
                    else:
                        c = cnc_pal[(r // 2) % len(cnc_pal)]

                draw.polygon(poly, fill=_color_to_rgb(c))

        # --- Draw edge outlines ---
        for curve in edge_curves:
            flat = []
            for px, py in curve:
                flat.extend([px, py])
            draw.line(flat, fill=(0, 0, 0), width=2)

        # Draw top and bottom capping splines for closed shapes
        if closure == 'closed':
            for r, t_cap in top_caps.items():
                flat = []
                for px, py in t_cap:
                    flat.extend([px, py])
                draw.line(flat, fill=(0, 0, 0), width=2)

            for r, b_cap in bot_caps.items():
                flat = []
                for px, py in b_cap:
                    flat.extend([px, py])
                draw.line(flat, fill=(0, 0, 0), width=2)
        else:
            # Draw standard top and bottom frame lines
            draw.line([(0, y_start), (W, y_start)], fill=(0, 0, 0), width=2)
            draw.line([(0, y_end), (W, y_end)], fill=(0, 0, 0), width=2)

        # --- Draw probe ---
        p_cfg = probe_config if probe_config else {}
        if p_cfg.get('enabled', True):
            probe_r = p_cfg.get('region', num_regions // 2)
            probe_r = max(0, min(num_regions - 1, probe_r))
            
            r_left = 0.0 if probe_r == 0 else spine_xs[probe_r - 1]
            r_right = float(W) if probe_r == num_regions - 1 else spine_xs[probe_r]
            
            cx = (r_left + r_right) / 2.0
            cy = H / 2.0
            sz = p_cfg.get('size', 16)
            pcol = _color_to_rgb(p_cfg.get('color', 'red'))
            draw.rectangle([cx - sz/2, cy - sz/2, cx + sz/2, cy + sz/2],
                           fill=pcol)

        return img


def main():
    parser = argparse.ArgumentParser(
        description="Figure-Ground Stimulus Generator (Peterson & Salvagio 2008)"
    )
    parser.add_argument('--num_regions', type=int, default=7,
                        help='Number of alternating vertical regions (default: 7, odd required for closure=closed)')
    parser.add_argument('--num_lobes', type=int, default=6,
                        help='Lobes (wave cycles) per edge, top to bottom (default: 6)')
    parser.add_argument('--fill_mode', type=str, default='outline',
                        choices=['outline', 'binary', 'colored', 'homogeneous'],
                        help='Region fill style (default: outline)')
    parser.add_argument('--target_part', type=str, default='convex',
                        choices=['convex', 'concave', 'both'],
                        help='Which region type gets the color palette (default: convex)')
    parser.add_argument('--convex_palette', type=str, nargs='+', default=None,
                        help='Colors for convex regions (space-separated)')
    parser.add_argument('--concave_palette', type=str, nargs='+', default=None,
                        help='Colors for concave regions (space-separated)')
    parser.add_argument('--amplitude', type=float, default=22,
                        help='Lobe peak amplitude in pixels (default: 22)')
    parser.add_argument('--sublobe_prob', type=float, default=0.44,
                        help='Probability of sub-lobes per lobe, 0.0-1.0 (default: 0.44)')
    parser.add_argument('--width_variability', type=float, default=0.0,
                        help='Variability factor (0.0 to 0.7) for region base widths across columns (default: 0.0)')
    parser.add_argument('--spine_wobble', type=float, default=15.0,
                        help='Pixel lateral wobble of spine along vertical y (varies width throughout a single region)')
    parser.add_argument('--amplitude_variability', type=float, default=0.2,
                        help='Variation factor for peak lobe amplitude along the edge')
    parser.add_argument('--lobe_height_variability', type=float, default=0.0,
                        help='Variation factor for vertical lobe heights along the edge')
    parser.add_argument('--closure', type=str, default='open', choices=['open', 'closed'],
                        help='Top/bottom shape closure: open (frame lines) or closed (top/bottom spline caps on odd regions)')
    parser.add_argument('--cap_amplitude', type=float, default=18.0,
                        help='Bulge height in pixels for top/bottom capping splines when closure=closed')
    parser.add_argument('--probe_region', type=int, default=None,
                        help='Region index (0-based) for probe (default: center region)')
    parser.add_argument('--no_probe', action='store_true',
                        help='Disable the red probe square')
    parser.add_argument('--seed', type=int, default=random.randint(0,100000),
                        help='Random seed')
    parser.add_argument('--output', type=str, default='generated_stimulus.png',
                        help='Output image file path (default: generated_stimulus.png)')
    parser.add_argument('--width', type=int, default=750,
                        help='Canvas width in pixels (default: 750)')
    parser.add_argument('--height', type=int, default=260,
                        help='Canvas height in pixels (default: 260)')

    args = parser.parse_args()

    gen = FigureGroundGenerator(width=args.width, height=args.height, seed=args.seed)

    probe_r = args.probe_region if args.probe_region is not None else args.num_regions // 2
    probe_cfg = {
        'enabled': not args.no_probe,
        'region': probe_r,
        'size': 16,
        'color': 'red'
    }

    img = gen.generate(
        num_regions=args.num_regions,
        num_lobes=args.num_lobes,
        fill_mode=args.fill_mode,
        target_part=args.target_part,
        convex_color_palette=args.convex_palette,
        concave_color_palette=args.concave_palette,
        amplitude=args.amplitude,
        sublobe_prob=args.sublobe_prob,
        width_variability=args.width_variability,
        spine_wobble=args.spine_wobble,
        amplitude_variability=args.amplitude_variability,
        lobe_height_variability=args.lobe_height_variability,
        closure=args.closure,
        cap_amplitude=args.cap_amplitude,
        probe_config=probe_cfg,
        seed=args.seed
    )

    img.save(args.output)
    print(f"Saved: {args.output} ({args.width}x{args.height})")
    print(f"  Regions: {args.num_regions}, Lobes: {args.num_lobes}, Closure: {args.closure}")
    print(f"  Fill: {args.fill_mode}, Target: {args.target_part}")


if __name__ == '__main__':
    main()
