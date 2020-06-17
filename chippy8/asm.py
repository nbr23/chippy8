#! /usr/bin/python3

import parse
import argparse
import sys

class Instruction:
    def __init__(self, opcode_exp, asm_exp):
        self.opcode_exp = opcode_exp
        self.asm_exp = asm_exp

    # Returns the machine binary for the ASM input
    def get_opcode(self, asm):
        return int(self.opcode_exp.format(**parse.parse(self.asm_exp,
                                                        asm).named), 16)

    # Returns the human readable ASM string for the instruction
    def get_asm(self, opcode):
        return self.asm_exp.format(**parse.parse(self.opcode_exp,
                                                 opcode).named)

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
    Instruction('0x8{a}{b}6', 'SHR V{a}, V{b}'),
    Instruction('0x8{a}{b}7', 'SUBN V{a}, V{b}'),
    Instruction('0x8{a}0E', 'SHL V{a}'),
    Instruction('0x8{a}{b}E', 'SHL V{a}, V{b}'),

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
                and asm_line.split()[0] == i.asm_exp.split()[0] \
                and len(asm_line.split()) == len(i.asm_exp.split()):
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

def disassemble(file_in, file_out, program_start=0x200):
    with open(file_in, 'rb') as fin:
        with open(file_out, 'w') as fout:
            barray = bytearray(fin.read())
            k = 0
            while k + 1 < len(barray):
                opcode = (barray[k] << 8) + barray[k + 1]
                asm_str = lookup_asm(opcode)
                if asm_str is not None:
                    if k % 8 == 0:
                        fout.write('%s ; %s\n' % (asm_str,
                            hex(program_start + k)))
                    else:
                        fout.write('%s\n' % asm_str)
                else:
                    fout.write(';%s: invalid instruction (@%s)\n'
                            % (hex(opcode), hex(program_start + k)))
                    print('Parse error: %s' % hex(opcode))
                k += 2

def print_help(argv):
    print('Usage:\n\tchippy8 asm -a file_in.c8 file_out\t# Assemble')
    print('\tchippy8 asm -d file_in file_out.c8\t# Disassemble')

def main(argv):
    argp = argparse.ArgumentParser(description='Chip8 Assembler/Disassembler',
            prog='chippy8 asm')
    argp.add_argument("-i", "--input", required=True, help="Input file")
    argp.add_argument("-o", "--output", required=True, help="Output file")
    argp.add_argument("-d", "--disassemble",
            action="store_true", help="Disassemble input to output")
    argp.add_argument("-a", "--assemble",
            action="store_true", help="Assemble input to output")
    argp.add_argument("-p", "--program_start", default='0x200',
            help="Set customer program start address (default 0x200). \
                    Ignored with --assemble")
    args = argp.parse_args(argv)

    if args.disassemble and not args.assemble:
        disassemble(args.input, args.output, int(args.program_start, 16))
    elif args.assemble:
        assemble(args.input, args.output)
    else:
        args.print_help()
