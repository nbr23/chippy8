import chippy8.asm
import chippy8.emulator
import sys

def print_usage():
    print('Usage:\n  chippy8 MODULE\n\nModules:\n' \
            '\t- asm: Assemble CHIP8\n' \
            '\t- disasm: Disassemble CHIP8\n' \
            '\t- emulator: CHIP8 emulator.')

def main():
    if len(sys.argv) < 2:
        print_usage()
        return 1
    if sys.argv[1] == 'asm':
        return chippy8.asm.main(sys.argv[1:])
    elif sys.argv[1] == 'disasm':
        return chippy8.asm.main(sys.argv[1:])
    elif sys.argv[1] == 'emulator':
        return chippy8.emulator.main(sys.argv[2:])
    print_usage()

if __name__ == "__main__":
    sys.exit(main())
