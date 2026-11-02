import sys

def parse_game_start(filename):
    with open(filename, 'r') as f:
        lines = f.readlines()
        
    for i in range(len(lines)):
        if lines[i].startswith("game_start "):
            ops_str = lines[i+1].strip().split()
            num_ops = int(ops_str[0])
            idx = 1
            op_idx = 0
            while idx < len(ops_str):
                opcode = int(ops_str[idx])
                
                # Check for call_script (1)
                if opcode == 1:
                    num_args = int(ops_str[idx+1])
                    script_id = int(ops_str[idx+2])
                    args = ops_str[idx+3 : idx+2+num_args]
                    print(f"[{op_idx}] call_script {script_id} args: {args}")
                    idx += 2 + num_args
                else:
                    # just skip to next opcode? we don't know num_args for other opcodes!
                    # Wait, in Warband compiled txt, each opcode doesn't explicitly store num_args unless it's a known format?
                    # NO, in Warband txt, every operation does NOT store num_args!
                    pass
            break

parse_game_start("/home/wxm/GOG Games/Mount Blade Warband/game/Modules/Native/scripts.txt")
