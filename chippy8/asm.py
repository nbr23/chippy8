#! /usr/bin/python3

import parse
import sys

class Instruction:
    def __init__(self, opcode_exp, asm_exp):
        self.opcode_exp = opcode_exp
        self.asm_exp = asm_exp

    # Returns the machine binary for the ASM input
    def get_opcode(self, asm):
        return int(self.opcode_exp.format(**parse.parse(self.asm_exp, asm).named), 16)

    # Returns the human readable ASM string for the instruction
    def get_asm(self, opcode):
        return self.asm_exp.format(**parse.parse(self.opcode_exp, opcode).named)

    def clean_asm_input(s):
        s = s.split(';')[0]
        return ' '.join(s.split()).upper().replace('0X', '0x')


INSTRUCTIONS_TABLE = {
    Instruction('0x00E0', 'CLS'),
    Instruction('0x00EE', 'RET'),
    Instruction('0x0{a}{b}{c}', 'SYS 0x{a}{b}{c}'),

    Instruction('0x1{a}{b}{c}', 'JP 0x{a}{b}{c}'),
    Instruction('0x2{a}{b}{c}', 'CALL 0x{a}{b}{c}'),
    Instruction('0x3{a}{b}{c}', 'SE V{a}, 0x{b}{c}'),
    Instruction('0x4{a}{b}{c}', 'SNE V{a}, 0x{b}{c}'),
    Instruction('0x5{a}{b}0', 'SE V{a}, V{b}'),
    Instruction('0x6{a}{b}{c}', 'LD V{a}, 0x{b}{c}'),
    Instruction('0x7{a}{b}{c}', 'ADD V{a}, 0x{b}{c}'),

    Instruction('0x8{a}{b}0', 'LD V{a}, V{b}'),
    Instruction('0x8{a}{b}1', 'OR V{a}, V{b}'),
    Instruction('0x8{a}{b}2', 'AND V{a}, V{b}'),
    Instruction('0x8{a}{b}3', 'XOR V{a}, V{b}'),
    Instruction('0x8{a}{b}4', 'ADD V{a}, V{b}'),
    Instruction('0x8{a}{b}5', 'SUB V{a}, V{b}'),
    Instruction('0x8{a}06', 'SHR V{a}'),
    Instruction('0x8{a}{b}7', 'SUBN V{a}, V{b}'),
    Instruction('0x8{a}0E', 'SHL V{a}'),

    Instruction('0x9{a}{b}0', 'SNE V{a}, V{b}'),
    Instruction('0xA{a}{b}{c}', 'LD I, 0x{a}{b}{c}'),
    Instruction('0xB{a}{b}{c}', 'JP V0, 0x{a}{b}{c}'),
    Instruction('0xC{a}{b}{c}', 'RND V{a}, 0x{b}{c}'),
    Instruction('0xD{a}{b}{c}', 'DRW V{a}, V{b}, 0x{c}'),

    Instruction('0xE{a}9E', 'SKP V{a}'),
    Instruction('0xE{a}A1', 'SKNP V{a}'),

    Instruction('0xF{a}07', 'LD V{a}, DT'),
    Instruction('0xF{a}0A', 'LD V{a}, K'),
    Instruction('0xF{a}15', 'LD DT, V{a}'),
    Instruction('0xF{a}18', 'LD ST, V{a}'),
    Instruction('0xF{a}1E', 'ADD I, V{a}'),
    Instruction('0xF{a}29', 'LD F, V{a}'),
    Instruction('0xF{a}33', 'LD B, V{a}'),
    Instruction('0xF{a}55', 'LD [I], V{a}'),
    Instruction('0xF{a}65', 'LD V{a}, [I]'),
}

# returns the opcode for an asm line
def lookup_opcode(asm_line):
    for i in INSTRUCTIONS_TABLE:
        if parse.search(i.asm_exp, asm_line) \
                and asm_line.split()[0] == i.asm_exp.split()[0]:
            return i.get_opcode(asm_line)
    return None

# returns the asm for an opcode
def lookup_asm(opcode):
    opcode = '0x{0:0{1}X}'.format(opcode, 4)
    for i in INSTRUCTIONS_TABLE:
        if parse.search(i.opcode_exp, opcode):
            s = i.get_asm(opcode)
            return i.get_asm(opcode)
    return None

def assemble(file_in, file_out):
    barray = []
    k = 0
    with open(file_in) as fin:
        for line in fin:
            line = Instruction.clean_asm_input(line)
            if line == '':
                continue
            b = lookup_opcode(line)
            if b is not None:
                barray.append((b & 0xFF00)>>8)
                barray.append((b & 0x00FF))
            else:
                print('Parse error: %s' % line)
            k += 1
    with open(file_out, 'wb') as fout:
        fout.write(bytearray(barray))

def disassemble(file_in, file_out):
    with open(file_in, 'rb') as fin:
        with open(file_out, 'w') as fout:
            barray = bytearray(fin.read())
            k = 0
            while k + 1 < len(barray):
                asm_str = lookup_asm((barray[k] << 8) + barray[k + 1])
                if asm_str is not None:
                    if k % 8 == 0:
                        fout.write('%s ; %s\n' % (asm_str, hex(0x200 + k)))
                    else:
                        fout.write('%s\n' % asm_str)
                else:
                    fout.write(';%s: invalid instruction (@%s)\n'
                            % (opcode, hex(0x200 + k)))
                    print('Parse error: %s' % opcode)
                k += 2

def print_help(argv):
    print('Usage:\n\t%s -a file_in.c8 file_out\t# Assemble' % argv[0])
    print('\t%s -d file_in file_out.c8\t# Disassemble' % argv[0])

def main():
    if len(sys.argv) <= 3:
        print_help(sys.argv)
        return 1
    if sys.argv[1] == '-d':
        disassemble(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == '-a':
        assemble(sys.argv[2], sys.argv[3])
    else:
        print_help(sys.argv)

if __name__ == "__main__":
    sys.exit(main())
