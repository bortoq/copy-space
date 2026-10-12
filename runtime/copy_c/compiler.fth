\ C subset compiler. All source parsing and target emission run in Forth.
\ Target bit addresses; int values use LSB-first fields in MSB-first bytes.
decimal
1048576 constant cc-source-max
128 constant cc-layer-max
18176 constant cc-layer-bits
2272 constant cc-layer-bytes
131072 constant cc-data-base
262144 constant cc-code-base
163840 constant cc-constant-base
196608 constant cc-table-base
151552 constant cc-a
151584 constant cc-b
151616 constant cc-r
151648 constant cc-carry
151680 constant cc-tmp
151712 constant cc-jaddr
151744 constant cc-lret
151776 constant cc-load-status
151808 constant cc-output
151840 constant cc-call-args
152096 constant cc-saved-result
152128 constant cc-sp
152192 constant cc-stack-message
152384 constant cc-pointer-message
153024 constant cc-mul-a
153056 constant cc-mul-b
153088 constant cc-mul-result
153120 constant cc-mul-return
153216 constant cc-div-n
153248 constant cc-div-d
153280 constant cc-div-q
153312 constant cc-div-r
153344 constant cc-div-return
153376 constant cc-div-count
153408 constant cc-div-carry
153440 constant cc-div-sign-q
153472 constant cc-div-sign-r
153504 constant cc-div-signed
153536 constant cc-div-mod
153600 constant cc-shift-message
153856 constant cc-divide-message
154112 constant cc-shift-value
154144 constant cc-shift-count
154176 constant cc-shift-return
154208 constant cc-shift-right
154240 constant cc-shift-signed
8388608 constant cc-stack-base
16384 constant cc-frame-bits
16760832 constant cc-stack-last

\ Small local-name compiler over pForth's existing local primitives.
create cc-local-names 256 allot
variable cc-local-count
: cc-local-name ( i -- addr ) 32 * cc-local-names + ;
create cc-local-fetch-xts
' (1_LOCAL@) , ' (2_LOCAL@) , ' (3_LOCAL@) , ' (4_LOCAL@) ,
' (5_LOCAL@) , ' (6_LOCAL@) , ' (7_LOCAL@) , ' (8_LOCAL@) ,
: cc-local-hook ( word -- flag )
  dup count s" ;" compare 0= if
    drop compile (local.exit) 0 local-compiler ! 0 exit
  then
  dup count s" exit" compare 0= if
    drop compile (local.exit) compile exit -1 exit
  then
  cc-local-count @ 0 do
    dup count i cc-local-name count compare 0= if
      drop i cells cc-local-fetch-xts + @ compile, -1 unloop exit
    then
  loop drop 0 ;
