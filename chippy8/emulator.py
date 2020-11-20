import random
import curses
import sys
import time
import chippy8.asm as asm
import argparse

class UI:
    HEIGHT = 32
    WIDTH = 64

    def __init__(self, stdscr, debug=False):
        self.debug_count = 0
        self.debug_hist = ''
        self.stdscr = stdscr
        self.stdscr.nodelay(True)
        self.mainscreen = self.stdscr.subpad(UI.HEIGHT + 2,
                UI.WIDTH * 2 + 2, 0, 0)
        self.mainscreen.border()

        if debug:
            self.debug = self.stdscr.subpad(UI.HEIGHT + 2, 16 + 2, 0,
                    UI.WIDTH * 2 + 2)
            self.debug.border()
            self.registers = self.stdscr.subpad(18 + 4, 13 + 2, 0,
                                            UI.WIDTH * 2 + 2 + 16 + 2)
            self.registers.border()

    def get_bit_from_bytes(self, bytes_arr, location):
        byte_ptr = int(location / 8)
        bit_pos = 7 - (location % 8)
        return 0x1 & (bytes_arr[byte_ptr] >> bit_pos)


    def get_pixel(self, x, y, frame):
        return 0 if self.get_bit_from_bytes(frame, y * 64 + x) == 0 else 1

    def display_framebuffer(self, framebuffer):
        for y in range(0, 32):
            for x in range(0, 64):
                self.stdscr.addstr(y + 1, x * 2 + 1, '  ', curses.A_REVERSE \
                            if self.get_pixel(x, y, framebuffer) == 1 \
                            else curses.A_INVIS)
        self.mainscreen.refresh()

    # Debug display
    def debug_show_registers(self, cpu):
        self.registers.addstr(1, 1, 'I = %s' % hex(cpu.I))
        self.registers.addstr(2, 1, 'PC = %s' % hex(cpu.PC))
        self.registers.addstr(3, 1, 'DT = %s' % hex(cpu.DT))
        self.registers.addstr(4, 1, 'ST = %s' % hex(cpu.DT))
        for i in range(0, 0x10):
            self.registers.addstr(5 + i, 1, 'V[%s] = %s' % (hex(i),
                hex(cpu.V[i])))
        self.registers.refresh()

    def debug_str(self, s):
        if self.debug_hist != '':
            self.debug.addstr(1 + self.debug_count - 1, 1 + 0,
                    self.debug_hist)

        if self.debug_count > 31:
            self.debug_count = 0
            self.debug.border()
        self.debug_hist = s + ' ' * (16 - len(s))
        self.debug.addstr(1 + self.debug_count, 1 + 0, self.debug_hist,
                curses.A_REVERSE)
        self.debug.refresh()
        self.debug_count += 1


