import parse
import argparse
import re


class Instruction:
    LABEL_DECL_PAT = re.compile('^[A-Z][A-Z0-9_]*:')
    LABEL_CALL_PAT = re.compile('^\\$[A-Z][A-Z0-9_]*$')

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
        0x00E0: Instruction('0x00E0', 'CLS'),
        0x00EE: Instruction('0x00EE', 'RET'),
        0x0FFF: Instruction('0x0{a}{b}{c}', 'SYS 0x{a}{b}{c}'),

        0x1FFF: Instruction('0x1{a}{b}{c}', 'JP 0x{a}{b}{c}'),
        0x2FFF: Instruction('0x2{a}{b}{c}', 'CALL 0x{a}{b}{c}'),
        0x3FFF: Instruction('0x3{a}{b}{c}', 'SE V{a}, 0x{b}{c}'),
        0x4FFF: Instruction('0x4{a}{b}{c}', 'SNE V{a}, 0x{b}{c}'),
        0x5FF0: Instruction('0x5{a}{b}0', 'SE V{a}, V{b}'),
        0x6FFF: Instruction('0x6{a}{b}{c}', 'LD V{a}, 0x{b}{c}'),
        0x7FFF: Instruction('0x7{a}{b}{c}', 'ADD V{a}, 0x{b}{c}'),

        0x8FF0: Instruction('0x8{a}{b}0', 'LD V{a}, V{b}'),
        0x8FF1: Instruction('0x8{a}{b}1', 'OR V{a}, V{b}'),
        0x8FF2: Instruction('0x8{a}{b}2', 'AND V{a}, V{b}'),
        0x8FF3: Instruction('0x8{a}{b}3', 'XOR V{a}, V{b}'),
        0x8FF4: Instruction('0x8{a}{b}4', 'ADD V{a}, V{b}'),
        0x8FF5: Instruction('0x8{a}{b}5', 'SUB V{a}, V{b}'),
        0x8F06: Instruction('0x8{a}06', 'SHR V{a}'),
        0x8FF6: Instruction('0x8{a}{b}6', 'SHR V{a}, V{b}'),
        0x8FF7: Instruction('0x8{a}{b}7', 'SUBN V{a}, V{b}'),
        0x8F0E: Instruction('0x8{a}0E', 'SHL V{a}'),
        0x8FFE: Instruction('0x8{a}{b}E', 'SHL V{a}, V{b}'),

        0x9FF0: Instruction('0x9{a}{b}0', 'SNE V{a}, V{b}'),
        0xAFFF: Instruction('0xA{a}{b}{c}', 'LD I, 0x{a}{b}{c}'),
        0xBFFF: Instruction('0xB{a}{b}{c}', 'JP V0, 0x{a}{b}{c}'),
        0xCFFF: Instruction('0xC{a}{b}{c}', 'RND V{a}, 0x{b}{c}'),
        0xDFFF: Instruction('0xD{a}{b}{c}', 'DRW V{a}, V{b}, 0x{c}'),

        0xEF9E: Instruction('0xE{a}9E', 'SKP V{a}'),
        0xEFA1: Instruction('0xE{a}A1', 'SKNP V{a}'),

        0xFF07: Instruction('0xF{a}07', 'LD V{a}, DT'),
        0xFF0A: Instruction('0xF{a}0A', 'LD V{a}, K'),
        0xFF15: Instruction('0xF{a}15', 'LD DT, V{a}'),
        0xFF18: Instruction('0xF{a}18', 'LD ST, V{a}'),
        0xFF1E: Instruction('0xF{a}1E', 'ADD I, V{a}'),
        0xFF29: Instruction('0xF{a}29', 'LD F, V{a}'),
        0xFF33: Instruction('0xF{a}33', 'LD B, V{a}'),
        0xFF55: Instruction('0xF{a}55', 'LD [I], V{a}'),
        0xFF65: Instruction('0xF{a}65', 'LD V{a}, [I]'),
}


def preprocess(file_in):
    src = []
    labels = {}
    i = 0
    with open(file_in) as fin:
        for line in fin:
            line = ' '.join(line.split(';')[0].split()).upper()\
                    .replace('0X', '0x')
            label = Instruction.LABEL_DECL_PAT.match(line)
            if label:
                labels[label.group()[:-1]] = 0x200 + i
            elif len(line) > 0:
                src.append(line)
                i += 2
    return src, labels


def label_substitute(line, labels):
    s = line.split()
    if (s[0] in ['JP', 'CALL', 'LD', 'SYS'] and
            Instruction.LABEL_CALL_PAT.match(s[-1])):
        line = ' '.join(s[0:-1] + ['0x{0:0{1}X}'.format(labels[s[-1][1:]], 3)])
    return line


# returns the opcode for an asm line
def lookup_opcode(asm_line):
    for i in INSTRUCTIONS_TABLE.values():
        if parse.search(i.asm_exp, asm_line) \
                and asm_line.split()[0] == i.asm_exp.split()[0] \
                and len(asm_line.split()) == len(i.asm_exp.split()):
            return i.get_opcode(asm_line)
    return None


# returns the asm for an opcode
def lookup_asm(opcode):
    opcode_str = '0x{0:0{1}X}'.format(opcode, 4)
    for i in INSTRUCTIONS_TABLE:
        if (i & opcode) == opcode:
            return INSTRUCTIONS_TABLE[i].get_asm(opcode_str)
    return None


def assemble(file_in, file_out, verbose=False):
    barray = []
    src_in, labels = preprocess(file_in)
    for line in src_in:
        line = label_substitute(line, labels)
        b = lookup_opcode(line)
        if b is not None:
            if verbose:
                print('0x{:04X} ;\t{}'.format(b, line))
            barray.append((b & 0xFF00) >> 8)
            barray.append((b & 0x00FF))
        else:
            print('Parse error: %s' % line)
    with open(file_out, 'wb') as fout:
        fout.write(bytearray(barray))


def disassemble(file_in, file_out, program_start=0x200, verbose=False):
    with open(file_in, 'rb') as fin:
        with open(file_out, 'w') as fout:
            barray = bytearray(fin.read())
            k = 0
            while k + 1 < len(barray):
                opcode = (barray[k] << 8) + barray[k + 1]
                asm_str = lookup_asm(opcode)
                if asm_str is not None:
                    if verbose:
                        print('0x{:04X} ;\t{}'.format(opcode, asm_str))
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


def main(argv):
    mod = argv[0]
    argv = argv[1:]
    if mod == 'asm':
        argp = argparse.ArgumentParser(description='Chip8 Assembler',
                prog='chippy8 asm')
        argp.add_argument("input", help="Input file")
        argp.add_argument("output", help="Output file")
        argp.add_argument("-v", "--verbose", default=False,
                action="store_true", help="Enable verbose mode")
        args = argp.parse_args(argv)
        assemble(args.input, args.output, args.verbose)
    else:
        argp = argparse.ArgumentParser(description='Chip8 Disassembler',
                prog='chippy8 disasm')
        argp.add_argument("input", help="Input file")
        argp.add_argument("output", help="Output file")
        argp.add_argument("-p", "--program_start", default='0x200',
                help="Set customer program start address (default 0x200).")
        argp.add_argument("-v", "--verbose", default=False,
                action="store_true", help="Enable verbose mode")
        args = argp.parse_args(argv)
        disassemble(args.input, args.output, int(args.program_start, 16),
                args.verbose)