: L{ ( compilation: names } -- )
  0 cc-local-count !
  begin bl lword dup count s" }" compare while
    dup c@ 31 > cc-local-count @ 8 >= or if -1 throw then
    count cc-local-count @ cc-local-name place 1 cc-local-count +!
  repeat drop
  cc-local-count @ [compile] literal compile (local.entry)
  ['] cc-local-hook local-compiler ! ; immediate

create cc-source cc-source-max 1+ allot
variable cc-length
variable cc-pos
variable cc-token
variable cc-token-start
variable cc-token-size
variable cc-number
variable cc-number-type
variable cc-unevaluated
: cc-fail ( addr len -- )
  ." copy-c error at byte " cc-token-start @ . type cr 2 cs-exit ;
: cc-limit ( flag -- ) if s" capacity exceeded" cc-fail then ;

create cc-image 16384 cc-layer-max cc-layer-bytes * + allot
cc-image 16384 cc-layer-max cc-layer-bytes * + 0 fill
create cc-record 37 allot
create cc-reversed 256 allot
: cc-prepare-reverse
  256 0 do 0 i 8 0 do swap 2 * over 1 and + swap 1 rshift loop
    drop cc-reversed i + c! loop ;
cc-prepare-reverse

: cc-bits! ( value width position buffer -- )
  0 0 0 L{ value width position buffer part shift mask }
  begin width while
    8 position 7 and - width min 5 (local!)
    8 position 7 and - part - 6 (local!)
    1 part lshift 1- shift lshift 7 (local!)
    buffer position 3 rshift + dup c@ mask invert and
    value 255 and cc-reversed + c@ position 7 and rshift mask and or swap c!
    value part rshift 1 (local!)
    position part + 3 (local!) width part - 2 (local!)
  repeat ;
: cc-value! ( value bits target -- ) cc-data-base - cc-image cc-bits! ;

variable cc-row-n
variable cc-row-d
variable cc-row-s
variable cc-row-bit
variable cc-row-buffer
: cc-row-at ( n dst src bit buffer -- )
  cc-row-buffer ! cc-row-bit ! cc-row-s ! cc-row-d ! cc-row-n !
  cc-row-n @ 23 cc-row-bit @ cc-row-buffer @ cc-bits!
  cc-row-d @ 24 cc-row-bit @ 23 + cc-row-buffer @ cc-bits!
  cc-row-s @ 24 cc-row-bit @ 47 + cc-row-buffer @ cc-bits! ;
variable cc-emission-base
variable cc-emission-buffer
: cc-row ( n dst src target-bit -- )
  cc-unevaluated @ if 2drop 2drop exit then
  cc-emission-base @ - cc-emission-buffer @ cc-row-at ;

variable cc-layer
variable cc-slot
variable cc-constants
variable cc-data
variable cc-origin
: cc-current ( -- target ) cc-layer @ cc-layer-bits * cc-origin @ + ;
: cc-new 1 cc-layer +! cc-layer @ cc-layer-max >= cc-limit 3 cc-slot ! ;
: cc-end ( target -- )
  cc-layer-bits 0 rot cc-current 255 71 * + cc-row ;
: cc-jump ( target -- ) cc-unevaluated @ if drop exit then cc-end cc-new ;
: cc-room ( count -- ) cc-slot @ + 255 > if
    cc-current cc-layer-bits + cc-jump then ;
: cc-raw-op ( n dst src -- )
  1 cc-room cc-current cc-slot @ 71 * + cc-row 1 cc-slot +! ;
: cc-frame? ( address -- flag )
  dup cc-data-base >= swap cc-data-base cc-frame-bits + < and ;
: cc-frame-extra ( address -- count ) cc-frame? if 1 else 0 then ;
: cc-frame-address ( address -- address )
  dup cc-frame? if cc-data-base - cc-stack-base + then ;
: cc-op ( n dst src -- ) 0 L{ n dst src target }
  cc-unevaluated @ if exit then
  1 dst cc-frame-extra + src cc-frame-extra + cc-room
  cc-slot @ dst cc-frame-extra + src cc-frame-extra + 4 (local!)
  dst cc-frame? if 10 target 71 * 37 + cc-sp 14 + cc-raw-op then
  src cc-frame? if 10 target 71 * 61 + cc-sp 14 + cc-raw-op then
  n dst cc-frame-address src cc-frame-address cc-raw-op ;
: cc-boundary ( -- target )
  cc-slot @ 3 <> if cc-current cc-layer-bits + cc-jump then cc-current ;
: cc-cell ( -- target )
  cc-data @ 32 cc-data +! cc-data @ 147456 > cc-limit ;
: cc-const ( value -- target )
  cc-constants @ 32 cc-constants +!
  cc-constants @ 180224 > cc-limit >r 32 r@ cc-value! r> ;
: cc-patch ( target value -- ) cc-unevaluated @ if 2drop exit then swap 32 swap cc-value! ;
: cc-dynamic ( source -- )
  1 cc-room 24 18152 rot cc-op 0 cc-jump ;

\ Patch the active instruction, then perform its LUT read in the same tick.
: cc-lut1 ( dst base a -- ) L{ dst base a }
  2 a cc-frame-extra + dst cc-frame-extra + cc-room
  1 cc-slot @ 1+ a cc-frame-extra + dst cc-frame-extra + 71 * 47 + a cc-op
  1 dst base cc-op ;
: cc-lut2 ( dst base a b -- ) 0 L{ dst base a b target }
  3 a cc-frame-extra + b cc-frame-extra + dst cc-frame-extra + cc-room
  cc-slot @ 2 + a cc-frame-extra + b cc-frame-extra + dst cc-frame-extra + 5 (local!)
  1 target 71 * 47 + a cc-op
  1 target 71 * 48 + b cc-op 1 dst base cc-op ;
: cc-lut3 ( width dst base a b c stride -- ) 0 L{ width dst base a b c stride target }
  4 a cc-frame-extra + b cc-frame-extra + c cc-frame-extra + dst cc-frame-extra + cc-room
  cc-slot @ 3 + a cc-frame-extra + b cc-frame-extra + c cc-frame-extra + dst cc-frame-extra + 8 (local!)
  1 target 71 * 47 + stride + a cc-op
  1 target 71 * 48 + stride + b cc-op
  1 target 71 * 49 + stride + c cc-op
  width dst base cc-op ;
: cc-branch ( condition -- table ) L{ condition }
  cc-constants @ 63 + 63 invert and cc-constants !
  0 cc-const >r 0 cc-const drop
  3 condition cc-frame-extra + cc-room
  1 cc-slot @ 1+ condition cc-frame-extra + 71 * 52 + condition cc-op
  24 cc-jaddr r@ cc-op cc-jaddr cc-dynamic r> ;

variable cc-zero
variable cc-one
variable cc-add-entry
variable cc-sub-entry
variable cc-eq-entry
variable cc-lt-entry
variable cc-ult-entry
variable cc-and-entry
variable cc-or-entry
variable cc-xor-entry
variable cc-not-entry
variable cc-shl-entry
variable cc-shr-entry
variable cc-sar-entry
variable cc-mul-entry
variable cc-div-entry
variable cc-udiv-entry
variable cc-mod-entry
variable cc-umod-entry
variable cc-div-core
variable cc-div-error-table
variable cc-shift-error-table
variable cc-shift-core
variable cc-bool-entry
variable cc-output-entry
variable cc-stack-error-entry
variable cc-pointer-check-entry
variable cc-pointer-error-table
variable cc-library-layer
variable cc-library-constants
variable cc-library-end
: cc-full-add
  32 0 do
    2 cc-tmp cc-table-base cc-a i + cc-b i + cc-carry 1 cc-lut3
    1 cc-r i + cc-tmp cc-op 1 cc-carry cc-tmp 1+ cc-op
  loop cc-lret cc-dynamic ;
: cc-library-call ( entry -- )
  1 cc-room cc-current cc-layer-bits + cc-const
  24 cc-lret rot cc-op cc-jump ;
: cc-message! ( addr len target -- ) L{ text bytes target }
  bytes 0 ?do text i + c@ cc-reversed + c@ 8 target i 8 * + cc-value! loop
  10 cc-reversed + c@ 8 target bytes 8 * + cc-value! ;
: cc-bit-library ( table -- ) L{ table }
  32 0 do cc-r i + table cc-a i + cc-b i + cc-lut2 loop cc-lret cc-dynamic ;
: cc-shift-library
  cc-current cc-shift-core !
  24 cc-shift-return cc-lret cc-op
  32 cc-shift-value cc-a cc-op 32 cc-shift-count cc-b cc-op
  1 cc-carry cc-zero @ cc-op
  32 5 do cc-carry cc-table-base 24 + cc-carry cc-b i + cc-lut2 loop
  cc-carry cc-branch dup cc-shift-error-table ! cc-current cc-patch
  32 cc-a cc-shift-count cc-op cc-bool-entry @ cc-library-call
  cc-r cc-branch 0 0 0 L{ zero-table head direction-table skip }
  zero-table 32 + cc-current cc-patch cc-current 2 (local!)
  cc-shift-right cc-branch 3 (local!) direction-table cc-current cc-patch
  31 cc-shift-value 1+ cc-shift-value cc-op 1 cc-shift-value cc-zero @ cc-op
  cc-current 18152 + 4 (local!) 0 cc-jump
  direction-table 32 + cc-current cc-patch
  31 cc-shift-value cc-shift-value 1+ cc-op
  cc-shift-value 31 + cc-table-base 48 + cc-shift-value 31 + cc-shift-signed cc-lut2
  cc-boundary 24 skip cc-value!
  32 cc-a cc-shift-count cc-op 32 cc-b cc-one @ cc-op
  cc-sub-entry @ cc-library-call 32 cc-shift-count cc-r cc-op
  32 cc-a cc-shift-count cc-op cc-bool-entry @ cc-library-call
  cc-r cc-branch dup 32 + head cc-patch cc-current cc-patch
  zero-table cc-current cc-patch
  32 cc-r cc-shift-value cc-op 24 cc-lret cc-shift-return cc-op cc-lret cc-dynamic
  cc-current cc-shl-entry !
  1 cc-shift-right cc-zero @ cc-op 1 cc-shift-signed cc-zero @ cc-op cc-shift-core @ cc-jump
  cc-current cc-shr-entry !
  1 cc-shift-right cc-one @ cc-op 1 cc-shift-signed cc-zero @ cc-op cc-shift-core @ cc-jump
  cc-current cc-sar-entry !
  1 cc-shift-right cc-one @ cc-op 1 cc-shift-signed cc-one @ cc-op cc-shift-core @ cc-jump ;
: cc-multiply-library
  24 cc-mul-return cc-lret cc-op
  32 cc-mul-a cc-a cc-op 32 cc-mul-b cc-b cc-op
  32 cc-mul-result cc-zero @ cc-op
  cc-boundary L{ head }
  32 cc-a cc-mul-b cc-op cc-bool-entry @ cc-library-call
  cc-r cc-branch >r r@ 32 + cc-current cc-patch
  cc-mul-b cc-branch >r r@ 32 + cc-current cc-patch
  32 cc-a cc-mul-result cc-op 32 cc-b cc-mul-a cc-op
  cc-add-entry @ cc-library-call 32 cc-mul-result cc-r cc-op
  cc-boundary r> swap cc-patch
  31 cc-mul-a 1+ cc-mul-a cc-op 1 cc-mul-a cc-zero @ cc-op
  31 cc-mul-b cc-mul-b 1+ cc-op 1 cc-mul-b 31 + cc-zero @ cc-op
  head cc-jump r> cc-current cc-patch
  32 cc-r cc-mul-result cc-op 24 cc-lret cc-mul-return cc-op cc-lret cc-dynamic ;
: cc-div-absolute ( value -- ) L{ value }
  value 31 + cc-branch >r r@ 32 + cc-current cc-patch
  32 cc-a cc-zero @ cc-op 32 cc-b value cc-op
  cc-sub-entry @ cc-library-call 32 value cc-r cc-op
  cc-boundary r> swap cc-patch ;
: cc-division-library
  cc-current cc-div-core !
  24 cc-div-return cc-lret cc-op
  32 cc-div-n cc-a cc-op 32 cc-div-d cc-b cc-op
  32 cc-div-q cc-zero @ cc-op 32 cc-div-r cc-zero @ cc-op
  32 cc-div-count 32 cc-const cc-op
  1 cc-div-sign-q cc-zero @ cc-op 1 cc-div-sign-r cc-zero @ cc-op
  32 cc-a cc-div-d cc-op cc-bool-entry @ cc-library-call
  cc-r cc-branch dup cc-div-error-table ! 32 + cc-current cc-patch
  cc-div-signed cc-branch >r r@ 32 + cc-current cc-patch
  1 cc-div-sign-r cc-div-n 31 + cc-op
  cc-div-sign-q cc-table-base 16 + cc-div-n 31 + cc-div-d 31 + cc-lut2
  cc-div-n cc-div-absolute cc-div-d cc-div-absolute
  cc-boundary r> swap cc-patch
  cc-boundary 0 0 0 0 L{ head carry-table compare-table selection-table selection-field }
  1 cc-div-carry cc-div-r 31 + cc-op
  31 cc-div-r 1+ cc-div-r cc-op 1 cc-div-r cc-div-n 31 + cc-op
  31 cc-div-n 1+ cc-div-n cc-op 1 cc-div-n cc-zero @ cc-op
  31 cc-div-q 1+ cc-div-q cc-op 1 cc-div-q cc-zero @ cc-op
  cc-div-carry cc-branch 2 (local!) carry-table cc-current cc-patch
  32 cc-a cc-div-r cc-op 32 cc-b cc-div-d cc-op
  cc-ult-entry @ cc-library-call cc-r cc-branch 3 (local!)
  compare-table cc-current cc-patch carry-table 32 + cc-current cc-patch
  32 cc-a cc-div-r cc-op 32 cc-b cc-div-d cc-op
  cc-sub-entry @ cc-library-call 32 cc-div-r cc-r cc-op
  1 cc-div-q cc-one @ cc-op
  cc-boundary compare-table 32 + swap cc-patch
  32 cc-a cc-div-count cc-op 32 cc-b cc-one @ cc-op
  cc-sub-entry @ cc-library-call 32 cc-div-count cc-r cc-op
  32 cc-a cc-div-count cc-op cc-bool-entry @ cc-library-call
  cc-r cc-branch dup 32 + head cc-patch cc-current cc-patch
  cc-div-mod cc-branch 4 (local!) selection-table cc-current cc-patch
  32 cc-r cc-div-q cc-op 1 cc-div-carry cc-div-sign-q cc-op
  cc-current 18152 + 5 (local!) 0 cc-jump
  selection-table 32 + cc-current cc-patch
  32 cc-r cc-div-r cc-op 1 cc-div-carry cc-div-sign-r cc-op
  cc-boundary 24 selection-field cc-value!
  cc-div-carry cc-branch >r r@ 32 + cc-current cc-patch
  32 cc-b cc-r cc-op 32 cc-a cc-zero @ cc-op
  cc-sub-entry @ cc-library-call cc-boundary r> swap cc-patch
  24 cc-lret cc-div-return cc-op cc-lret cc-dynamic
  cc-current cc-udiv-entry !
  1 cc-div-signed cc-zero @ cc-op 1 cc-div-mod cc-zero @ cc-op cc-div-core @ cc-jump
  cc-current cc-div-entry !
  1 cc-div-signed cc-one @ cc-op 1 cc-div-mod cc-zero @ cc-op cc-div-core @ cc-jump
  cc-current cc-umod-entry !
  1 cc-div-signed cc-zero @ cc-op 1 cc-div-mod cc-one @ cc-op cc-div-core @ cc-jump
  cc-current cc-mod-entry !
  1 cc-div-signed cc-one @ cc-op 1 cc-div-mod cc-one @ cc-op cc-div-core @ cc-jump ;
: cc-library
  cc-code-base cc-origin ! cc-data-base cc-emission-base ! cc-image cc-emission-buffer !
  0 cc-layer ! 3 cc-slot ! cc-constant-base cc-constants !
  cc-stack-base 32 cc-sp cc-value!
  s" copy-c: stack overflow" 0 do
    dup i + c@ cc-reversed + c@ 8 cc-stack-message i 8 * + cc-value!
  loop drop
  10 cc-reversed + c@ 8 cc-stack-message 176 + cc-value!
  s" copy-c: pointer error" 0 do
    dup i + c@ cc-reversed + c@ 8 cc-pointer-message i 8 * + cc-value!
  loop drop
  10 cc-reversed + c@ 8 cc-pointer-message 168 + cc-value!
  s" copy-c: shift error" cc-shift-message cc-message!
  s" copy-c: divide by zero" cc-divide-message cc-message!
  0 cc-const cc-zero ! 1 cc-const cc-one !
  8 0 do
    i 1 and i 1 rshift 1 and + i 2 rshift 1 and +
    2 cc-table-base i 2 * + cc-value!
    i 1 and i 1 rshift 1 and = if i 2 rshift 1 and
      else i 1 rshift 1 and then
    1 cc-table-base 32 + i + cc-value!
  loop
  4 0 do
    i 1 and i 1 rshift 1 and xor
    1 cc-table-base 16 + i + cc-value!
    i 1 and i 1 rshift 1 and or
    1 cc-table-base 24 + i + cc-value!
    i 1 and i 1 rshift 1 and and
    1 cc-table-base 48 + i + cc-value!
  loop
  1 1 cc-table-base 40 + cc-value!
  cc-current cc-add-entry ! 1 cc-carry cc-zero @ cc-op cc-full-add
  cc-current cc-sub-entry !
  32 0 do cc-b i + cc-table-base 40 + cc-b i + cc-lut1 loop
  1 cc-carry cc-one @ cc-op cc-full-add
  cc-current cc-eq-entry ! 32 cc-r cc-zero @ cc-op
  1 cc-carry cc-zero @ cc-op
  32 0 do
    cc-tmp cc-table-base 16 + cc-a i + cc-b i + cc-lut2
    cc-carry cc-table-base 24 + cc-carry cc-tmp cc-lut2
  loop cc-r cc-table-base 40 + cc-carry cc-lut1 cc-lret cc-dynamic
  cc-current cc-lt-entry ! 32 cc-r cc-zero @ cc-op
  31 0 do
    1 cc-r cc-table-base 32 + cc-a i + cc-b i + cc-r 0 cc-lut3
  loop
  cc-tmp cc-table-base 40 + cc-a 31 + cc-lut1
  cc-tmp 1+ cc-table-base 40 + cc-b 31 + cc-lut1
  1 cc-r cc-table-base 32 + cc-tmp cc-tmp 1+ cc-r 0 cc-lut3
  cc-lret cc-dynamic
  cc-current cc-ult-entry ! 32 cc-r cc-zero @ cc-op
  32 0 do 1 cc-r cc-table-base 32 + cc-a i + cc-b i + cc-r 0 cc-lut3 loop
  cc-lret cc-dynamic
  cc-current cc-bool-entry ! 32 cc-r cc-zero @ cc-op
  32 0 do cc-r cc-table-base 24 + cc-r cc-a i + cc-lut2 loop
  cc-lret cc-dynamic
  cc-current cc-pointer-check-entry ! 1 cc-carry cc-zero @ cc-op
  2 0 do cc-carry cc-table-base 24 + cc-carry cc-a i + cc-lut2 loop
  32 21 do cc-carry cc-table-base 24 + cc-carry cc-a i + cc-lut2 loop
  cc-tmp cc-table-base 40 + cc-a 20 + cc-lut1
  cc-carry cc-table-base 24 + cc-carry cc-tmp cc-lut2
  cc-carry cc-branch dup cc-pointer-error-table ! cc-current cc-patch
  cc-lret cc-dynamic
  cc-current cc-and-entry ! cc-table-base 48 + cc-bit-library
  cc-current cc-or-entry ! cc-table-base 24 + cc-bit-library
  cc-current cc-xor-entry ! cc-table-base 16 + cc-bit-library
  cc-current cc-not-entry !
  32 0 do cc-r i + cc-table-base 40 + cc-a i + cc-lut1 loop cc-lret cc-dynamic
  cc-shift-library
  cc-current cc-mul-entry ! cc-multiply-library
  cc-division-library
  cc-current cc-output-entry !
  32 0 do 1 cc-output i 8 / 8 * 7 + i 7 and - +
    cc-r i + cc-op loop
  cc-current cc-layer-bits + cc-jump
  32 cc-output 0 cc-current 142 + cc-row
  65536 cc-jump
  cc-current cc-stack-error-entry !
  184 cc-stack-message 0 cc-current 142 + cc-row
  65536 cc-jump
  cc-pointer-error-table @ 32 + cc-current cc-patch
  176 cc-pointer-message 0 cc-current 142 + cc-row
  65536 cc-jump
  cc-shift-error-table @ 32 + cc-current cc-patch
  160 cc-shift-message 0 cc-current 142 + cc-row 65536 cc-jump
  cc-div-error-table @ cc-current cc-patch
  184 cc-divide-message 0 cc-current 142 + cc-row 65536 cc-jump
  cc-layer @ cc-library-layer ! cc-constants @ cc-library-constants !
  cc-current cc-library-end ! ;
cc-library

\ This small guard is installed before the large payload is read. Its code
\ is constant; only the expected count and success entry depend on the C.
4128768 constant cc-guard-data
4194304 constant cc-guard-code
create cc-guard-image cc-layer-bytes 2 * allot
create cc-guard-constants 36 allot
create cc-prelude 16384 allot
create cc-chunk 6 allot
variable cc-prelude-bytes
variable cc-preparing
: cc-three ( address -- value )
  dup c@ cc-reversed + c@ over 1+ c@ cc-reversed + c@ 8 lshift or
  swap 2 + c@ cc-reversed + c@ 16 lshift or ;
: cc-install ( target source bytes -- ) L{ target source bytes }
  bytes 0 ?do
    cc-chunk 6 0 fill source i + cc-chunk bytes i - 6 min cmove
    0 6 0 do cc-chunk i + c@ or loop
    if
      cc-record 37 0 fill
      48 target i 8 * + 18270 0 cc-record cc-row-at
      0 cc-chunk cc-three cc-chunk 3 + cc-three 71 cc-record cc-row-at
      284 0 18688 213 cc-record cc-row-at
      cc-preparing @ if
        cc-prelude-bytes @ 37 + 16384 > cc-limit
        cc-record cc-prelude cc-prelude-bytes @ + 37 cmove
        37 cc-prelude-bytes +!
      else cc-record 37 cs-write 37 <> if 1 cs-exit then then
    then
  6 +loop ;
: cc-prepare-guard
  cc-guard-image cc-layer-bytes 2 * 0 fill cc-guard-constants 36 0 fill
  4 0 do
    i 1 and i 1 rshift 1 and xor 1 32 i + cc-guard-constants cc-bits!
    i 1 and i 1 rshift 1 and or 1 40 i + cc-guard-constants cc-bits!
  loop
  cc-guard-code cc-layer-bits + 32 96 cc-guard-constants cc-bits!
  s" copy-c: load error" cc-guard-constants 16 + swap cmove
  10 cc-guard-constants 34 + c!
  cc-guard-code cc-origin ! cc-guard-code cc-emission-base !
  cc-guard-image cc-emission-buffer ! 0 cc-layer ! 4 cc-slot !
  1 cc-carry 65536 cc-op
  24 0 do
    cc-tmp cc-guard-data 32 + cc-load-status i + cc-guard-data i + cc-lut2
    cc-carry cc-guard-data 40 + cc-carry cc-tmp cc-lut2
  loop
  1 cc-slot @ 1+ 71 * 52 + cc-carry cc-op
  24 cc-jaddr cc-guard-data 64 + cc-op cc-jaddr cc-dynamic
  152 cc-guard-data 128 + 0 cc-current 142 + cc-row
  65536 cc-end
  -1 cc-preparing ! 0 cc-prelude-bytes !
  cc-guard-code cc-guard-image cc-layer-bytes 2 * cc-install
  0 cc-preparing !
  cc-code-base cc-origin ! cc-data-base cc-emission-base ! cc-image cc-emission-buffer !
  cc-library-layer @ cc-layer ! 3 cc-slot ! ;
cc-prepare-guard

: cc-invoke ( lhs rhs entry -- result ) L{ lhs rhs entry }
  3 lhs cc-frame-extra + rhs cc-frame-extra + cc-room
  32 cc-a lhs cc-op 32 cc-b rhs cc-op
  cc-current cc-layer-bits + cc-const 24 cc-lret rot cc-op
  entry cc-jump cc-cell dup 32 swap cc-r cc-op ;
defer cc-check-truth
: cc-truth ( value -- result ) dup cc-check-truth cc-zero @ cc-bool-entry @ cc-invoke ;
: cc-invert ( value -- result ) cc-cell L{ value result }
  32 result cc-zero @ cc-op
  result cc-table-base 40 + value cc-lut1 result ;
\ Lexer: names and numbers refer to source bytes, never to host parsing.
: cc-peek cc-pos @ cc-length @ < if cc-source cc-pos @ + c@ else -1 then ;
: cc-step 1 cc-pos +! ;
: cc-within ( n lo hi -- flag ) over - >r - r> u< ;
: cc-alpha ( c -- flag )
  dup 97 123 cc-within over 65 91 cc-within or swap 95 = or ;
: cc-digit ( c -- flag ) 48 58 cc-within ;
: cc-namechar dup cc-alpha swap cc-digit or ;
: cc-space dup 32 = swap 9 14 cc-within or ;
: cc-scan ( char -- )
  >r cc-source cc-pos @ + cc-length @ cc-pos @ - r> scan
  drop cc-source - cc-pos ! ;
: cc-comment
  cc-step cc-step
  begin
    42 cc-scan
    cc-peek -1 = if s" unfinished comment" cc-fail then
    cc-step cc-peek 47 = if cc-step exit then
  again ;
: cc-skip
  begin
    cc-peek cc-space if cc-step else
      cc-peek 47 = cc-pos @ 1+ cc-length @ < and if
        cc-source cc-pos @ 1+ + c@ dup 47 = if
          drop 10 cc-scan
        else 42 = if cc-comment
        else exit then then
      else exit then
    then
  again ;
: cc-text cc-source cc-token-start @ + cc-token-size @ ;
: cc-is ( addr len -- flag ) cc-text compare 0= ;
variable cc-radix
variable cc-number-start
: cc-number-next
  0 cc-number ! 0 cc-number-type ! 10 cc-radix !
  cc-peek 48 = cc-pos @ 1+ cc-length @ < and if
    8 cc-radix ! cc-source cc-pos @ 1+ + c@
    dup 120 = over 88 = or if drop cc-step cc-step 16 cc-radix ! else
      dup 98 = swap 66 = or if cc-step cc-step 2 cc-radix ! then then
  then cc-pos @ cc-number-start !
  begin cc-peek dup cc-digit if 48 - else
    dup 97 103 cc-within if 87 - else
      dup 65 71 cc-within if 55 - else drop 99 then then then
    dup cc-radix @ <
  while
    cc-radix @ 2 = if cc-number @ 2147483647 u> else
      cc-radix @ 8 = if cc-number @ 536870911 u> else
        cc-radix @ 10 = if
          cc-number @ 429496729 u> cc-number @ 429496729 = 2 pick 5 > and or
        else cc-number @ 268435455 u> then then then
    if drop s" integer literal out of range" cc-fail then
    cc-number @ cc-radix @ * + cc-number ! cc-step
  repeat drop
  cc-pos @ cc-number-start @ = if s" malformed number" cc-fail then
  cc-peek dup 117 = swap 85 = or if 1 cc-number-type ! cc-step then
  cc-peek cc-namechar if s" unsupported or malformed integer suffix" cc-fail then
  cc-number @ 2147483647 u> cc-number-type @ 0= and if
    cc-radix @ 10 = if s" 64-bit decimal literal unsupported" cc-fail then
    1 cc-number-type !
  then
  1 cc-token ! ;
: cc-next
  cc-skip cc-pos @ cc-token-start ! 0 cc-token-size !
  cc-peek dup -1 = if drop 0 cc-token ! exit then
  dup 0= if s" NUL in source" cc-fail then
  dup cc-alpha if drop
    begin cc-peek cc-namechar while cc-step repeat 2 cc-token !
  else dup cc-digit if drop cc-number-next
  else cc-step cc-token !
    cc-token @ dup 61 = over 33 = or over 60 = or swap 62 = or
    cc-peek 61 = and if
      cc-token @ dup 61 = if drop 256 else dup 33 = if drop 257 else
        60 = if 258 else 259 then then then cc-token ! cc-step
    then
    cc-token @ dup 60 = over 62 = or over 38 = or over 124 = or
    over 43 = or swap 45 = or
    cc-peek cc-token @ = and if
      cc-token @ dup 60 = if drop 260 else dup 62 = if drop 261 else
        dup 38 = if drop 262 else dup 124 = if drop 263 else
          43 = if 264 else 265 then then then then then cc-token ! cc-step
    then
    cc-token @ dup 43 = over 45 = or over 42 = or over 47 = or
    over 37 = or over 38 = or over 94 = or over 124 = or
    over 260 = or swap 261 = or cc-peek 61 = and if
      512 cc-token +! cc-step then
  then then cc-pos @ cc-token-start @ - cc-token-size ! ;
: cc-expect ( token -- ) cc-token @ <> if s" unexpected token" cc-fail then cc-next ;

create cc-function-names 16 32 * allot
create cc-function-entry 16 cells allot
create cc-function-return 16 cells allot
create cc-function-value 16 cells allot
create cc-function-argc 16 cells allot
create cc-function-params 16 8 * cells allot
create cc-symbol-names 128 32 * allot
create cc-symbol-address 128 cells allot
create cc-symbol-levels 128 cells allot
create cc-call-functions 128 cells allot
create cc-call-fields 128 cells allot
variable cc-call-count
variable cc-new-function
variable cc-parameter-count
create cc-types 512 allot
create cc-lvalues 512 allot
create cc-lvalue-pointers 512 cells allot
create cc-constant-types 512 allot
cc-constant-types 512 0 fill
variable cc-declared-type
variable cc-base-type
variable cc-function-type
variable cc-function-count
variable cc-function-index
variable cc-symbol-count
variable cc-main-index
variable cc-depth
variable cc-scope-level
variable cc-first-block
variable cc-statement-result
variable cc-in-function
: cc-find ( names count -- index ) L{ names entries }
  entries 0 ?do cc-text names entries 1- i - 32 * + count compare 0= if
    entries 1- i - unloop exit then
  loop -1 ;
: cc-find-symbol cc-symbol-names cc-symbol-count @ cc-find ;
: cc-find-function cc-function-names cc-function-count @ cc-find ;
: cc-type ( target -- type )
  dup cc-frame? if cc-data-base - 32 / cc-types + c@ exit then
  dup cc-constant-base >= over 180224 < and if
    cc-constant-base - 32 / cc-constant-types + c@ else drop 0 then ;
: cc-type! ( target type -- ) swap dup cc-frame? if
    cc-data-base - 32 / cc-types + c! else
    cc-constant-base - 32 / cc-constant-types + c! then ;
: cc-pointer? ( target -- flag ) cc-type 2 = ;
: cc-lvalue ( target -- kind )
  dup cc-frame? if cc-data-base - 32 / cc-lvalues + c@ else drop 0 then ;
: cc-lvalue! ( target kind -- ) swap cc-data-base - 32 / cc-lvalues + c! ;
: cc-lvalue-pointer ( target -- address ) cc-data-base - 32 / cells cc-lvalue-pointers + ;
: cc-value ( source -- value ) cc-cell L{ source value }
  value source cc-type cc-type! 32 value source cc-op value ;
: cc-integer-check ( target -- )
  cc-type 1 u> if s" expected integer operand" cc-fail then ;
: cc-value-check ( target -- ) cc-type 3 = if s" void value unsupported here" cc-fail then ;
' cc-value-check is cc-check-truth
: cc-common-type ( left right -- type ) cc-type swap cc-type or ;
: cc-null-constant? ( target -- flag )
  dup cc-constant-base >= over 180224 < and if
    cc-data-base - 8 / cc-image + dup c@ over 1+ c@ or
    over 2 + c@ or swap 3 + c@ or 0=
  else drop 0 then ;
: cc-assignment-check ( destination source -- ) L{ destination source }
  destination cc-value-check source cc-value-check
  destination cc-pointer? source cc-pointer? = if exit then
  destination cc-pointer? source cc-null-constant? and if exit then
  s" incompatible int and pointer" cc-fail ;
: cc-nest 1 cc-depth +! cc-depth @ 32 > cc-limit ;
: cc-unnest -1 cc-depth +! ;
defer cc-expression
defer cc-full-expression
defer cc-unary
defer cc-inspect
: cc-basic-type-start ( -- flag ) s" int" cc-is s" signed" cc-is or s" unsigned" cc-is or ;
: cc-typeof-token? s" typeof" cc-is s" __typeof" cc-is or s" __typeof__" cc-is or ;
: cc-type-start ( -- flag ) cc-basic-type-start cc-typeof-token? or ;
: cc-read-basic-type 0 0 L{ saw-int sign }
  cc-basic-type-start 0= if s" expected integer type" cc-fail then
  begin cc-basic-type-start while
    s" int" cc-is if saw-int if s" duplicate int type" cc-fail then -1 1 (local!)
    else sign if s" conflicting sign specifier" cc-fail then
      s" unsigned" cc-is if 2 else 1 then 2 (local!) then cc-next
  repeat sign 2 = if 1 else 0 then dup cc-declared-type ! cc-base-type !
  cc-token @ 42 = if
    cc-declared-type @ if s" unsigned pointer type unsupported" cc-fail then
    2 cc-declared-type ! cc-next then ;
: cc-read-type
  cc-typeof-token? if
    cc-next 40 cc-expect cc-nest
    cc-type-start if recurse else 0 cc-inspect cc-declared-type ! then
    cc-unnest 41 cc-expect cc-declared-type @ dup cc-base-type !
    cc-token @ 42 = if
      if s" pointer type unsupported" cc-fail then cc-next 2 then cc-declared-type !
  else cc-read-basic-type then ;
: cc-name! ( destination -- )
  s" int" cc-is s" void" cc-is or s" if" cc-is or s" else" cc-is or
  s" while" cc-is or s" return" cc-is or s" signed" cc-is or
  s" unsigned" cc-is or s" sizeof" cc-is or s" for" cc-is or
  s" do" cc-is or s" break" cc-is or s" continue" cc-is or
  cc-typeof-token? or
  if s" reserved name" cc-fail then
  cc-token @ 2 <> cc-token-size @ 31 > or cc-limit cc-text rot place ;
: cc-symbol-at ( target -- target )
  cc-find-symbol dup 0< 0= if cells cc-symbol-levels + @ cc-scope-level @ =
    if s" duplicate local name" cc-fail then else drop then
  cc-symbol-count @ 128 >= cc-limit
  cc-symbol-names cc-symbol-count @ 32 * + cc-name!
  dup cc-symbol-address cc-symbol-count @ cells + !
  cc-scope-level @ cc-symbol-levels cc-symbol-count @ cells + !
  dup 1 cc-lvalue!
  1 cc-symbol-count +! ;
: cc-symbol ( -- target ) cc-cell cc-symbol-at ;
: cc-fget ( index array -- value ) swap cells + @ ;
: cc-fset ( value index array -- ) swap cells + ! ;
: cc-param ( fn index -- target ) swap 8 * + cells cc-function-params + @ ;
defer cc-statement
defer cc-increment
defer cc-block
defer cc-sizeof
create cc-break-fields 128 cells allot
create cc-continue-fields 128 cells allot
variable cc-break-count
variable cc-continue-count
variable cc-loop-level

: cc-call ( fn -- value ) 0 L{ fn nargs }
  fn 0< fn cc-function-count @ >= or if s" unknown function" cc-fail then
  fn cc-main-index @ = cc-unevaluated @ 0= and if s" main cannot be called" cc-fail then
  40 cc-expect
  cc-token @ 41 <> if
    begin nargs 8 >= cc-limit cc-expression
      nargs 1+ 2 (local!)
      cc-token @ 44 = if cc-next 0 else -1 then
    until
  then
  41 cc-expect
  nargs fn cc-function-argc cc-fget <> if s" wrong argument count" cc-fail then
  nargs 0 ?do
    dup fn nargs 1- i - cc-param swap cc-assignment-check
    32 cc-call-args nargs 1- i - 32 * + rot cc-op
  loop
  cc-sp cc-stack-last cc-const cc-eq-entry @ cc-invoke cc-branch >r
  r@ 32 + cc-stack-error-entry @ cc-patch r> cc-current cc-patch
  cc-sp cc-frame-bits cc-const cc-add-entry @ cc-invoke 32 cc-sp rot cc-op
  nargs 0 ?do 32 fn i cc-param cc-call-args i 32 * + cc-op loop
  2 cc-room cc-current cc-layer-bits + cc-const
  24 fn cc-function-return cc-fget rot cc-op
  fn cc-function-entry cc-fget dup if cc-jump else drop
    cc-unevaluated @ 0= if
      cc-call-count @ 128 >= cc-limit
      fn cc-call-functions cc-call-count @ cells + !
      cc-current 18152 + cc-call-fields cc-call-count @ cells + !
      1 cc-call-count +!
    then 0 cc-jump
  then
  32 cc-saved-result fn cc-function-value cc-fget cc-op
  cc-sp cc-frame-bits negate cc-const cc-add-entry @ cc-invoke 32 cc-sp rot cc-op
  cc-cell dup fn cc-function-value cc-fget cc-type cc-type!
  dup 32 swap cc-saved-result cc-op ;

: cc-address ( target -- pointer ) cc-cell L{ target result }
  target cc-type if s" pointer to pointer unsupported" cc-fail then
  32 result target cc-data-base - cc-stack-base + 8 / cc-const cc-op
  10 result 11 + cc-sp 14 + cc-op result 2 cc-type! result ;
: cc-pointer-check ( pointer -- )
  dup cc-type 2 <> if s" expected int pointer" cc-fail then
  cc-zero @ cc-pointer-check-entry @ cc-invoke drop ;
: cc-pointer-read ( pointer -- value ) cc-value cc-cell 0 L{ pointer result slot }
  result 2 cc-lvalue! pointer result cc-lvalue-pointer !
  pointer cc-pointer-check
  2 pointer cc-frame-extra + result cc-frame-extra + cc-room
  cc-slot @ 1+ pointer cc-frame-extra + result cc-frame-extra + 3 (local!)
  21 slot 71 * 50 + pointer cc-op 32 result 0 cc-op result ;
: cc-pointer-write ( pointer value -- ) 0 L{ pointer value slot }
  value cc-integer-check
  pointer cc-pointer-check
  2 pointer cc-frame-extra + value cc-frame-extra + cc-room
  cc-slot @ 1+ pointer cc-frame-extra + value cc-frame-extra + 3 (local!)
  21 slot 71 * 26 + pointer cc-op 32 0 value cc-op ;
: cc-lvalue-write ( destination source -- value ) 0 L{ destination source result }
  destination cc-lvalue 0= if s" assignment requires lvalue" cc-fail then
  destination source cc-assignment-check
  source cc-value 3 (local!) result destination cc-type cc-type!
  destination cc-lvalue 1 = if 32 destination result cc-op else
    destination cc-lvalue-pointer @ result cc-pointer-write then result ;

: cc-primary ( -- target )
  cc-token @ 40 = if cc-next cc-nest
    cc-token @ 123 = if
      cc-in-function @ 0= if s" statement expression outside function" cc-fail then
      cc-block dup 0= if drop cc-cell dup 3 cc-type! then
    else cc-full-expression then cc-unnest 41 cc-expect exit then
  cc-token @ 1 = if cc-number @ cc-const dup cc-number-type @ cc-type! cc-next exit then
  cc-token @ 2 = if
    cc-find-symbol >r cc-find-function >r cc-next
    cc-token @ 40 = if r> r> 0< 0= if s" indirect call unsupported" cc-fail then
      cc-nest cc-call cc-unnest else
      r> drop r> dup 0< if drop s" unknown variable" cc-fail then
      cells cc-symbol-address + @ then exit
  then s" expected expression" cc-fail ;
: cc-postfix ( -- value )
  cc-primary begin cc-token @ dup 264 = swap 265 = or while
    cc-token @ cc-next -1 cc-increment repeat ;
: cc-unary-body ( -- target )
  s" sizeof" cc-is if cc-next cc-sizeof exit then
  cc-token @ 40 = if cc-token-start @ >r cc-next cc-type-start if
      cc-read-type cc-declared-type @ r> drop >r 41 cc-expect
      cc-nest recurse cc-unnest cc-cell dup r@ cc-type!
      dup 32 swap 3 roll cc-op r> drop exit
    then r> cc-pos ! cc-next then
  cc-token @ dup 264 = swap 265 = or if cc-token @ >r cc-next
    cc-nest recurse cc-unnest r> 0 cc-increment exit then
  cc-token @ 38 = if cc-next cc-find-symbol dup 0<
    if s" expected local object after &" cc-fail then
    cells cc-symbol-address + @ cc-next cc-address exit then
  cc-token @ 42 = if cc-next cc-nest recurse cc-unnest cc-pointer-read exit then
  cc-token @ 45 = if cc-next cc-nest recurse cc-unnest
    dup cc-integer-check dup cc-type >r
    cc-zero @ swap cc-sub-entry @ cc-invoke dup r> cc-type! exit then
  cc-token @ 43 = if cc-next cc-nest recurse cc-unnest dup cc-integer-check cc-value exit then
  cc-token @ 126 = if cc-next cc-nest recurse cc-unnest
    dup cc-integer-check dup cc-type >r
    cc-zero @ cc-not-entry @ cc-invoke dup r> cc-type! exit then
  cc-token @ 33 = if cc-next cc-nest recurse cc-unnest
    cc-truth cc-invert exit then cc-postfix ;
' cc-unary-body is cc-unary
: cc-integer-op ( lhs rhs entry -- value ) L{ lhs rhs entry }
  lhs cc-integer-check rhs cc-integer-check
  lhs rhs cc-common-type >r lhs rhs entry cc-invoke dup r> cc-type! ;
: cc-multiplicative-op ( lhs rhs token -- value ) L{ lhs rhs token }
  lhs rhs token 42 = if cc-mul-entry @ else
    lhs rhs cc-common-type 1 = if token 47 = if cc-udiv-entry @ else cc-umod-entry @ then
    else token 47 = if cc-div-entry @ else cc-mod-entry @ then then
  then cc-integer-op ;
: cc-multiplicative ( -- value )
  cc-unary begin cc-token @ dup 42 = over 47 = or swap 37 = or while
    cc-token @ >r cc-next cc-unary r> cc-multiplicative-op repeat ;
: cc-scale-index ( value -- value ) cc-cell L{ value result }
  32 result cc-zero @ cc-op 30 result 2 + value cc-op result ;
: cc-additive-op ( lhs rhs token -- value ) 0 0 L{ lhs rhs token difference result }
  lhs cc-pointer? rhs cc-pointer? and if
    token 45 <> if s" cannot add pointers" cc-fail then
    lhs rhs cc-sub-entry @ cc-invoke 4 (local!) cc-cell 5 (local!)
    30 result difference 2 + cc-op
    1 result 30 + difference 31 + cc-op 1 result 31 + difference 31 + cc-op result exit
  then
  lhs cc-pointer? if
    lhs rhs cc-scale-index token 43 = if cc-add-entry @ else cc-sub-entry @ then
    cc-invoke dup 2 cc-type! exit
  then
  rhs cc-pointer? if
    token 43 <> if s" cannot subtract pointer from int" cc-fail then
    rhs lhs cc-scale-index cc-add-entry @ cc-invoke dup 2 cc-type! exit
  then
  lhs rhs token 43 = if cc-add-entry @ else cc-sub-entry @ then cc-integer-op ;
: cc-increment-body ( destination token postfix -- value ) 0 L{ destination token postfix old }
  destination cc-lvalue 0= if s" increment requires lvalue" cc-fail then
  postfix if destination cc-value 4 (local!) then
  destination dup cc-one @ token 264 = if 43 else 45 then cc-additive-op
  cc-lvalue-write postfix if drop old then ;
' cc-increment-body is cc-increment
: cc-additive ( -- target )
  cc-multiplicative begin cc-token @ dup 43 = swap 45 = or while
    cc-token @ >r cc-next cc-multiplicative r> cc-additive-op repeat ;
: cc-shift-op ( lhs rhs token -- value ) L{ lhs rhs token }
  lhs cc-integer-check rhs cc-integer-check lhs cc-type >r
  lhs rhs token 260 = if cc-shl-entry @ else
    lhs cc-type 1 = if cc-shr-entry @ else cc-sar-entry @ then then
  cc-invoke dup r> cc-type! ;
: cc-shift ( -- target )
  cc-additive begin cc-token @ dup 260 = swap 261 = or while
    cc-token @ >r cc-next cc-additive r> cc-shift-op repeat ;
: cc-relational-op ( lhs rhs op -- target ) L{ lhs rhs op }
  lhs cc-value-check rhs cc-value-check
  lhs cc-pointer? rhs cc-pointer? <> if s" incompatible comparison" cc-fail then
  lhs cc-type rhs cc-type or if cc-ult-entry @ else cc-lt-entry @ then >r
  op 60 = if lhs rhs r> cc-invoke exit then
  op 62 = if rhs lhs r> cc-invoke exit then
  op 258 = if rhs lhs r> cc-invoke cc-invert else
    lhs rhs r> cc-invoke cc-invert then ;
: cc-relational ( -- target )
  cc-shift begin cc-token @ dup 60 = over 62 = or over 258 = or swap 259 = or while
    cc-token @ >r cc-next cc-shift r> cc-relational-op repeat ;
: cc-equality ( -- target )
  cc-relational begin cc-token @ dup 256 = swap 257 = or while
    cc-token @ >r cc-next cc-relational
    dup cc-value-check over cc-value-check
    2dup cc-pointer? swap cc-pointer? <> if
      2dup cc-null-constant? swap cc-null-constant? or 0=
      if s" incompatible comparison" cc-fail then
    then cc-eq-entry @ cc-invoke
    r> 257 = if cc-invert then repeat ;
: cc-bit-and ( -- value )
  cc-equality begin cc-token @ 38 = while cc-next cc-equality cc-and-entry @ cc-integer-op repeat ;
: cc-bit-xor ( -- value )
  cc-bit-and begin cc-token @ 94 = while cc-next cc-bit-and cc-xor-entry @ cc-integer-op repeat ;
: cc-bit-or ( -- value )
  cc-bit-xor begin cc-token @ 124 = while cc-next cc-bit-xor cc-or-entry @ cc-integer-op repeat ;
: cc-forward ( -- field ) cc-current 18152 + >r 0 cc-jump r> ;
: cc-link! ( field target -- ) cc-unevaluated @ if 2drop exit then swap 24 swap cc-value! ;
defer cc-logical-and
defer cc-conditional
: cc-logical-step ( lhs token -- result ) cc-cell 0 0 L{ lhs token result table skip }
  lhs cc-truth cc-branch 4 (local!)
  table token 262 = if 0 else 32 then + cc-current cc-patch
  32 result token 262 = if cc-zero @ else cc-one @ then cc-op
  cc-forward 5 (local!)
  table token 262 = if 32 else 0 then + cc-current cc-patch
  cc-next token 262 = if cc-bit-or else cc-logical-and then cc-truth
  32 result rot cc-op skip cc-boundary cc-link! result ;
: cc-logical-and-body ( -- value )
  cc-bit-or begin cc-token @ 262 = while 262 cc-logical-step repeat ;
' cc-logical-and-body is cc-logical-and
: cc-logical-or ( -- value )
  cc-logical-and begin cc-token @ 263 = while 263 cc-logical-step repeat ;
: cc-conditional-step ( condition -- result )
    cc-truth cc-branch cc-cell 0 0 0 L{ table result yes no skip }
    table 32 + cc-current cc-patch cc-next
    cc-nest cc-full-expression cc-unnest 3 (local!)
    32 result yes cc-op cc-forward 5 (local!)
    58 cc-expect table cc-current cc-patch
    cc-nest cc-conditional cc-unnest 4 (local!) 32 result no cc-op
    yes cc-type 3 = no cc-type 3 = or if result 3 cc-type! else
    yes cc-pointer? no cc-pointer? <> if
      yes cc-pointer? if no else yes then cc-null-constant? 0=
      if s" incompatible conditional operands" cc-fail then
      result 2 cc-type!
    else result yes no cc-common-type cc-type! then then
    skip cc-boundary cc-link! result ;
: cc-conditional-body ( -- result )
  cc-logical-or cc-token @ 63 = if cc-conditional-step then ;
' cc-conditional-body is cc-conditional
: cc-compound-op ( lhs rhs token -- value ) L{ lhs rhs token }
  token 43 = token 45 = or if lhs rhs token cc-additive-op exit then
  token 42 = token 47 = or token 37 = or if lhs rhs token cc-multiplicative-op exit then
  token 260 = token 261 = or if lhs rhs token cc-shift-op exit then
  lhs rhs token 38 = if cc-and-entry @ else
    token 94 = if cc-xor-entry @ else cc-or-entry @ then then cc-integer-op ;
: cc-assignment-step ( destination token -- value ) L{ destination token }
  destination cc-lvalue 0= if s" assignment requires lvalue" cc-fail then
  cc-next cc-nest cc-expression cc-unnest
  token 61 <> if destination swap token 512 - cc-compound-op then
  destination swap cc-lvalue-write ;
: cc-assignment-expression ( -- value )
  cc-conditional cc-token @ dup 61 = swap 512 >= or if
    cc-token @ cc-assignment-step then ;
' cc-assignment-expression is cc-expression
: cc-full-expression-body ( -- value )
  cc-expression cc-token @ 44 = if
    begin drop cc-next cc-expression cc-token @ 44 <> until cc-value then ;
' cc-full-expression-body is cc-full-expression
: cc-inspect-body ( unary -- type )
  cc-data @ cc-constants @ cc-call-count @ cc-symbol-count @ 0
  L{ unary data constants calls symbols type }
  1 cc-unevaluated +! cc-nest
  unary if cc-unary else cc-full-expression then cc-type 6 (local!)
  cc-unnest -1 cc-unevaluated +!
  data cc-data-base - 32 / cc-data @ data - 32 / >r
  dup cc-types + r@ 0 fill cc-lvalues + r> 0 fill
  constants cc-constant-base - 32 / cc-constant-types +
  cc-constants @ constants - 32 / 0 fill
  data cc-data ! constants cc-constants ! calls cc-call-count ! symbols cc-symbol-count ! type ;
' cc-inspect-body is cc-inspect
: cc-sizeof-body
  cc-token @ 40 = if
    cc-token-start @ >r cc-next cc-type-start if
      cc-read-type cc-declared-type @ r> drop 41 cc-expect
    else r> cc-pos ! cc-next 1 cc-inspect then
  else 1 cc-inspect then
  3 = if 1 else 4 then cc-const dup 1 cc-type! ;
' cc-sizeof-body is cc-sizeof

: cc-return-value ( value -- )
  dup cc-function-index @ cc-function-value cc-fget swap cc-assignment-check
  cc-function-index @ cc-main-index @ = if 32 cc-r rot cc-op cc-output-entry @ cc-jump else
    32 cc-function-index @ cc-function-value cc-fget rot cc-op
    cc-function-index @ cc-function-return cc-fget cc-dynamic then ;
: cc-if
  cc-next 40 cc-expect cc-full-expression 41 cc-expect cc-truth cc-branch L{ table }
  table 32 + cc-current cc-patch cc-nest cc-statement cc-unnest
  s" else" cc-is if
    cc-forward >r table cc-current cc-patch cc-next
    cc-nest cc-statement cc-unnest r> cc-boundary cc-link!
  else table cc-boundary cc-patch then ;
: cc-loop-finish ( continue-target end breaks continues -- ) L{ continue-target end breaks continues }
  cc-break-count @ breaks ?do cc-break-fields i cells + @ end cc-link! loop
  cc-continue-count @ continues ?do cc-continue-fields i cells + @ continue-target cc-link! loop
  breaks cc-break-count ! continues cc-continue-count ! -1 cc-loop-level +! ;
: cc-loop-transfer ( is-continue -- ) L{ is-continue }
  cc-loop-level @ 0= if s" loop transfer outside loop" cc-fail then
  cc-next 59 cc-expect
  cc-unevaluated @ if exit then
  is-continue if
    cc-continue-count @ 128 >= cc-limit
    cc-forward cc-continue-fields cc-continue-count @ cells + ! 1 cc-continue-count +!
  else
    cc-break-count @ 128 >= cc-limit
    cc-forward cc-break-fields cc-break-count @ cells + ! 1 cc-break-count +!
  then ;
: cc-while
  cc-next cc-boundary 0 0 0 L{ head table breaks continues }
  40 cc-expect cc-full-expression 41 cc-expect cc-truth cc-branch 2 (local!)
  cc-break-count @ 3 (local!) cc-continue-count @ 4 (local!) 1 cc-loop-level +!
  table 32 + cc-current cc-patch cc-nest cc-statement cc-unnest
  head cc-jump table cc-current cc-patch
  head cc-current breaks continues cc-loop-finish ;
: cc-do
  cc-next cc-boundary 0 cc-break-count @ cc-continue-count @ L{ head condition breaks continues }
  1 cc-loop-level +! cc-nest cc-statement cc-unnest
  cc-boundary 2 (local!)
  s" while" cc-is 0= if s" do requires while" cc-fail then
  cc-next 40 cc-expect cc-full-expression 41 cc-expect 59 cc-expect
  cc-truth cc-branch dup 32 + head cc-patch cc-current cc-patch
  condition cc-current breaks continues cc-loop-finish ;
: cc-declarator-type ( base -- type )
  cc-token @ 42 = if
    if s" pointer type unsupported" cc-fail then cc-next 2 then ;
: cc-declaration
  cc-read-type cc-base-type @ cc-declared-type @ L{ base type }
  begin
    type 3 = if s" void object unsupported" cc-fail then
    cc-symbol dup type cc-type! >r cc-next
    cc-token @ 61 = if cc-next cc-expression else cc-zero @ then
    dup r@ swap cc-assignment-check 32 r> rot cc-op
    cc-token @ 44 = if cc-next base cc-declarator-type 2 (local!) 0 else -1 then
  until 59 cc-expect ;
: cc-for
  cc-symbol-count @ 0 0 0 0 0 L{ symbols head table step breaks continues }
  cc-next 40 cc-expect
  1 cc-scope-level +!
  cc-type-start if cc-declaration else
    cc-token @ 59 <> if cc-full-expression drop then 59 cc-expect then
  cc-boundary 2 (local!)
  cc-token @ 59 = if cc-one @ else cc-full-expression cc-truth then
  59 cc-expect cc-branch 3 (local!)
  cc-boundary 4 (local!)
  cc-token @ 41 <> if cc-full-expression drop then 41 cc-expect
  head cc-jump table 32 + cc-current cc-patch
  cc-break-count @ 5 (local!) cc-continue-count @ 6 (local!) 1 cc-loop-level +!
  cc-nest cc-statement cc-unnest step cc-jump
  table cc-current cc-patch step cc-current breaks continues cc-loop-finish
  symbols cc-symbol-count ! -1 cc-scope-level +! ;
: cc-block-body
  cc-symbol-count @ cc-first-block @ L{ symbols first }
  0 cc-first-block ! first 0= if 1 cc-scope-level +! then
  0 cc-statement-result ! cc-next begin cc-token @ 125 <> while
    cc-token @ 0= if s" unfinished block" cc-fail then
    cc-nest cc-statement cc-unnest
  repeat cc-next symbols cc-symbol-count !
  first 0= if -1 cc-scope-level +! then cc-statement-result @ ;
' cc-block-body is cc-block
: cc-statement-body
  0 cc-statement-result !
  cc-token @ 123 = if
    cc-block drop 0 cc-statement-result ! exit then
  cc-type-start if cc-declaration 0 cc-statement-result ! exit then
  s" if" cc-is if cc-if 0 cc-statement-result ! exit then
  s" while" cc-is if cc-while 0 cc-statement-result ! exit then
  s" do" cc-is if cc-do 0 cc-statement-result ! exit then
  s" for" cc-is if cc-for 0 cc-statement-result ! exit then
  s" break" cc-is if 0 cc-loop-transfer exit then
  s" continue" cc-is if -1 cc-loop-transfer exit then
  s" return" cc-is if cc-next cc-full-expression 59 cc-expect cc-return-value
    0 cc-statement-result ! exit then
  cc-token @ 59 = if cc-next exit then
  cc-full-expression cc-statement-result ! 59 cc-expect ;
' cc-statement-body is cc-statement

: cc-function
  cc-read-type cc-declared-type @ cc-function-type !
  cc-function-type @ 3 = if s" void function unsupported" cc-fail then
  cc-find-function dup -1 = if drop
    -1 cc-new-function !
    cc-function-count @ dup cc-function-index ! 16 >= cc-limit
    cc-function-names cc-function-index @ 32 * + cc-name!
    0 cc-function-index @ cc-function-entry cc-fset
    cc-cell cc-function-index @ cc-function-return cc-fset
    cc-cell dup cc-function-type @ cc-type!
    cc-function-index @ cc-function-value cc-fset
    0 cc-function-index @ cc-function-argc cc-fset
    1 cc-function-count +!
  else cc-function-index ! 0 cc-new-function !
    cc-function-index @ cc-function-value cc-fget cc-type cc-function-type @ <>
    if s" conflicting function return type" cc-fail then
  then
  s" main" cc-is if cc-function-index @ cc-main-index ! then
  0 cc-symbol-count ! 0 cc-parameter-count ! 1 cc-scope-level ! cc-next 40 cc-expect
  cc-token @ 41 <> if
    s" void" cc-is if cc-next else
      begin
        cc-read-type
        cc-declared-type @ 3 = if s" void parameter unsupported" cc-fail then
        cc-parameter-count @ dup 8 >= cc-limit >r
        cc-new-function @ if
          cc-cell dup cc-declared-type @ cc-type!
          dup cc-function-index @ 8 * r@ + cells cc-function-params + !
        else
          r@ cc-function-index @ cc-function-argc cc-fget >=
          if s" conflicting prototype" cc-fail then
          cc-function-index @ r@ cc-param
          dup cc-type cc-declared-type @ <>
          if s" conflicting parameter type" cc-fail then
        then
        cc-token @ 2 = if cc-symbol-at drop cc-next else drop then
        r> 1+ cc-parameter-count !
        cc-token @ 44 = if cc-next 0 else -1 then
      until
    then
  then 41 cc-expect
  cc-new-function @ if
    cc-parameter-count @ cc-function-index @ cc-function-argc cc-fset
  else cc-parameter-count @ cc-function-index @ cc-function-argc cc-fget <>
    if s" conflicting prototype" cc-fail then
  then
  cc-token @ 59 = if cc-next exit then
  cc-function-index @ cc-function-entry cc-fget
  if s" duplicate function definition" cc-fail then
  cc-symbol-count @ cc-parameter-count @ <>
  if s" parameter name missing in definition" cc-fail then
  cc-boundary cc-function-index @ cc-function-entry cc-fset
  cc-function-index @ cc-main-index @ = if
    cc-function-type @ if s" main must return int" cc-fail then
    cc-function-index @ cc-function-argc cc-fget 0<> if s" main takes no parameters" cc-fail then
  then
  cc-token @ 123 <> if s" expected function body" cc-fail then
  -1 cc-first-block !
  -1 cc-in-function ! cc-statement 0 cc-in-function ! cc-zero @ cc-return-value ;

: cc-finish
  cc-main-index @ 0< if s" main missing" cc-fail then
  cc-main-index @ cc-function-entry cc-fget 0=
  if s" main definition missing" cc-fail then
  cc-call-count @ 0 ?do
    cc-call-functions i cells + @ cc-function-entry cc-fget
    dup 0= if s" called function has no definition" cc-fail then
    cc-call-fields i cells + @ swap cc-link!
  loop
  cc-main-index @ cc-function-entry cc-fget 32 64 cc-guard-constants cc-bits!
  cc-current cc-data-base - 2 * 32 0 cc-guard-constants cc-bits! ;
: cc-export
  cc-prelude cc-prelude-bytes @ dup >r cs-write r> <> if 1 cs-exit then
  cc-guard-data cc-guard-constants 36 cc-install
  cc-record 37 0 fill
  24 cc-load-status 118 0 cc-record cc-row-at
  cc-current cc-data-base - cc-data-base 0 71 cc-record cc-row-at
  cc-layer-bits 0 cc-guard-code 213 cc-record cc-row-at
  cc-record 37 cs-write 37 <> if 1 cs-exit then
  cc-image cc-current cc-data-base - 8 / dup >r cs-write r> <> if 1 cs-exit then ;
: cc-read-source
  0 cc-length !
  begin cc-source cc-length @ + cc-source-max 1+ cc-length @ - cs-read
    dup 0< if drop s" input error" cc-fail then
    dup 0= if drop exit then cc-length +!
    cc-length @ cc-source-max > cc-limit
  again ;
: CC-RUN
  0 cc-pos ! 0 cc-token-start ! 0 cc-depth ! 0 cc-function-count ! 0 cc-call-count !
  0 cc-loop-level ! 0 cc-break-count ! 0 cc-continue-count !
  0 cc-scope-level ! 0 cc-first-block !
  0 cc-unevaluated !
  0 cc-in-function !
  -1 cc-main-index ! cc-data-base cc-data !
  cc-types 512 0 fill
  cc-lvalues 512 0 fill
  cc-constant-types 512 0 fill
  cc-code-base cc-origin ! cc-data-base cc-emission-base ! cc-image cc-emission-buffer !
  cc-library-layer @ cc-layer ! 3 cc-slot !
  cc-library-constants @ cc-constants !
  cc-read-source cc-next begin cc-token @ while cc-function repeat
  cc-finish cc-export 0 cs-exit ;
