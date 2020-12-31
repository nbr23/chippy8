CLS
LD V0, 0x00
LD V1, 0x00
LD V2, 0x00
LD V3, 0x00
LD V4, 0x02
LD V5, 0x03
LD V6, 0x05

main:
LD V7, 0x05
LD F, V4
CLS
DRW V0, V2, 0x5
LD F, V5
ADD V0, 0x05
DRW V0, V2, 0x5
SUB V0, V6
SNE V1, 0x00
CALL $increment_x
SNE V1, 0x01
CALL $decrement_x
SNE V3, 0x00
CALL $increment_y
SNE V3, 0x01
CALL $decrement_y
LD DT, V7
wait_tick:
LD V8, DT
SE V8, 0x00
JP $wait_tick
JP $main

increment_x:
SNE V0, 0x37
LD V1, 0x01
SE V0, 0x37
ADD V0, 0x01
RET

decrement_x:
SNE V0, 0x00
LD V1, 0x00
SE V0, 0x00
SUB V0, V1
RET

increment_y:
SNE V2, 0x1B
LD V3, 0x01
SE V2, 0x1B
ADD V2, 0x01
RET

decrement_y:
SNE V2, 0x00
LD V3, 0x00
SE V2, 0x00
SUB V2, V3
RET