class CPU:
    def __init__(self, ui, debug=False, frequency=60):
        self.debug = debug
        self.frequency = frequency
        self.clock_rate = int((1 / self.frequency) * 1000)

        self.LOOKUP_TABLE_8 = {
            0x0000: self.t8_load_reg,
            0x0001: self.t8_or,
            0x0002: self.t8_and,
            0x0003: self.t8_xor,
            0x0004: self.t8_add_reg,
            0x0005: self.t8_sub,
            0x0006: self.t8_shift_right,
            0x0007: self.t8_subn,
            0x000E: self.t8_shift_left,
        }

        self.LOOKUP_TABLE_F = {
            0x0007: self.tf_load_dt,
            0x000A: self.tf_wait_key,
            0x0015: self.tf_set_dt,
            0x0018: self.tf_set_st,
            0x001E: self.tf_add_reg_i,
            0x0029: self.tf_load_dig_sprite,
            0x0033: self.tf_load_bcd,
            0x0055: self.tf_write_mem,
            0x0065: self.tf_read_mem,
        }

        self.LOOKUP_TABLE = {
            0x0000: self.lookup_0,

            0x1000: self.t1_jump,
            0x2000: self.t2_call,

            0x3000: self.t3_skip_equal,
            0x4000: self.t4_skip_ne,
            0x5000: self.t5_skip_equal_reg,

            0x6000: self.t6_load,
            0x7000: self.t7_add,

            0x8000: self.lookup_8,

            0x9000: self.t9_skip_ne_reg,
            0xA000: self.ta_load_i,
            0xB000: self.tb_jump_v0,
            0xC000: self.tc_rand,
            0xD000: self.td_draw,

            0xE000: self.lookup_e,

            0xF000: self.lookup_f,
        }

        self.KEY_ARRAY = ['x', # 0
                '1', '2', '3', # 1, 2, 3
                'q', 'w', 'e', # 4, 5, 6
                'a', 's', 'd', # 7, 8, 9
                'z', 'c', # a, b
                '4', 'r', 'f', 'v' # c, d, e, f
                ]

        self.reset()
        self.ui = ui
        self.last_tick = int(time.time() * 1000)

    def lookup_0(self):
        if self.opcode == 0x00E0:
            return self.t0_clear_screen()
        elif self.opcode == 0x00EE:
            return self.t0_return_sub()
        else:
            return self.t0_sys_jump()

    def lookup_8(self):
        return self.LOOKUP_TABLE_8[self.opcode & 0x000F]()

    def lookup_e(self):
        if self.opcode & 0xEF9E:
            return self.te_skip_key()
        elif self.opcode & 0XEFA1:
            return self.te_skipn_key()

    def lookup_f(self):
        return self.LOOKUP_TABLE_F[self.opcode & 0x00FF]()

    # 0x0000
    def t0_clear_screen(self):
        for i in range (0, 0xFF):
            self.memory[0xF00 + i] = 0

    def t0_return_sub(self):
        self.PC = self.stack.pop()

    def t0_sys_jump(self):
        pass

    # 0x31000
    def t1_jump(self):
        self.PC = 0x0FFF & self.opcode

    # 0x2000
    def t2_call(self):
        self.stack.append(self.PC)
        self.PC = 0x0FFF & self.opcode

    # 0x3000
    def t3_skip_equal(self):
        x = (self.opcode & 0x0F00) >> 8
        val = self.opcode & 0x00FF
        if self.V[x] == val:
            self.PC += 2

    # 0x4000
    def t4_skip_ne(self):
        x = (self.opcode & 0x0F00) >> 8
        val = self.opcode & 0x00FF
        if self.V[x] != val:
            self.PC += 2

    # 0x5000
    def t5_skip_equal_reg(self):
        x = (self.opcode & 0x0F00) >> 8
        y = (self.opcode & 0x00F0) >> 4
        if self.V[x] == self.V[y]:
            self.PC += 2

    # 0x6000
    def t6_load(self):
        x = (self.opcode & 0x0F00) >> 8
        val = self.opcode & 0x00FF
        self.V[x] = val

    # 0x7000
    def t7_add(self):
        x = (self.opcode & 0x0F00) >> 8
        val = self.opcode & 0x00FF
        self.V[x] = 0xFF & (val + self.V[x])

    # 0x8000
    def t8_load_reg(self):
        x = (self.opcode & 0x0F00) >> 8
        y = (self.opcode & 0x00F0) >> 4
        self.V[x] = self.V[y]

    def t8_or(self):
        x = (self.opcode & 0x0F00) >> 8
        y = (self.opcode & 0x00F0) >> 4
        self.V[x] = self.V[x] | self.V[y]

    def t8_and(self):
        x = (self.opcode & 0x0F00) >> 8
        y = (self.opcode & 0x00F0) >> 4
        self.V[x] = self.V[x] & self.V[y]

    def t8_xor(self):
        x = (self.opcode & 0x0F00) >> 8
        y = (self.opcode & 0x00F0) >> 4
        self.V[x] = self.V[x] ^ self.V[y]

    def t8_add_reg(self):
        x = (self.opcode & 0x0F00) >> 8
        y = (self.opcode & 0x00F0) >> 4
        val = self.V[x] + self.V[y]
        self.V[x] = val & 0xFF
        self.V[0xF] = 1 if val > 255 else 0

    def t8_sub(self):
        x = (self.opcode & 0x0F00) >> 8
        y = (self.opcode & 0x00F0) >> 4
        self.V[0xF] = 1 if self.V[x] > self.V[y] else 0
        self.V[x] = 0xFF & (self.V[x] - self.V[y])

    def t8_shift_right(self):
        x = (self.opcode & 0x0F00) >> 8
        self.V[0xF] = self.V[x] & 0x01
        self.V[x] = self.V[x] >> 1

    def t8_subn(self):
        x = (self.opcode & 0x0F00) >> 8
        y = (self.opcode & 0x00F0) >> 4
        self.V[0xF] = 1 if self.V[y] > self.V[x] else 0
        self.V[x] = 0xFF & (self.V[y] - self.V[x])

    def t8_shift_left(self):
        x = (self.opcode & 0x0F00) >> 8
        self.V[0xF] = ((self.V[x] & 0xFF) >> 7) & 0x1
        self.V[x] = 0xFF & (self.V[x] << 1)

    # 0x9000
    def t9_skip_ne_reg(self):
        x = (self.opcode & 0x0F00) >> 8
        y = (self.opcode & 0x00F0) >> 4
        if self.V[x] != self.V[y]:
            self.PC += 2

    # 0xA000
    def ta_load_i(self):
        self.I = self.opcode & 0x0FFF

    # 0xB000
    def tb_jump_v0(self):
        self.PC = (0x0FFF & self.opcode) + self.V[0x0]

    # 0xC000
    def tc_rand(self):
        x = (self.opcode & 0x0F00) >> 8
        k = self.opcode & 0x00FF
        self.V[x] = random.randrange(0, 255) & k

    # 0xD000
    def get_memory_bit(self, location):
        byte_ptr = int(location / 8)
        bit_pos = 7 - (location % 8)
        return 0x1 & (self.memory[byte_ptr] >> bit_pos)

    def set_memory_bit(self, location, value):
        byte_ptr = int(location / 8)
        bit_pos = 7 - (location % 8)
        self.memory[byte_ptr] = (self.memory[byte_ptr] \
                & (0xff - (0x1 << bit_pos))) \
                + (value << bit_pos)

    def td_draw(self):
        x = self.V[(self.opcode & 0x0F00) >> 8]
        y = self.V[(self.opcode & 0x00F0) >> 4]
        n = self.opcode & 0x000F
        self.V[0xF] = 0
        for k in range(0, n):
            y_comp = (y + k) % 32
            for j in range(0, 8):
                mem_bit = self.get_memory_bit((self.I + k) * 8 + j)
                x_comp = (x + j) % 64
                current_pixel = self.get_memory_bit(0xF00 * 8 + y_comp * 64 \
                        + x_comp)
                xored = 0x01 & (mem_bit ^ current_pixel)
                self.set_memory_bit(0xF00 * 8 + y_comp * 64 + x_comp, xored)
                if current_pixel > xored:
                    self.V[0xF] = 1
        self.draw_flag = True

    # 0xE000
    def get_pressed_key(self):
        key = self.ui.stdscr.getch()
        return key if key >= 0 else 0

    def te_skip_key(self):
        x = (self.opcode & 0x0F00) >> 8
        key = self.get_pressed_key()
        if chr(key) not in self.KEY_ARRAY \
                or self.V[x] != self.KEY_ARRAY.index(chr(key)):
                self.PC += 2

    def te_skipn_key(self):
        x = (self.opcode & 0x0F00) >> 8
        key = self.get_pressed_key()
        if chr(key) in self.KEY_ARRAY \
                and self.V[x] == self.KEY_ARRAY.index(chr(key)):
                self.PC += 2

    # 0xF000
    def tf_load_dt(self):
        x = (self.opcode & 0x0F00) >> 8
        self.V[x] = self.DT

    def tf_wait_key(self):
        x = (self.opcode & 0x0F00) >> 8
        key = self.get_pressed_key()
        while chr(key) not in self.KEY_ARRAY:
            key = self.get_pressed_key()
        self.V[x] = self.KEY_ARRAY.index(chr(key))

    def tf_set_dt(self):
        x = (self.opcode & 0x0F00) >> 8
        self.DT = self.V[x]

    def tf_set_st(self):
        x = (self.opcode & 0x0F00) >> 8
        self.ST = self.V[x]

    def tf_add_reg_i(self):
        x = (self.opcode & 0x0F00) >> 8
        self.I = 0xFFFF & (self.I + self.V[x])

    def tf_load_dig_sprite(self):
        x = (self.opcode & 0x0F00) >> 8
        self.I = self.V[x] * 5

    def tf_load_bcd(self):
        x = (self.opcode & 0x0F00) >> 8
        self.memory[self.I] = int((self.V[x] % 1000) / 100)
        self.memory[self.I + 1] = int((self.V[x] % 100) / 10)
        self.memory[self.I + 2] = self.V[x] % 10

    def tf_write_mem(self):
        x = (self.opcode & 0x0F00) >> 8
        for i in range(x + 1):
            self.memory[self.I + i] = self.V[i]

    def tf_read_mem(self):
        x = (self.opcode & 0x0F00) >> 8
        for i in range(x + 1):
            self.V[i] = self.memory[self.I + i]

    def load_characters(self):
        characters = bytearray([0xF0, 0x90, 0x90, 0x90, 0xF0,
            0x20, 0x60, 0x20, 0x20, 0x70,
            0xF0, 0x10, 0xF0, 0x80, 0xF0,
            0xF0, 0x10, 0xF0, 0x10, 0xF0,
            0x90, 0x90, 0xF0, 0x10, 0x10,
            0xF0, 0x80, 0xF0, 0x10, 0xF0,
            0xF0, 0x80, 0xF0, 0x90, 0xF0,
            0xF0, 0x10, 0x20, 0x40, 0x40,
            0xF0, 0x90, 0xF0, 0x90, 0xF0,
            0xF0, 0x90, 0xF0, 0x10, 0xF0,
            0xF0, 0x90, 0xF0, 0x90, 0x90,
            0xE0, 0x90, 0xE0, 0x90, 0xE0,
            0xF0, 0x80, 0x80, 0x80, 0xF0,
            0xE0, 0x90, 0x90, 0x90, 0xE0,
            0xF0, 0x80, 0xF0, 0x80, 0xF0,
            0xF0, 0x80, 0xF0, 0x80, 0x80])
        for i in range(0, 5 * 16):
            self.memory[i] = characters[i]

    def tick(self):
        if self.DT > 0:
            self.DT -= 1
        if self.ST > 0:
            self.ST -= 1

    def reset(self):
        self.running = True
        self.memory = bytearray(4096)
        self.V = bytearray(16)
        self.I = 0
        self.PC = 0x200
        self.opcode = 0x0000

        self.DT = 0
        self.ST = 0

        self.stack = []

        self.keys = bytearray(16)

        self.draw_flag = True

        self.load_characters()

        self.t0_clear_screen()

        self.last_tick = int(time.time() * 1000)

    def load_rom(self, program_file):
        with open(program_file, 'rb') as fin:
            barray = bytearray(fin.read())
            i = 0
            for b in barray:
                self.memory[0x200 + i] = b
                i += 1

    def debug_handle_input(self, breakpoint):
        if self.ui.stdscr.getch() == ord(' ') or breakpoint:
            while self.ui.stdscr.getch() == ord(' '):
                pass
            while True:
                key = self.ui.stdscr.getch()
                if key == ord('n'):
                    return True
                if key  == ord(' '):
                    return False

    def run(self, breakpoint=False):
        while True:
            self.opcode = self.memory[self.PC & 0xFFF] << 8 \
                    | self.memory[(self.PC + 1) & 0xFFF]
            self.PC += 2

            self.LOOKUP_TABLE[self.opcode & 0xF000]()

            if self.debug:
                breakpoint = self.debug_handle_input(breakpoint)
                self.ui.debug_show_registers(self)
                asm_str = asm.lookup_asm(self.opcode)
                if asm_str:
                    self.ui.debug_str(asm_str)
                else:
                    self.ui.debug_str(hex(self.opcode))

            if self.draw_flag:
                self.ui.display_framebuffer(self.memory[0xF00:])
                self.draw_flag = False
            now = int(time.time() * 1000)
            if now  - self.last_tick > self.clock_rate:
                self.tick()
                self.last_tick = now

def emulator_start(stdscr, rom_path, debug, frequency, breakpoint):
    ui = UI(stdscr, debug=debug)
    cpu = CPU(ui, debug=debug, frequency=frequency)
    cpu.load_rom(rom_path)
    cpu.run(breakpoint)

def main(argv):
    argp = argparse.ArgumentParser(description='Chip8 Emulator',
            prog='chippy8 emulator')
    argp.add_argument("rom", help="Rom file to load")
    argp.add_argument("-d", "--debug",
            action="store_true", help="Enable debug mode")
    argp.add_argument("-f", "--frequency", type=int, default=60,
            help="Set timers frequency (default 60Hz)")
    argp.add_argument("-b", "--breakpoint",
            action="store_true", help="Enable breakpoint at start")
    args = argp.parse_args(argv)
    sys.exit(curses.wrapper(emulator_start, args.rom, args.debug, args.frequency, args.breakpoint))
