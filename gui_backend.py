"""
Figure-Ground Perception Stimulus Generator - GUI Backend Server
Provides local HTTP web server and REST API for the GUI interface.
"""

import argparse
import base64
import json
import os
import shlex
import sys
from http import HTTPStatus
from http.server import HTTPServer, BaseHTTPRequestHandler
from io import BytesIO
from urllib.parse import parse_qs, urlparse

# Import generator from workspace
from stimulus_generator import FigureGroundGenerator, _color_to_rgb


def parse_cli_command(command_str):
    """
    Parse a python3 stimulus_generator.py CLI command string into a parameter dictionary.
    """
    cmd = command_str.strip()
    if cmd.startswith('$'):
        cmd = cmd[1:].strip()
    
    tokens = shlex.split(cmd)
    
    # Strip leading 'python3', 'python', 'stimulus_generator.py', etc.
    filtered_tokens = []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token.endswith('.py') or token in ('python', 'python3', 'py'):
            i += 1
            continue
        filtered_tokens.append(token)
        i += 1

    parser = argparse.ArgumentParser()
    parser.add_argument('--num_regions', type=int, default=8)
    parser.add_argument('--num_lobes', type=int, default=6)
    parser.add_argument('--fill_mode', type=str, default='outline',
                        choices=['outline', 'binary', 'colored', 'homogeneous'])
    parser.add_argument('--target_part', type=str, default='convex',
                        choices=['convex', 'concave', 'both'])
    parser.add_argument('--convex_palette', type=str, nargs='+', default=None)
    parser.add_argument('--concave_palette', type=str, nargs='+', default=None)
    parser.add_argument('--amplitude', type=float, default=22)
    parser.add_argument('--sublobe_prob', type=float, default=0.44)
    parser.add_argument('--width_variability', type=float, default=0.0)
    parser.add_argument('--spine_wobble', type=float, default=15.0)
    parser.add_argument('--amplitude_variability', type=float, default=0.2)
    parser.add_argument('--lobe_height_variability', type=float, default=0.0)
    parser.add_argument('--closure', type=str, default='open', choices=['open', 'closed'])
    parser.add_argument('--cap_amplitude', type=float, default=18.0)
    parser.add_argument('--probe_region', type=int, default=None)
    parser.add_argument('--no_probe', action='store_true')
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--output', type=str, default='generated_stimulus.png')
    parser.add_argument('--width', type=int, default=750)
    parser.add_argument('--height', type=int, default=260)

    try:
        args, _ = parser.parse_known_args(filtered_tokens)
    except Exception as e:
        raise ValueError(f"Could not parse command string: {e}")

    probe_r = args.probe_region if args.probe_region is not None else (args.num_regions // 2)
    
    cvx_pal = args.convex_palette if args.convex_palette else []
    cnc_pal = args.concave_palette if args.concave_palette else []

    params = {
        'num_regions': args.num_regions,
        'num_lobes': args.num_lobes,
        'fill_mode': args.fill_mode,
        'target_part': args.target_part,
        'convex_palette': cvx_pal,
        'concave_palette': cnc_pal,
        'amplitude': args.amplitude,
        'sublobe_prob': args.sublobe_prob,
        'width_variability': args.width_variability,
        'spine_wobble': args.spine_wobble,
        'amplitude_variability': args.amplitude_variability,
        'lobe_height_variability': args.lobe_height_variability,
        'closure': args.closure,
        'cap_amplitude': args.cap_amplitude,
        'probe_enabled': not args.no_probe,
        'probe_region': probe_r,
        'seed': args.seed,
        'width': args.width,
        'height': args.height,
        'output': args.output
    }
    return params


def generate_command_string(params):
    """
    Format a parameter dictionary into a standard copy-pastable CLI command string.
    """
    parts = ["python3 stimulus_generator.py"]
    
    num_regions = int(params.get('num_regions', 8))
    parts.append(f"--num_regions {num_regions}")
    parts.append(f"--num_lobes {params.get('num_lobes', 6)}")
    
    fill_mode = params.get('fill_mode', 'outline')
    parts.append(f"--fill_mode {fill_mode}")
    
    if fill_mode in ('colored', 'homogeneous'):
        parts.append(f"--target_part {params.get('target_part', 'convex')}")
    
    cvx = params.get('convex_palette', [])
    if cvx and len(cvx) > 0:
        cvx_str = " ".join(cvx)
        parts.append(f"--convex_palette {cvx_str}")
        
    cnc = params.get('concave_palette', [])
    if cnc and len(cnc) > 0:
        cnc_str = " ".join(cnc)
        parts.append(f"--concave_palette {cnc_str}")

    amp = float(params.get('amplitude', 22))
    parts.append(f"--amplitude {amp:g}")
    
    sublobe = float(params.get('sublobe_prob', 0.44))
    parts.append(f"--sublobe_prob {sublobe:g}")
    
    closure = params.get('closure', 'open')
    if closure == 'closed':
        parts.append("--closure closed")
        parts.append(f"--cap_amplitude {float(params.get('cap_amplitude', 18)):g}")
        
    w_var = float(params.get('width_variability', 0.0))
    if w_var > 0:
        parts.append(f"--width_variability {w_var:g}")
        
    wobble = float(params.get('spine_wobble', 15.0))
    if wobble != 15.0:
        parts.append(f"--spine_wobble {wobble:g}")
        
    amp_var = float(params.get('amplitude_variability', 0.2))
    if amp_var != 0.2:
        parts.append(f"--amplitude_variability {amp_var:g}")
        
    h_var = float(params.get('lobe_height_variability', 0.0))
    if h_var > 0:
        parts.append(f"--lobe_height_variability {h_var:g}")
        
    probe_enabled = params.get('probe_enabled', True)
    if not probe_enabled:
        parts.append("--no_probe")
    else:
        pr_r = int(params.get('probe_region', num_regions // 2))
        if pr_r != num_regions // 2:
            parts.append(f"--probe_region {pr_r}")

    seed = params.get('seed')
    if seed is not None:
        parts.append(f"--seed {seed}")

    width = int(params.get('width', 750))
    height = int(params.get('height', 260))
    if width != 750:
        parts.append(f"--width {width}")
    if height != 260:
        parts.append(f"--height {height}")

    out = params.get('output', 'generated_stimulus.png')
    if out != 'generated_stimulus.png':
        parts.append(f"--output {shlex.quote(out)}")

    return " ".join(parts)


class StimulusGUIRequestHandler(BaseHTTPRequestHandler):

    def log_message(self, format, *args):
        pass

    def _send_json(self, data, status=HTTPStatus.OK):
        body = json.dumps(data).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, filepath, content_type):
        try:
            with open(filepath, 'rb') as f:
                content = f.read()
            self.send_response(HTTPStatus.OK)
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(HTTPStatus.NOT_FOUND, f"File not found: {e}")

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path

        if path in ('/', '/index.html'):
            static_dir = os.path.join(os.path.dirname(__file__), 'static')
            index_path = os.path.join(static_dir, 'index.html')
            self._send_file(index_path, 'text/html; charset=utf-8')
        elif path.startswith('/static/'):
            filename = os.path.basename(path)
            static_dir = os.path.join(os.path.dirname(__file__), 'static')
            file_path = os.path.join(static_dir, filename)
            
            ct = 'text/plain'
            if filename.endswith('.css'):
                ct = 'text/css; charset=utf-8'
            elif filename.endswith('.js'):
                ct = 'application/javascript; charset=utf-8'
            elif filename.endswith('.png'):
                ct = 'image/png'
            elif filename.endswith('.svg'):
                ct = 'image/svg+xml'
            
            self._send_file(file_path, ct)
        else:
            self.send_error(HTTPStatus.NOT_FOUND, "Page not found")

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get('Content-Length', 0))
        raw_body = self.rfile.read(content_length).decode('utf-8')
        
        try:
            req_data = json.loads(raw_body) if raw_body else {}
        except Exception:
            req_data = {}

        if path == '/api/preview':
            self.handle_preview(req_data)
        elif path == '/api/parse_command':
            self.handle_parse_command(req_data)
        elif path == '/api/batch_generate':
            self.handle_batch_generate(req_data)
        elif path == '/api/export_commands':
            self.handle_export_commands(req_data)
        else:
            self.send_error(HTTPStatus.NOT_FOUND, "API route not found")

    def handle_preview(self, params):
        try:
            w = int(params.get('width', 750))
            h = int(params.get('height', 260))
            seed = params.get('seed')
            if seed is not None and str(seed).strip() != '':
                seed = int(seed)
            else:
                seed = 42

            gen = FigureGroundGenerator(width=w, height=h, seed=seed)

            num_regions = int(params.get('num_regions', 8))
            probe_r = int(params.get('probe_region', num_regions // 2))
            probe_cfg = {
                'enabled': bool(params.get('probe_enabled', True)),
                'region': probe_r,
                'size': int(params.get('probe_size', 16)),
                'color': params.get('probe_color', 'red')
            }

            cvx = params.get('convex_palette', [])
            cnc = params.get('concave_palette', [])
            bg_col = params.get('background_color', 'white')

            img = gen.generate(
                num_regions=num_regions,
                num_lobes=int(params.get('num_lobes', 6)),
                fill_mode=params.get('fill_mode', 'outline'),
                target_part=params.get('target_part', 'convex'),
                convex_color_palette=cvx if cvx else None,
                concave_color_palette=cnc if cnc else None,
                background_color=bg_col,
                amplitude=float(params.get('amplitude', 22)),
                sublobe_prob=float(params.get('sublobe_prob', 0.44)),
                width_variability=float(params.get('width_variability', 0.0)),
                spine_wobble=float(params.get('spine_wobble', 15.0)),
                amplitude_variability=float(params.get('amplitude_variability', 0.2)),
                lobe_height_variability=float(params.get('lobe_height_variability', 0.0)),
                closure=params.get('closure', 'open'),
                cap_amplitude=float(params.get('cap_amplitude', 18.0)),
                probe_config=probe_cfg,
                seed=seed
            )

            buffer = BytesIO()
            img.save(buffer, format='PNG')
            b64_str = base64.b64encode(buffer.getvalue()).decode('utf-8')
            data_url = f"data:image/png;base64,{b64_str}"

            cmd_str = generate_command_string(params)

            self._send_json({
                'status': 'ok',
                'image': data_url,
                'command': cmd_str,
                'width': w,
                'height': h
            })
        except Exception as e:
            self._send_json({'status': 'error', 'message': str(e)}, status=HTTPStatus.BAD_REQUEST)

    def handle_parse_command(self, req_data):
        cmd_str = req_data.get('command', '')
        if not cmd_str:
            self._send_json({'status': 'error', 'message': 'Command string is empty'}, status=HTTPStatus.BAD_REQUEST)
            return

        try:
            params = parse_cli_command(cmd_str)
            self._send_json({'status': 'ok', 'params': params})
        except Exception as e:
            self._send_json({'status': 'error', 'message': str(e)}, status=HTTPStatus.BAD_REQUEST)

    def handle_batch_generate(self, req_data):
        try:
            params = req_data.get('settings', {})
            output_dir = req_data.get('output_dir', './output_batch').strip()
            count = int(req_data.get('count', 10))
            seed_mode = req_data.get('seed_mode', 'sequential')
            base_seed = int(params.get('seed', 100))
            prefix = req_data.get('prefix', 'stimulus').strip() or 'stimulus'

            os.makedirs(output_dir, exist_ok=True)

            w = int(params.get('width', 750))
            h = int(params.get('height', 260))
            num_regions = int(params.get('num_regions', 8))
            probe_r = int(params.get('probe_region', num_regions // 2))
            probe_cfg = {
                'enabled': bool(params.get('probe_enabled', True)),
                'region': probe_r,
                'size': int(params.get('probe_size', 16)),
                'color': params.get('probe_color', 'red')
            }
            cvx = params.get('convex_palette', [])
            cnc = params.get('concave_palette', [])
            bg_col = params.get('background_color', 'white')

            generated_files = []
            commands_log = []

            for i in range(count):
                if seed_mode == 'sequential':
                    current_seed = base_seed + i
                else:
                    import random
                    current_seed = random.randint(1, 999999)

                curr_params = dict(params)
                curr_params['seed'] = current_seed
                filename = f"{prefix}_{i+1:03d}_seed{current_seed}.png"
                filepath = os.path.join(output_dir, filename)
                curr_params['output'] = filepath

                gen = FigureGroundGenerator(width=w, height=h, seed=current_seed)
                img = gen.generate(
                    num_regions=num_regions,
                    num_lobes=int(params.get('num_lobes', 6)),
                    fill_mode=params.get('fill_mode', 'outline'),
                    target_part=params.get('target_part', 'convex'),
                    convex_color_palette=cvx if cvx else None,
                    concave_color_palette=cnc if cnc else None,
                    background_color=bg_col,
                    amplitude=float(params.get('amplitude', 22)),
                    sublobe_prob=float(params.get('sublobe_prob', 0.44)),
                    width_variability=float(params.get('width_variability', 0.0)),
                    spine_wobble=float(params.get('spine_wobble', 15.0)),
                    amplitude_variability=float(params.get('amplitude_variability', 0.2)),
                    lobe_height_variability=float(params.get('lobe_height_variability', 0.0)),
                    closure=params.get('closure', 'open'),
                    cap_amplitude=float(params.get('cap_amplitude', 18.0)),
                    probe_config=probe_cfg,
                    seed=current_seed
                )
                img.save(filepath)
                generated_files.append(filename)
                commands_log.append(generate_command_string(curr_params))

            log_path = os.path.join(output_dir, 'commands_log.txt')
            with open(log_path, 'w', encoding='utf-8') as f:
                f.write(f"# Batch Generated Stimuli Log ({count} files)\n")
                f.write(f"# Output Directory: {os.path.abspath(output_dir)}\n\n")
                for cmd in commands_log:
                    f.write(cmd + "\n")

            self._send_json({
                'status': 'ok',
                'message': f"Successfully generated {count} stimuli in '{output_dir}'",
                'output_dir': os.path.abspath(output_dir),
                'files_count': count,
                'log_path': os.path.abspath(log_path),
                'sample_files': generated_files[:5]
            })
        except Exception as e:
            self._send_json({'status': 'error', 'message': str(e)}, status=HTTPStatus.BAD_REQUEST)

    def handle_export_commands(self, req_data):
        try:
            filepath = req_data.get('filepath', 'generated_commands.txt').strip()
            command_text = req_data.get('command_text', '').strip()
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("# Figure-Ground Perception Stimuli Commands\n")
                f.write(command_text + "\n")

            self._send_json({
                'status': 'ok',
                'message': f"Saved commands file to '{os.path.abspath(filepath)}'",
                'filepath': os.path.abspath(filepath)
            })
        except Exception as e:
            self._send_json({'status': 'error', 'message': str(e)}, status=HTTPStatus.BAD_REQUEST)


def run_server(port=5000):
    server_address = ('0.0.0.0', port)
    httpd = HTTPServer(server_address, StimulusGUIRequestHandler)
    print(f"Stimulus Generator GUI server running at http://localhost:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down GUI server.")
        httpd.server_close()


if __name__ == '__main__':
    port = 5000
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        port = int(sys.argv[1])
    run_server(port)
